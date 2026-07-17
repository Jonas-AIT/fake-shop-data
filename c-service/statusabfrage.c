// Autor: Jonas Sheikh; AIT Austrian Institute of technology
// Projekt: Statusabfrage
// Beschreibung: Das Programm prüft anhand des Statuscodes, ob eine Website noch online ist

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h> 
#include <time.h>

#define MAX_PUFFER 255
#define Ergebnisdatei "data/statusvalues.csv"
#define MAX_CONNECTION_DURATION 3L

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

// Funktion stellt sicher, dass die Datei existiert und ggf. "sep=;" enthält
void datei_initialisieren()
{
    FILE *fp = fopen(Ergebnisdatei, "r");
    if (fp == NULL) 
    {
        // Datei existiert nicht -> Neu erstellen mit Kopfzeile
        printf("Ergebnisdatei existiert nicht. Erstelle mit Header...\n");
        FILE *new_fp = fopen(Ergebnisdatei, "w");
        if (new_fp != NULL) 
        {
            fprintf(new_fp, "sep=;\n");
            fclose(new_fp);
        }
    }
    else 
    {
        fclose(fp);
    }
}

// Funktion zum Beschreiben der CSV Datei mit den Ergebnisen
void datei_schreiben(char url[MAX_PUFFER], long response_code)
{
    FILE *fp = fopen(Ergebnisdatei, "a");
    if(fp == NULL) 
    {
        printf("Fehler beim Oeffnen der Ergebnis Datei");
        return;
    }

    char *zeit = zeit_berechnen();
    zeit[strcspn(zeit, "\n")] = '\0';

    fprintf(fp, "%s;%ld;%s\n", url, response_code, zeit);
    fclose(fp);
}

// Funktion zum Überprüfen von Duplikaten in der CSV Datei
int csv_duplikatpruefung(char url[MAX_PUFFER], long *ptr_current_line)
{
    FILE *fp = fopen(Ergebnisdatei, "r");
    if(fp == NULL) return 0;

    char csv_zeile[MAX_PUFFER];
    long aktueller_offset = 0;

    while (1) 
    {
        aktueller_offset = ftell(fp);
        if (fgets(csv_zeile, MAX_PUFFER, fp) == NULL) break;

        // Wenn die Zeile mit "sep=" beginnt, überspringen wir sie sofort
        if (strncmp(csv_zeile, "sep=", 4) == 0) {
            continue;
        }

        char zeile_kopie[MAX_PUFFER];
        strcpy(zeile_kopie, csv_zeile);
        char *gespeicherte_url = strtok(zeile_kopie, ";");

        if(gespeicherte_url != NULL && strcmp(gespeicherte_url, url) == 0)
        {
            *ptr_current_line = aktueller_offset;
            fclose(fp);
            return 1;
        }
    }
    fclose(fp);
    return 0;
}

// Funktion zu Aktualisieren des Zeitstempels & Statuscode bei bereits vorhandener URL
void datei_aktualisieren(long *ptr_current_line, char url[MAX_PUFFER], long response_code)
{
    FILE *fp = fopen(Ergebnisdatei, "r+");
    if(fp == NULL)
    {
        printf("Fehler beim Oeffnen der Ergebnis Datei\n");
        return;
    }

    fseek(fp, *ptr_current_line, SEEK_SET);
    fseek(fp, strlen(url) + 1, SEEK_CUR);

    char *aktuelle_zeit = zeit_berechnen();
    aktuelle_zeit[strcspn(aktuelle_zeit, "\n")] = '\0';

    fprintf(fp, "%3ld;%s\n", response_code, aktuelle_zeit);
    fclose(fp);
}

// Funktion zum Schreiben in die csv Datei, wenn keine Verbindung aufgebaut wurde
void datei_schreiben_netzwerkfehler(char url[MAX_PUFFER], long *ptr_current_line)
{
    if (csv_duplikatpruefung(url, ptr_current_line) == 0)
    {
        // Nicht da -> Normal anhängen
        FILE *fp = fopen(Ergebnisdatei, "a");
        if (fp == NULL) return;
        char *zeit = zeit_berechnen();
        zeit[strcspn(zeit, "\n")] = '\0';
        fprintf(fp, "%s;---;%s\n", url, zeit);
        fclose(fp);
    }
    else
    {
        // Bereits da -> Direkt in-place überschreiben
        FILE *fp = fopen(Ergebnisdatei, "r+");
        if (fp == NULL) return;

        fseek(fp, *ptr_current_line, SEEK_SET);
        fseek(fp, strlen(url) + 1, SEEK_CUR);

        char *aktuelle_zeit = zeit_berechnen();
        aktuelle_zeit[strcspn(aktuelle_zeit, "\n")] = '\0';

        // Wir schreiben manuell "---" statt der Zahl
        fprintf(fp, "---;%s\n", aktuelle_zeit);
        fclose(fp);
    }
}

int main(int argc, char *argv[]) {
    long current_line = 0;
    long *ptr_current_line = &current_line;

    // Beende das Programm, wenn keine URL eingegeben wurde
    if (argc < 2)
    {
        printf("Fehler, keine URL angeben!\n");
        return 0;
    }

    printf("URL: %s\n", argv[1]);
    
    datei_initialisieren();

    CURL *curl = curl_easy_init();

    // Prüfen, ob noch genug Speicher frei ist
    if (curl != NULL)
    {
        uebertragung_konfigurieren(curl, argv[1]);

        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK)
        {
            printf("Netzwerkfehler: %s\n", curl_easy_strerror(res));
            datei_schreiben_netzwerkfehler(argv[1], ptr_current_line);
            curl_easy_cleanup(curl);
            return 0;
        }
        else
        {
            long response_code = 0;
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);

            statusmeldung(response_code);

            if (csv_duplikatpruefung(argv[1], ptr_current_line) == 0) // URL noch nicht vorhanden
            {
                datei_schreiben(argv[1], response_code);
            }
            else 
            {
                datei_aktualisieren(ptr_current_line, argv[1], response_code); 
            }
        }
        curl_easy_cleanup(curl);
    }
    else
    {
        printf("Fehler: curl_easy_init() ist fehlgeschlagen (evtl. kein Speicher frei)\n");
        return 0;
    }
    return 0;
}