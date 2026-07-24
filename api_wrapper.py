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
import sqlite3

load_dotenv()

FILE_NAME = "data/fakeshops.db"
SCHEDULE_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", 10)) # Fallback-Wert = 10
PORT = int(os.getenv("PORT", 8000))
NUMBER_OF_SITES = int(os.getenv("SITES_TO_CHECK", 40))
C_SERVICE_URL = os.getenv("C_SERVICE_URL", "http://c-service:8000")  

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "fakeshops.db")

def get_shop_by_url(url):
    # Verwende den absoluten Pfad zur DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM fakeshops WHERE URL = ? ORDER BY ID DESC LIMIT 1", (url,)
    )
    shop_data = cursor.fetchone()
    conn.close()
    return shop_data

app = Flask(__name__)

@app.route("/manual_test", methods=["POST"])
def manual_test():
    input_url = request.form.get("shop_url")
    shop_info = None

    if input_url:
        try:       
            resp = requests.post(f"{C_SERVICE_URL}/manual_test/{input_url}", timeout = 40)
            if resp.status_code == 409:
                print("[Hinweis] Es laeuft bereits eine Pruefung, neuer Trigger wurde abgelehnt ⚠️", flush = True)
            elif resp.status_code == 200:
                shop_info = get_shop_by_url(input_url)

        except requests.exceptions.RequestException as e:
            print(f"[Fehler] C-Service nicht erreichbar: {e}", flush = True)
    return render_template('test.html', shop=shop_info)    
        

@app.route("/test/<number_of_sites>")
def check_watchlist(number_of_sites):
    try:
        resp = requests.post(f"{C_SERVICE_URL}/test/{number_of_sites}", timeout = 40)
        if resp.status_code == 409:
            print("[Hinweis] Es laeuft bereits eine Pruefung, neuer Trigger wurde abgelehnt", flush = True)
    except requests.exceptions.RequestException as e:
        print(f"[Fehler] C-Service nicht erreichbar: {e}", flush = True)
    return render_template('index.html')    

def trigger_watchlist_check(number_of_sites):
    """Startet die Watchlist-Prüfung, nur für die Automatik"""
    try:
        requests.post(f"{C_SERVICE_URL}/test/{number_of_sites}", timeout = 40)
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

@app.route("/results/download")
def download_results():
    if os.path.exists(FILE_NAME):
        return send_file(
            FILE_NAME,
            mimetype = 'application/x-sqlite3',
            as_attachment = True,
            download_name = FILE_NAME
        )
    else:
        return "<pre>Es liegen noch keine Testergebnisse vor. Bitte starte zuerst einen Websitetest.</pre>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = PORT)
    #app.run(debug = True)

