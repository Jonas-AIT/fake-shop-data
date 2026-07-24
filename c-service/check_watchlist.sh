#!/bin/bash
#
# check_watchlist.sh
# Holt Domains von der offiziellen Watchlist Internet
# (https://www.watchlist-internet.at/liste-betruegerischer-shops/)
# und prueft sie mit dem C-Programm "statusabfrage".
#
# Verwendung: ./check_watchlist.sh [ANZAHL]
#   ./check_watchlist.sh        -> prueft 20 Domains (Standard)
#   ./check_watchlist.sh 100    -> prueft 100 Domains
set -uo pipefail

# Keine Core-Dumps erzeugen (verhindert core-Dateien im Arbeitsverzeichnis 
# bei jedem Absturz von statusabfrage)
ulimit -c 0

BASE_URL="https://www.watchlist-internet.at/liste-betruegerischer-shops/"
ANZAHL="${1:-20}"
PROGRAMM="./statusabfrage"
PROGRAMM_TIMEOUT=45   # Sekunden, nach denen ein haengender/abstuerzender Aufruf abgebrochen wird
PAUSE_SEKUNDEN=0.1      # Hoeflichkeitspause zwischen Seitenabrufen

if [ ! -x "$PROGRAMM" ]; then
    echo "Fehler: '$PROGRAMM' existiert nicht oder ist nicht ausfuehrbar."
    echo "Kompilieren mit: gcc statusabfrage.c -o statusabfrage -lcurl"
    exit 1
fi

if ! [[ "$ANZAHL" =~ ^[0-9]+$ ]]; then
    echo "Fehler: '$ANZAHL' ist keine gueltige Zahl."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Fehler: python3 wird zum Parsen der Seite benoetigt, ist aber nicht installiert."
    exit 1
fi

echo "Lade Domains von der Watchlist Internet..."
echo "----------------------------------------"

domains_datei=$(mktemp)
trap 'rm -f "$domains_datei"' EXIT

seite=1
gefunden=0

while [ "$gefunden" -lt "$ANZAHL" ]; do
    if [ "$seite" -eq 1 ]; then
        url="$BASE_URL"
    else
        url="${BASE_URL}?tx_solr%5Bpage%5D=${seite}"
    fi

    html=$(curl -fsS -A "Mozilla/5.0" "$url") || {
        echo "Fehler beim Laden von Seite $seite. Breche ab."
        break
    }

    # Extrahiert Domainnamen aus Links wie:
    # <a href=".../liste-betruegerischer-shops/shop/techeco-outilscom/" class="...">tech.eco-outils.com</a>
    neue_domains=$(echo "$html" | python3 -c '
import sys, re
html = sys.stdin.read()
pattern = re.compile(r"href=\"[^\"]*?/shop/[^\"]+/\"[^>]*>\s*([^<]+?)\s*<", re.DOTALL)
for match in pattern.finditer(html):
    text = match.group(1).strip()
    if text and "." in text and " " not in text:
        print(text)
')

    if [ -z "$neue_domains" ]; then
        echo "Keine weiteren Domains auf Seite $seite gefunden. Ende der Liste erreicht."
        break
    fi

    echo "$neue_domains" >> "$domains_datei"
    sort -u "$domains_datei" -o "$domains_datei"
    gefunden=$(wc -l < "$domains_datei")
    echo "Seite $seite geladen (insgesamt $gefunden Domains gesammelt)..."

    seite=$((seite + 1))
    sleep "$PAUSE_SEKUNDEN"
done

echo "----------------------------------------"
echo "Starte Ueberpruefung mit dem C-Programm fuer $ANZAHL Domain(s)..."
echo "----------------------------------------"

head -n "$ANZAHL" "$domains_datei" | while read -r domain; do
    domain=$(echo "$domain" | tr -d '\r' | xargs)
    [ -z "$domain" ] && continue

    url="https://$domain"

    # timeout verhindert, dass ein haengendes statusabfrage die ganze Pruefung blockiert;
    # der Exit-Code wird ausgewertet, um Abstuerze klar (statt als rohen Kernel-Log) zu melden
    timeout "$PROGRAMM_TIMEOUT" "$PROGRAMM" "$url"
    rc=$?

    if [ "$rc" -eq 139 ]; then
        echo ">> statusabfrage ist mit Segmentation Fault abgestuerzt bei: $url"
    elif [ "$rc" -eq 124 ]; then
        echo ">> statusabfrage hat das Zeitlimit (${PROGRAMM_TIMEOUT}s) ueberschritten bei: $url"
    elif [ "$rc" -ne 0 ]; then
        echo ">> statusabfrage endete mit Fehlercode $rc bei: $url"
    fi

    echo "----------------------------------------"
done