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
import sys
from langdetect import DetectorFactory, detect

load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
db_path = os.path.join(data_dir, "fakeshops.db")  # Pass den Dateinamen an, falls nötig
os.makedirs(data_dir, exist_ok=True)

if len(sys.argv) < 2:
    print("Fehler, keine URL ueberliefert! ❌")
    sys.exit(1)

start_url = sys.argv[1]    

def format_date(datum):
    """Hilfsfunktion, da WHOIS-Daten manchmal als Liste zurückgegeben werden"""
    if isinstance(datum, list):
        return datum[0].strftime("%Y-%m-%d %H:%M:%S")
    elif datum:
        return datum.strftime("%Y-%m-%d %H:%M:%S")
    return "NULL"    

def finde_impressum(start_url):
    """
    Sucht auf der Startseite nach Links zu Impressum, Kontakt oder Über uns.
    Falls nichts oder kaputte Links gefunden werden, wird die start_url zurückgegeben.
    """
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    headers = {"User-Agent": USER_AGENT}
    
    parsed_base = urlparse(start_url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    # Wir merken uns den reinen Domainnamen (z.B. "plu-group.at")
    raw_domain = parsed_base.netloc.replace("www.", "")
    
    suchbegriffe = ["impressum", "legal", "kontakt", "contact", "about", "politica", "privacy"]
    
    PRIORITAETEN = {
        "impressum": 1,
        "about": 2,
        "kontakt": 3,
        "contact": 4,
        "legal": 5,
        "politica": 6,
        "privacy": 7
    }

    try:
        response = requests.get(start_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return start_url
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Liste zum Sammeln aller potenziellen Treffer: (Priorität, URL)
        gefundene_links = []
        
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            link_text = link.get_text().lower()

            if href.lower().startswith("javascript:"):
                continue
            
            # Wir gehen die Begriffe nach ihren Prioritäten durch
            for begriff, prio in PRIORITAETEN.items():
                if begriff in link_text or begriff in href.lower():
                    # Link auflösen, falls er relativ ist
                    full_href = href
                    if full_href.startswith("/"):
                        full_href = base_domain + full_href
                    elif not full_href.startswith("http"):
                        full_href = base_domain + "/" + full_href
                    
                    # SICHERHEITS-CHECK: Verhindert kaputte Links
                    parsed_found = urlparse(full_href)
                    if raw_domain not in parsed_found.netloc:
                        continue 
                        
                    # Nicht sofort zurückgeben, sondern mit Priorität merken!
                    gefundene_links.append((prio, full_href))

        # Wenn Treffer gefunden wurden: Sortieren und den besten nehmen
        if gefundene_links:
            # Sortiert nach 'prio' (Element 0 im Tupel) -> 1 kommt vor 2, etc.
            gefundene_links.sort(key=lambda x: x[0])
            
            beste_prio, beste_url = gefundene_links[0]
            print(f"Such URL: {beste_url}")
            return beste_url
                    
    except Exception as e:
        print(f"Fehler bei der automatischen Suche: {e} ❌")
        
    print("-> Kein valider spezifischer Link gefunden. Nutze Startseite.")
    return start_url

with sqlite3.connect(db_path, detect_types = sqlite3.PARSE_DECLTYPES) as connection:
    cursor = connection.cursor()

    # cursor.execute("DELETE FROM fakeshops")

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    headers = {"User-Agent": USER_AGENT}

    url = finde_impressum(start_url)

    try:
        response = requests.get(start_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        page = soup.get_text()

        # Websitesprache ausgeben
        DetectorFactory.seed = 0

        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator = " ", strip = True) 

        if text:
            detected_lang = detect(text)
            cursor.execute("""
                           UPDATE fakeshops
                           SET language = ?,
                           date = datetime('now', 'localtime')
                           WHERE URL = ?
            """, (detected_lang, start_url,))
        
        # Websitetitel ausgeben
        if soup.title and soup.title.string:
            whole_title = soup.title.string
            title = whole_title.strip().split(" ", 1)[0]

            cursor.execute("""
                           UPDATE fakeshops
                           SET title = ?,
                           date = datetime('now', 'localtime')
                           WHERE URL = ?
            """, (title, start_url,))
            connection.commit()
    except Exception as e:
        print(f"\n[!] Konnte Titel/Text von {url} nicht laden ({e}). Fallback auf Startseite für Playwright. ❌")
        # Falls die Unterseite fehlerhaft war, zwingen wir das restliche Skript, 
        # stattdessen mit der sicheren Startseite weiterzuarbeiten:
        url = start_url

    "Funktion zum Suchen von Daten auf Seiten mit dynamischen JavaScript Elementen"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless = True)
        page = browser.new_page(user_agent = USER_AGENT)

        page_text = ""
        try:
            page.goto(url, wait_until="domcontentloaded")
            page_text = page.locator("body").inner_text()
        except Exception as e:
            print(f"\nFehler: Playwright konnte die Seite nicht laden: {e} ❌")

        if page_text:

            # E-Mail Adressen über ein Muster suchen

            p_email_muster = r"[a-zA-Z0-9-_.]+@[a-zA-Z0-9-_.]+\.[a-zA-Z]{2,}"
            found_mails = re.findall(p_email_muster, page_text)

            if found_mails:
                count = 1
                for email in set(found_mails):

                    if count == 1:
                        cursor.execute("""
                                       UPDATE fakeshops
                                       SET email1 = ?
                                       WHERE URL = ?
                        """, (email, start_url,))

                    if count == 2:
                        cursor.execute("""
                                       UPDATE fakeshops
                                       SET email2 = ?
                                       WHERE URL = ?
                        """, (email, start_url,))
                    count = count + 1    


            # Adressen über die KI-Bibliothek postal suchen

            # Liste von Wörtern, die keinesfalls in einer echten Straße oder Stadt stehen dürfen
            BLACK_WORDS = ["samstag", "sonntag", "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "uhr", "öffnungszeiten", "tel", "telefon"]

            # 1. Analyse durchführen
            analyse = parse_address(page_text)

            # Speicher für die gefundenen Werte
            valid_road = None
            valid_house_number = None
            valid_postcode = None
            valid_city = None

            # 2. Wir gehen alle von libpostal erkannten Elemente einzeln durch
            for wert, label in analyse:
                wert_clean = wert.strip().title()
                wert_lower = wert.lower()

                # Prüfen, ob dieser konkrete Wert ein Blacklist-Wort enthält
                has_blacklist_word = any(bad_word in wert_lower for bad_word in BLACK_WORDS)

                # -------------------------------------------------------------
                # STRASSE: Nimm das erste Element mit Label 'road', das KEIN Blacklist-Wort hat
                # -------------------------------------------------------------
                if label == 'road' and not valid_road:
                    if not has_blacklist_word:
                        valid_road = wert_clean

                # -------------------------------------------------------------
                # HAUSNUMMER: Nimm die erste gefundene Hausnummer
                # -------------------------------------------------------------
                elif label == 'house_number' and not valid_house_number:
                    valid_house_number = wert_clean

                # -------------------------------------------------------------
                # POSTLEITZAHL: Nimm die erste Zahl (4 bis 5 Stellen)
                # -------------------------------------------------------------
                elif label == 'postcode' and not valid_postcode:
                    if wert_clean.isdigit() and len(wert_clean) in [4, 5]:
                        valid_postcode = wert_clean

                # -------------------------------------------------------------
                # STADT: Nimm die erste Stadt ohne Blacklist-Wort
                # -------------------------------------------------------------
                elif label == 'city' and not valid_city:
                    if not has_blacklist_word:
                        valid_city = wert_clean


            # 3. Zusammenbauen der Adresse
            formatted_address = None

            # Nur wenn wir alle Bestandteile sauber gefunden haben, bauen wir die Adresse zusammen
            if valid_road and valid_house_number and valid_city and valid_postcode:
                formatted_address = f"{valid_road} {valid_house_number}, {valid_postcode} {valid_city}"

            # Database-Update bleibt wie gehabt
            cursor.execute("""
                UPDATE fakeshops
                SET address = ?
                WHERE URL = ?
            """, (formatted_address, start_url,))


            # Telefonnummer über Googles Bibliothek libphonenumbers finden 

            matcher = PhoneNumberMatcher(page_text, "AT")

            for match in matcher:
                phone_obj = match.number

                formatted = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                formatted_location = geocoder.description_for_number(phone_obj, "de")
                formatted_carrier = carrier.name_for_number(phone_obj, "de")

                cursor.execute("""
                               UPDATE fakeshops
                               SET phonenumber = ?,
                                   phonenumber_location = ?,
                                   phonenumber_carrier = ?
                               WHERE URL = ?
                """, (formatted, formatted_location, formatted_carrier, start_url,))


            # analysieren der eventuell angegebenen Umsatzsteuer-Identifikationsnummer

            USt_IdNr_muster = re.compile(
                r'\b('
                r'AT\s*U\s*\d{8}|'        # Österreich: ATU + 8 Ziffern
                r'DE\s*\d{9}|'            # Deutschland: DE + 9 Ziffern
                r'CH\s*E\s*\d{9}|'        # Schweiz (UID): CHE + 9 Ziffern (oft im Impressum)
                r'FR\s*[A-Z0-9]{2}\s*\d{9}|' # Frankreich
                r'NL\s*\d{9}\s*B\s*\d{2}|' # Niederlande
                r'PL\s*\d{10}|'           # Polen
                r'IT\s*\d{11}'            # Italien
                r')\b', 
                re.IGNORECASE
            )
            found_ID = USt_IdNr_muster.findall(page_text)

            is_valid = None
            company_name = None
            company_address = None
            single_clean_id = None

            if found_ID:
                
                erstes_match = list(set(found_ID))[0]
                single_clean_id = re.sub(r'[\s\.\-]', '', erstes_match).upper()

                country_code = single_clean_id[:2]
                vat_number = single_clean_id[2:]

                if country_code == "GR":
                    country_code = "EL"

                # Für die Schweiz (CHE) gibt es keine EU-VIES-Abfrage
                if country_code == "CH":
                    print("Schweizer UID gefunden (keine VIES API Validierung möglich). ❌")
                else:
                    api_url = f"https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{country_code}/vat/{vat_number}"

                    try:
                        response = requests.get(api_url, timeout = 10)
                        if response.status_code == 200:
                            data = response.json()
                            is_valid = data.get("isValid", False)
                            company_name = data.get("name")
                            company_address = data.get("address")
                        else:
                            print(f"VIES API antwortete mit Status Code: {response.status_code}")
                    except Exception as e:
                        print(f"Unerwarteter Fehler bei der VIES-Abfrage: {e} ❌")

            cursor.execute("""
                           UPDATE fakeshops
                           SET USt_IdNr = ?,
                               is_valid = ?,
                               company_name = ?,
                               company_address = ?
                           WHERE URL = ?
            """, (single_clean_id, is_valid, company_name, company_address, start_url,))


        # Serverdaten mit der Python Bibliothek whois auslesen

        # Standardwerte definieren
        url_creation_date = None
        url_expiration_date = None
        url_last_update = None
        servername = None
        domain_status = None
        registered_country = None

        try: 
            # 1. Sicherstellen, dass urllib ein Schema (http://) sieht
            clean_url = url.strip()
            if not clean_url.startswith(("http://", "https://")):
                clean_url = "http://" + clean_url

            parsed_url = urlparse(clean_url)
            
            # 2. Domain herausfiltern und säubern
            domain = parsed_url.netloc or parsed_url.path
            domain = domain.split("/")[0].split(":")[0]  # Pfade und Ports entfernen
            
            if domain.startswith("www."):
                domain = domain[4:]

            # Sofort RDAP via HTTPS nutzen
            rdap_response = requests.get(f"https://rdap.org/domain/{domain}", timeout = 5)

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
                print(f"RDAP API lieferte Status-Code: {rdap_response.status_code} ❌")

        except Exception as rdap_error:
            print(f"RDAP-Abfrage fehlgeschlagen: {rdap_error} ❌")

        cursor.execute("""
                       UPDATE fakeshops
                       SET url_creation_date = ?,
                           url_expiration_date = ?,
                           url_last_update = ?,
                           servername = ?,
                           domain_status = ?,
                           registered_country = ?
                       WHERE URL = ?
        """, (url_creation_date, url_expiration_date, url_last_update, servername, domain_status, registered_country, start_url,)) 
        connection.commit()
        browser.close() 