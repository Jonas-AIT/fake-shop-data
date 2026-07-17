# Author: Jonas Sheikh
# AIT Austrian Institute of technology
# description: API for the C programm "statusabfrage.C"

from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)
LOCKFILE = "/tmp/check_watchlist.lock"

@app.route("/test/<int:anzahl>", methods = ["POST"])
def run_check(anzahl):
    if os.path.exists(LOCKFILE):
        return jsonify({"status": "abgelehnt", "Grund": "Bereits Laufende Pruefung"})
    
    def starten():
        with open(LOCKFILE, "w") as f:
            f.write(str(os.getpid()))
        try:
            subprocess.run(["./check_watchlist.sh", str(anzahl)])
        finally:
            if os.path.exists(LOCKFILE):
                os.remove(LOCKFILE)

    import threading
    threading.Thread(target = starten, daemon = True).start()
    return jsonify({"status": "gestartet", "anzahl": anzahl}), 202

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 8000)