# FAKE SHOP DATA

Das Projekt liest automatisiert Daten aus fakehops aus, welche entweder manuell eingegeben
oder von der Watchlist Internet als solche markiert wurden.

## Über das Projekt

Das Projekt wurde ins Leben gerufen, um die Strafverfolgung von fakeshop-Betreibern
zu vereinfachen. Es automatisiert die Extraktion von allen relevanten Daten, die später
genutzt werden können, um Muster in den fakes zu erkennen.

## Features

**Automatische URL Suche:** Dieses Feauture ist nach hochfahren der API automatisch aktiviert. Die
                            Watchlist Internet wird nach allen als betrügerische Fakeshops gelisteten
                            URLs durchsucht und von diesen automatisch Daten extrahiert.

**Manuelle URL Suche:**     Um auch spezielle URLs überprüfen zu können, gibt es auf der API eine 
                            Funktion "manual test". Mit dieser kann eine eingegebene URL direkt
                            durchsucht werden, ohne das diese auf der Watchlist eingetragen ist.

**Download & results:**     Mit den Funktionen "download data" und "results" kann die gesamte Datenbank
                            eingesehen oder heruntergeladen werden. Beide Funktionen sind nebeneinander 
                            auf der API zu finden.

## Gebaut mit / Technologien
verwendete Haupttechnologien und Programmiersprachen

- Haupt API (Python 3.12, HTML, CSS)
- Statusabfrage (C, SQLite 3)
- shop-data (Python 3.12, SQLite 3)
- Packaging (DOCKER)

## Maßgeschneiderte Bibliotheken
Aufgrund der speziellen Aufgabe wurden einige Bibliotheken mit maßgeschneiderten Funktionen eingebunden

**Playwright:** Öffnet eigenen Bowser und sieht auch mit JavaScript nachgeladenen Daten.

**Googles libphonenumber:** (Python: pyphonenumber) erkennt, strukturiert und prüft Telefonnummern

**pypostal:** erkennt, strukturiert und prüft angegebene Adressen in allen Formaten

## Konfiguration
in der.env Datei können Werte festgelegt werden, um die Geschwindigkeit und Lage des Programms 
zu kontrollieren. 

**PORT:** Legt fest, an welchem PORT die Haupt API (api_wrapper.py) laufen soll

**SCHDULE_INTERVALL_MINUTES:** Legt fest, wie viel Zeit zwischen den automatischen Test sein soll

**SITES_TO_CHECK:** Legt fest, wie viele Seiten pro automatischem Durchlauf kontrolliert werden sollen.

Um überlappende Testanfragen zu vermeiden bitte mindestens 5 Sekunden pro Seite einplanen.

## Installation

1. Herunterladen & entpacken der ZIP Datei
2. CMD öffnen
3. in den Ordner "Statusabfrage" navigieren
4. DOCKER compose up --build eingeben
5. ca. 10min für den Download warten
