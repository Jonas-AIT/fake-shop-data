// Autor: Jonas Sheikh; AIT Austrian Institute of technology
// Projekt: Statusabfrage
// Beschreibung: Das Programm prüft anhand des Statuscodes, ob eine Website noch online ist

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h> 
#include <time.h>
#include <sqlite3.h>

#define MAX_PUFFER 255
#define Ergebnisdatei "data/statusvalues.csv"
#define MAX_CONNECTION_DURATION 8L

// Callback-Funktion wird für jede Zeile aufgerufen, die von sqlite3_exec zurückgegeben wird
static int callback(void *data, int argc, char **argv, char **azColName) {
    for (int i = 0; i < argc; i++) {
        printf("%s: %s\n", azColName[i], argv[i] ? argv[i] : "NULL");
    }
    printf("\n");
    return 0;
}

// Funktion zum Erstellen der SQLite Datenbank Tabelle fakeshops
void tabelle_erstellen(sqlite3 *db, int rc, char *zErrMsg)
{
    const char *sql_create = "CREATE TABLE IF NOT EXISTS fakeshops(" \
                            "ID INTEGER PRIMARY KEY AUTOINCREMENT," \
                            "URL TEXT," \
                            "status INTEGER," \
                            "title TEXT," \
                            "language TEXT," \
                            "email1 TEXT," \
                            "email2 TEXT," \
                            "phonenumber TEXT," \
                            "phonenumber_location TEXT," \
                            "phonenumber_carrier TEXT," \
                            "address TEXT," \
                            "url_creation_date TEXT," \
                            "url_expiration_date TEXT," \
                            "url_last_update TEXT," \
                            "servername TEXT," \
                            "domain_status TEXT," \
                            "registered_country TEXT," \
                            "USt_IdNr TEXT," \
                            "is_valid BOOLEAN," \
                            "company_name TEXT," \
                            "company_address TEXT," \
                            "date TIMESTAMP DEFAULT (datetime('now', 'localtime')));";

    // 2. Tabelle erstellen
    rc = sqlite3_exec(db, sql_create, callback, 0, &zErrMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL-Fehler: %s ❌\n", zErrMsg);
        sqlite3_free(zErrMsg);
    }                        
}

// Funktion zum Konfigurieren des cURL Übertragungsvorgangs
void uebertragung_konfigurieren(CURL *curl, char url[MAX_PUFFER])
{
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_NOBODY, 1L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    // User Agent
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

    // Timeouts, damit das Programm bei toten/langsamen Servern nicht ewig haengt
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, MAX_CONNECTION_DURATION);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, MAX_CONNECTION_DURATION);  // max. 4s fuer die gesamte Anfrage
}

// Funktion, zum Ausgeben des Statuscodes & dessen Beschreibung auf der Konsole
void statusmeldung(long response_code)
{
    switch(response_code)
    {
        case 200: printf("Statuscode: %ld\nDer Server ist aktiv\n", response_code); break;
        case 403: printf("Statuscode: %ld\nDer Zugriff aus den Server ist verboten\n", response_code); break;
        case 404: printf("Statuscode: %ld\nDer Server ist nicht erreichbar\n", response_code); break;
        case 504: printf("Statuscode: %ld\nDer Server ist ueberlastet / Wartungsarbeiten\n", response_code); break;
        default: printf("Statuscode: %ld\n", response_code);
    }
}

// Funktion zum Berechnen der aktuellen Zeit
char* zeit_berechnen()
{
    time_t sec_since_1970;
    struct tm* local_time;
    char *ptr_timestring;

    sec_since_1970 = time(NULL);
    local_time = localtime(&sec_since_1970);
    ptr_timestring = asctime(local_time);

    return ptr_timestring;
}

// Funktion zum Beschreiben der CSV Datei mit den Ergebnisen
void datei_schreiben(char url[MAX_PUFFER], long response_code, sqlite3 *db, int rc, char *zErrMsg)
{
    char sql_insert[512];
    snprintf(sql_insert, sizeof(sql_insert), 
         "INSERT INTO fakeshops (url, status) VALUES ('%s', %ld);", 
         url, response_code);

    rc = sqlite3_exec(db, sql_insert, callback, 0, &zErrMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL-Fehler beim Einfügen: %s\n", zErrMsg);
        sqlite3_free(zErrMsg);
    }
    sqlite3_close(db);

    if (response_code == 200)
    {
        char command[MAX_PUFFER];
        snprintf(command, sizeof(command), "python3 shop-data.py %s", url);

        int ret = system(command);
        if (ret != 0) {
            fprintf(stderr, "[Fehler] Python-Skript konnte nicht erfolgreich ausgeführt werden! Return-Code: %d ❌\n", ret);
        }
    }
}

// Funktion zum Überprüfen von Duplikaten in der Datenbank
int csv_duplikatpruefung(char url[MAX_PUFFER], sqlite3 *db)
{
    sqlite3_stmt *stmt;
    const char *sql = "SELECT 1 FROM fakeshops WHERE URL = ? LIMIT 1;";
    int existiert = 0;

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        // Die URL sicher an das '?' binden
        sqlite3_bind_text(stmt, 1, url, -1, SQLITE_STATIC);

        // Zeile abrufen: Wenn SQLITE_ROW zurückkommt, gibt es den Eintrag
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            existiert = 1;
        }
    }

    sqlite3_finalize(stmt);
    return existiert; // Gibt 1 zurück wenn vorhanden, sonst 0
}

// Funktion zu Aktualisieren des Zeitstempels & Statuscode bei bereits vorhandener URLs
void datei_aktualisieren(char url[MAX_PUFFER], long response_code, sqlite3 *db, int rc, char *zErrMsg)
{
    char sql_update[512];
    snprintf(sql_update, sizeof(sql_update), 
         "UPDATE fakeshops SET status = %ld, date = datetime('now', 'localtime') WHERE url = '%s';", 
         response_code, url);

    rc = sqlite3_exec(db, sql_update, callback, 0, &zErrMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL-Fehler beim Einfügen: %s\n", zErrMsg);
        sqlite3_free(zErrMsg);
    }
    sqlite3_close(db);

    if (response_code == 200)
    {
        char command[MAX_PUFFER];
        snprintf(command, sizeof(command), "python3 shop-data.py %s", url);

        int ret = system(command);
        if (ret != 0) {
            fprintf(stderr, "[Fehler] Python-Skript konnte nicht erfolgreich ausgeführt werden! Return-Code: %d ❌\n", ret);
        }
    }
}

// Funktion zum Schreiben in die csv Datei, wenn keine Verbindung aufgebaut wurde
void datei_schreiben_netzwerkfehler(char url[MAX_PUFFER], sqlite3 *db, int rc, char *zErrMsg)
{
    long response_code = 000;

    if (csv_duplikatpruefung(url, db) == 0)
    {
        // Nicht da -> Normal anhängen
        char sql_insert[512];
        snprintf(sql_insert, sizeof(sql_insert), 
             "INSERT INTO fakeshops (url, status) VALUES ('%s', %ld);", 
             url, response_code);

        rc = sqlite3_exec(db, sql_insert, callback, 0, &zErrMsg);
        if (rc != SQLITE_OK) {
            fprintf(stderr, "SQL-Fehler beim Einfügen: %s\n", zErrMsg);
            sqlite3_free(zErrMsg);
        }    
    }
    else {
        char sql_update[512];
        snprintf(sql_update, sizeof(sql_update), 
         "UPDATE fakeshops SET status = %ld, date = datetime('now', 'localtime') WHERE url = '%s';", 
         response_code, url);

        rc = sqlite3_exec(db, sql_update, callback, 0, &zErrMsg);
        if (rc != SQLITE_OK) {
            fprintf(stderr, "SQL-Fehler beim Einfügen: %s ❌\n", zErrMsg);
            sqlite3_free(zErrMsg);
        }
    }
    sqlite3_close(db);
}

int main(int argc, char *argv[]) {

    sqlite3 *db;
    char *zErrMsg = 0;
    int rc;

    // Beende das Programm, wenn keine URL eingegeben wurde
    if (argc < 2)
    {
        printf("Fehler, keine URL angeben! ❌\n");
        return 0;
    }

    printf("URL: %s\n", argv[1]);
    
    // datei_initialisieren();
    rc = sqlite3_open("data/fakeshops.db", &db);

    char full_path[512];
    if (realpath("data/fakeshops.db", full_path) != NULL) {
        printf("[DEBUG] Datenbank wird geöffnet unter: %s ", full_path);
    }

    if (rc != SQLITE_OK) {
        fprintf(stderr, "Kann Datenbank nicht öffnen: %s ❌\n", sqlite3_errmsg(db));
        return 1;
    } else {
        fprintf(stdout, "✅\n");
    }

    tabelle_erstellen(db, rc, zErrMsg);

    CURL *curl = curl_easy_init();

    // Prüfen, ob noch genug Speicher frei ist
    if (curl != NULL)
    {
        uebertragung_konfigurieren(curl, argv[1]);

        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK)
        {
            printf("Seite nicht erreichbar: %s 💀\n", curl_easy_strerror(res));
            datei_schreiben_netzwerkfehler(argv[1], db, rc, zErrMsg);
            curl_easy_cleanup(curl);
            return 0;
        }
        else
        {
            long response_code = 0;
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);

            statusmeldung(response_code);

            if (csv_duplikatpruefung(argv[1], db) == 0) // URL noch nicht vorhanden
            {
                datei_schreiben(argv[1], response_code, db, rc, zErrMsg);
            }
            else 
            {
                datei_aktualisieren(argv[1], response_code, db, rc, zErrMsg); 
            }
        }
        curl_easy_cleanup(curl);
    }
    else
    {
        printf("Fehler: curl_easy_init() ist fehlgeschlagen (evtl. kein Speicher frei) ❌\n");
        return 0;
    }
    return 0;
}