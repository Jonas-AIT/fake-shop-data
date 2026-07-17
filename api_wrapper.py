# Author: Jonas Sheikh
# AIT Austrian Institute of technology
# description: API for the eintire Project"

import os
import subprocess
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from dotenv import load_dotenv
import schedule
import time
import threading
import requests

load_dotenv()

FILE_NAME = "data/statusvalues.csv"
SCHEDULE_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", 10)) # Fallback-Wert = 10
PORT = int(os.getenv("PORT", 8000))
NUMBER_OF_SITES = int(os.getenv("SITES_TO_CHECK", 40))
C_SERVICE_URL = os.getenv("C_SERVICE_URL", "http://c-service:8000")  

app = Flask(__name__)

@app.route("/test/<number_of_sites>")
def run_watchlist(number_of_sites):
    try:
        resp = requests.post(f"{C_SERVICE_URL}/test/{number_of_sites}", timeout = 5)
        if resp.status_code == 409:
            print("[Hinweis] Es laeuft bereits eine Pruefung, neuer Trigger wurde abgelehnt", flush = True)
    except requests.exceptions.RequestException as e:
        print(f"[Fehler] C-Service nicht erreichbar: {e}", flush = True)
    return jsonify({"status": "finished"})    

def trigger_watchlist_check(number_of_sites):
    """Startet die Watchlist-Prüfung, nur für die Automatik"""
    try:
        requests.post(f"{C_SERVICE_URL}/test/{number_of_sites}", timeout = 5)
    except requests.exceptions.RequestException as e:
        print(f"[Scheduler-Fehler] C-Service nicht erreichbar: {e}", flush=True)

def run_scheduler():
    print(f"[Scheduler] Thread gestartet, Intervall: {SCHEDULE_MINUTES} Minuten", flush=True)
    schedule.every(SCHEDULE_MINUTES).minutes.do(trigger_watchlist_check, NUMBER_OF_SITES)
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/forward_test', methods = ['POST'])
def forward_test():
    chosen_id = requests.form.get('ammount_tests')
    return redirect(url_for('run_watchlist', number_of_sites = chosen_id))

@app.route("/results")
def show_results():
    if not os.path.exists(FILE_NAME):
        return "<pre>Es liegen noch keine Testergebnisse vor.</pre>"

    with open(FILE_NAME, 'r') as file:
        zeilen = file.readlines()

    # "sep=;"-Zeile überspringen
    zeilen = [z for z in zeilen if not z.startswith("sep=")]

    rows_html = ""
    for zeile in zeilen:
        teile = zeile.strip().split(";")
        if len(teile) != 3:
            continue
        url, status, zeit = teile

        # Farbe je nach Status bestimmen
        if status == "200":
            farbe = "green"
        elif status == "---":
            farbe = "gray"
        else:
            farbe = "red"

        rows_html += f"""
        <tr>
            <td>{url}</td>
            <td style="color:{farbe}; font-weight:bold;">{status}</td>
            <td>{zeit}</td>
        </tr>
        """

    html = f"""
    <table border="1" cellpadding="8" style="border-collapse: collapse;">
        <tr><th>URL</th><th>Status</th><th>Zeitpunkt</th></tr>
        {rows_html}
    </table>
    """
    return html

@app.route("/results/download")
def download_results():
    if os.path.exists(FILE_NAME):
        return send_file(
            FILE_NAME,
            mimetype = 'text/csv',
            as_attachment = True,
            download_name = FILE_NAME
        )
    else:
        return "<pre>Es liegen noch keine Testergebnisse vor. Bitte starte zuerst einen Websitetest.</pre>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = PORT)
    #app.run(debug = True)

