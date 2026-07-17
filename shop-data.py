# Author: Jonas Sheikh
# AIT Austrian Institute of technology
# description: extraction of data from online shops

# Bereits getestete und funktionierende URLs für die E-Mail Extraktion:

# url = "https://www.cuttingboarddirect.com/kontaktieren-sie-uns/"
# url = "https://wildlingschuh.com/about-us/"
# url = "https://eolatetuko.shop/pages/kontaktieren-sie-uns"
# url = "https://motelamiioofficial.com/pages/impressum" #(Identifikationsnummer)
# url = "https://alpenholz.shop/" #(Statisch auffindbar)
# url = "https://www.redefinedrebelit.com/politica-sulla-riservatezza/"

import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from postal.parser import parse_address
from postal.expand import expand_address
import phonenumbers
from phonenumbers import PhoneNumberMatcher, carrier, geocoder
import sqlite3
import os
from dotenv import load_dotenv
import whois
from urllib.parse import urlparse
import socket

load_dotenv()
db_path = os.getenv("DATABASE_PATH")

url = "https://motelamiioofficial.com/pages/impressum"

def format_date(datum):
    """Hilfsfunktion, da WHOIS-Daten manchmal als Liste zurückgegeben werden"""
    if isinstance(datum, list):
        return datum[0].strftime("%Y-%m-%d %H:%M:%S")
    elif datum:
        return datum.strftime("%Y-%m-%d %H:%M:%S")
    return "NULL"    

with sqlite3.connect(db_path) as connection:
    cursor = connection.cursor()

    # Tabelle erstellen: Später im C-Programm
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fakeshops (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   url TEXT,
                   status INTEGER,
                   title TEXT,
                   email1 TEXT,   
                   email2 TEXT,
                   phonenumber TEXT,
                   phonenumber_location TEXT,
                   phonenumber_carrier TEXT,
                   address TEXT UNIQUE,
                   url_creation_date TEXT,
                   url_expiration_date TEXT,
                   url_last_update TEXT,
                   servername TEXT,
                   domain_status TEXT,
                   registered_country TEXT,
                   date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # cursor.execute("DELETE FROM fakeshops")

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    headers = {"User-Agent": USER_AGENT}

    # cursor.execute("""
    #                INSERT INTO fakeshops(url)
    #                VALUES (?)
    # """, (url,))

    response = requests.get(url, headers = headers)
    soup = BeautifulSoup(response.text, "html.parser")
    page = soup.get_text()

    # Websitetitel ausgeben
    whole_title = soup.title.string
    title = whole_title.text.split(" ", 1)[0]
    print("Titel: ", title)

    cursor.execute("""
                   UPDATE fakeshops
                   SET title = ?
                   WHERE url = ?
    """, (title, url,))

    "Funktion zum Suchen von Daten auf Seiten mit dynamischen JavaScript Elementen"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless = False)
        page = browser.new_page(user_agent = USER_AGENT)

        page_text = ""
        try:
            page.goto(url, wait_until="domcontentloaded")
            page_text = page.locator("body").inner_text()
        except Exception as e:
            print(f"\nFehler: Playwright konnte die Seite nicht laden: {e}")

        if page_text:

            # E-Mail Adressen über ein Muster suchen

            p_email_muster = r"[a-zA-Z0-9-_.]+@[a-zA-Z0-9-_.]+\.[a-zA-Z]{2,}"
            found_mails = re.findall(p_email_muster, page_text)

            if found_mails:
                print("\nGefundene E-Mail-Adressen:")
                count = 1
                for email in set(found_mails):
                    print(f"- {email}")

                    if count == 1:
                        cursor.execute("""
                                       UPDATE fakeshops
                                       SET email1 = ?
                                       WHERE url = ?
                        """, (email, url,))

                    if count == 2:
                        cursor.execute("""
                                       UPDATE fakeshops
                                       SET email2 = ?
                                       WHERE url = ?
                        """, (email, url,))
                    count = count + 1    
            else:
                print("Keine E-Mail-Adresse im Text der Seite gefunden.")


            # Adressen über die KI-Bibliothek postal suchen

            formatted_address = None

            analyse = parse_address(page_text)
            c_address = {}

            # Ersten Buchstaben groß
            for wert, label in analyse:
                c_address[label] = wert.title()

            road = c_address.get('road', '')
            house_number = c_address.get('house_number', '')
            postcode = c_address.get('postcode', '')
            city = c_address.get('city', '')    

            if (road and house_number and city):
                formatted_address = f"{road} {house_number}, {postcode} {city}".strip(", ")

                print("\nAdresse: ", end = "")
                print(formatted_address)

            cursor.execute("""
                           UPDATE fakeshops
                           SET address = ?
                           WHERE url = ?
            """, (formatted_address, url,))


            # Telefonnummer über Googles Bibliothek libphonenumbers finden 

            matcher = PhoneNumberMatcher(page_text, "AT")
            print("\nTelefonnummer: ")

            for match in matcher:
                phone_obj = match.number

                formatted = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                formatted_location = geocoder.description_for_number(phone_obj, "de")
                formatted_carrier = carrier.name_for_number(phone_obj, "de")

                print(f"{formatted}\nlocation: {formatted_location}\ncarrier: {formatted_carrier}")

                cursor.execute("""
                               UPDATE fakeshops
                               SET phonenumber = ?,
                                   phonenumber_location = ?,
                                   phonenumber_carrier = ?
                               WHERE url = ?
                """, (formatted, formatted_location, formatted_carrier, url,))


        # Serverdaten mit der Python Bibliothek whois auslesen

        # Standardwerte definieren
        url_creation_date = None
        url_expiration_date = None
        url_last_update = None
        servername = None
        domain_status = None
        registered_country = None

        socket.setdefaulttimeout(10.0)

        try: 
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            if domain.startswith("www."):
                domain = domain[4:]

            w = whois.whois(domain)  

            url_creation_date = format_date(w.creation_date)
            url_expiration_date = format_date(w.expiration_date)
            url_last_update = format_date(w.updated_date)

            if isinstance(w.name_servers, list):
                servername = ", ".join(w.name_servers)
            else:
                servername = w.name_servers

            if isinstance(w.status, list):
                domain_status = ", ".join(w.status)
            else:
                domain_status = w.status

            registered_country = w.country

        except Exception as e:
            print(f"Standard-WHOIS fehlgeschlagen ({e}). Starte RDAP HTTP-Fallback...")

            try: 
                rdap_response = requests.get(f"https://rdap.org/domain/{domain}", timeout=10)

                if rdap_response.status_code == 200:
                    rdap_data = rdap_response.json()

                    events = rdap_data.get("events") or []
                    for event in events:
                        action = event.get("eventAction", "").lower()
                        raw_date = event.get("eventDate")

                        formatted_date = raw_date.replace("T", " ").replace("Z", "")[:19] if raw_date else None

                        if "registration" in action or "create" in action:
                            url_creation_date = formatted_date
                        elif "expiration" in action or "expire" in action:
                            url_expiration_date = formatted_date
                        elif "changed" in action or "update" in action:
                            url_last_update = formatted_date

                    ns_list = rdap_data.get("nameservers", [])
                    if ns_list:
                        servername = ", ".join([ns.get("ldhName", "").lower() for ns in ns_list])
                        
                    status_list = rdap_data.get("status", [])
                    if status_list:
                        domain_status = ", ".join(status_list)      

                    # Registriertes Land aus vCard-Einträgen auslesen
                    entities = rdap_data.get("entities") or []
                    for entity in entities:
                        if not entity:  # Falls ein Entity-Eintrag None ist
                            continue
                        
                        vcard_array = entity.get("vcardArray")
                        if isinstance(vcard_array, list) and len(vcard_array) > 1:
                            vcard = vcard_array[1] or []
                            for prop in vcard:
                                if isinstance(prop, list) and prop[0] == "adr" and len(prop) > 3:
                                    address_parts = prop[3]
                                    if isinstance(address_parts, list) and address_parts:
                                        registered_country = address_parts[-1]
                else: 
                    print(f"RDAP API lieferte Status-Code: {rdap_response.status_code}")

            except Exception as rdap_error:
                print(f"RDAP-Fallback ebenfalls fehlgeschlagen: {rdap_error}")

        cursor.execute("""
                       UPDATE fakeshops
                       SET url_creation_date = ?,
                           url_expiration_date = ?,
                           url_last_update = ?,
                           servername = ?,
                           domain_status = ?,
                           registered_country = ?
                       WHERE url = ?
        """, (url_creation_date, url_expiration_date, url_last_update, servername, domain_status, registered_country, url,))

        connection.commit()
        browser.close() 