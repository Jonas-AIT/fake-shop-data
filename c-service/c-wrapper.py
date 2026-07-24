# Author: Jonas Sheikh
# AIT Austrian Institute of technology
# description: API for the C programm "statusabfrage.C"

from flask import Flask, jsonify
import subprocess
import os
import threading

app = Flask(__name__)
LOCKFILE_WATCHLIST = "/tmp/check_watchlist.lock"

@app.route("/test/<int:anzahl>", methods = ["POST"])
def run_check(anzahl):
    if os.path.exists(LOCKFILE_WATCHLIST):
        return (jsonify({"status": "abgelehnt", "Grund": "Bereits Laufende Pruefung"}), 409,)
    
    def starten():
        with open(LOCKFILE_WATCHLIST, "w") as f:
            f.write(str(os.getpid()))
        try:
            subprocess.run(["./check_watchlist.sh", str(anzahl)])
        finally:
            if os.path.exists(LOCKFILE_WATCHLIST):
                os.remove(LOCKFILE_WATCHLIST)

    import threading
    threading.Thread(target = starten, daemon = True).start()
    return (jsonify({"status": "gestartet", "anzahl": anzahl}), 202,)

@app.route("/manual_test/<path:url>", methods = ["POST"])
def manual_check(url):
        try:
            subprocess.run(["./statusabfrage", url], capture_output=True, text=True, check=True, timeout=40)    
            return (jsonify({"status": "erfolgreich", "Grund": "selbsterklärend"}), 200)
        except subprocess.CalledProcessError as e:
                return (jsonify({"status": "error", "message": f"Fehler bei Ausfuehrung: {e.stderr}",}),500,)        

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 8000)