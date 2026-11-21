# Paket D: UX und Barrierefreiheit (21.11.2026)

Umsetzung zu `BERICHT_2026-11.md`, Nr. 13–17, 19, 41–43.

| Nr. | Umgesetzt |
|---|---|
| 13 | Flächen und Punkte der Karte (SVG-Pfade) sind keine Tab-Stopps mehr. Tab-Stopps in der Karte: Endenich 33 statt 86, mit Ebene Bebauungspläne 33 statt über 700, Stadtbezirk Bonn 9 statt 13. Sammelpunkte bleiben erreichbar und heißen für Vorleseprogramme „N Vorlagen an dieser Stelle, vergrößern“. |
| 14 | Das Suchmenü öffnet sich beim Klick, beim Tippen und mit Pfeil nach unten, nicht mehr beim Fokus, und schließt, wenn der Fokus Suchfeld und Menü verlässt. Der Titel auf dem Telefon ist ein Link (Rückweg zu „Los geht's“ per Tastatur); bei 390 und 320 px bleibt „Los geht's“ beim Durchtabben offen. |
| 15 | Verlauf des Browsers: Wechsel des Gebiets und des Vorgangs legen Einträge an; Zurück schließt den Vorgang bzw. führt zum vorigen Gebiet, Vor stellt ihn wieder her. Filter, Zeitraum und Ebenen ersetzen den Eintrag wie bisher. |
| 16 | Hinweis im Suchmenü und auf der Übersicht `thema/`: Die Themen des Filters (alle Vorlagen seit 2019, grob) und die Themenseiten (enger, ab November 2025) sind verschiedene Auswahlen, auch bei gleichem Namen. |
| 17 | Assistent: Links zu den Videos der Sitzungen (YouTube), zur Seite der Ratstranskripte und zu den Quellen der Zahlen zum Gebiet werden angezeigt. Das Suchwort für die Transkripte steht als Text daneben, nicht in der Adresse (Systemprompt v0.9, Vermerk 31). Plan-PDFs mit Leerzeichen im Namen sind verlinkbar. |
| 19 | Assistent: Verbrauch je Antwort und im Gespräch (Tokens laut Anbieter) in der Fußzeile; ab 60.000 Eingabe-Tokens ein Hinweis auf „Neues Gespräch“. Der Verlauf wird nicht gekürzt (siehe unten). |
| 41 | Fokus nach dem Schließen: Dialoge „Über“ und „Was ist neu?“ geben ihn an das Menü „Über“ bzw. auf dem Telefon an „Menü“ zurück; auf dem Telefon führt das Schließen des Vorgangs zurück zur Liste und zum gewählten Eintrag. |
| 42 | Begriffe: Überschrift im Dialog „Wie verlässlich sind die Angaben?“ wie die Kachel im Menü; README mit „Ort belegt / erkannt / unklar“; Schaltfläche zum Einklappen nennt den Inhalt („Vorgang einklappen“); Zoom-Schaltflächen auf Deutsch. |
| 43 | Assistent: Verbindungsabriss als Netzwerkfehler gemeldet, Hinweis bei leerer oder abgeschnittener Antwort, die Frage bleibt nach einem Fehler im Eingabefeld. |

Nicht umgesetzt:

- Kürzen älterer Werkzeugergebnisse im Verlauf des Assistenten (Teil von Nr. 19): Es verändert, was das Modell von früheren Schritten weiß, und braucht eine Auswertung mit echtem Anbieter (`eval.yml`). Vorschlag: nach den Testläufen mit Anthropic und Mistral entscheiden.
- Rückgabe des Fallback-Blocks an Anthropic (im Bericht „ungeprüft“): nur mit echtem Anbieter prüfbar.

Prüfung: Unit-Tests JavaScript (Links, Werkzeuge, Prompt-Fassung); Browser-Tests gegen die Vorschau; axe in 95 Zuständen bei 1440, 1024 und 390 px ohne Verstoß; Tab-Protokoll bei 1440 und 390 px ohne verdeckte oder unbenannte Stopps; Zurück und Vor auf Desktop und Telefon; Suchmenü per Tastatur.
