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
                            URLs durchsucht und von diesen automatsch Daten extrahiert.

**Manuelle URL Suche:**     Um auch spezielle URLs überprüfen zu können, gibt es auf der API eine 
                            Funktion "manual test". Mit dieser kann eine eingegebene URL direkt
                            durchsucht werden, ohne das diese auf der Watchlist eingetragen ist.

**Download & results:**     Mit den Funktionen "download data" und "results" kann die gesamte Datenbank
                            eingesehen oder heruntergeladen werden. Bei Funktionen sind nebeneinander 
                            auf der API zu finden.

## Gebaut mit / Technologien
verwendete Haupttechnologien und Programmiersprachen

- Haupt API (Python 3.12, HTML, CSS)
- Statusabfrage (C, SQLite 3)
- shop-data (Python 3.12, SQLite 3)
- Packaging (DOCKER)

## Maßgeschneiderte Bibliotheken
Aufgrund der bsonderen Aufgabe wurden einige spezielle Bibliotheken eingebunden

**Playwright** {Öffnet eigenen Bowser und sieht auch mit JavaScript nachgeladenen Daten.}
**Googles libphonenumber** {(Python: pyphonenumber) erkennt, strukturiert und prüft Telefonnummern}
**pypostal** {erkennt, strukturiert und prüft angegebene Adressen in allen Formaten}

## Installation

1. Herunterladen & entpacken der ZIP Datei
2. CMD öffnen
3. in den Ordner "Statusabfrage" navigieren
4. DOCKER compose up --build eingeben
5. ca. 10min für den Download warten
