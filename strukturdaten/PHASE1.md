# Strukturdaten Bonn – Phase 1 (Adapter)

Stand 10.11.2026 · Freigabe des Plans durch den Auftraggeber am 10.11.2026

## Umsetzung

- `pipeline/strukturdaten.py`, Schritt `strukturdaten`. Er läuft auf Knopfdruck und lokal, weil sich der Atlas etwa einmal im Jahr ändert. Der Schritt erledigt drei Dinge:
  - Abruf nach `_strukturdaten_dl/`; das Ordner liegt nicht im Repository
  - Aufbereitung nach `data/strukturdaten/`
  - Prüfung (`pruefen`)
- Ausgabe nach dem Datenvertrag „Strukturdaten v1“ (Entwurf `1.0-entwurf`):

| Datei | Inhalt |
|---|---|
| `indikatoren.tsv` | 83 Indikatoren: 71 aus dem Atlas (58 Indikatoren, davon drei Verteilungen mit zusammen 16 Kategorien als eigene Anteile), 12 aus dem Wegweiser Kommune |
| `werte.tsv` | 48.930 Werte, ein Wert je Zeile: 65 statistische Bezirke, 4 Stadtbezirke, ganz Bonn; Status `ok`, `geheim` oder `fehlt` |
| `raum/statistischer_bezirk.geojson`, `raum/stadtbezirk.geojson` | Geometrien mit `raum_id`, `name`, `raumebene`, `eltern_id`, `quelle`, `lizenz` |
| `gesamtstadt.tsv` | 609 Vergleichswerte Bonn, Köln, Wuppertal (Wegweiser, alle verfügbaren Jahre) |
| `meta.json` | Datenstand des Atlas (Last-Modified 03.02.2026), Abrufdatum, Version der Wegweiser-Schnittstelle (3.12.0), Herkunft der Geometrie, Lizenzen, Hinweise |
| `audit_abruf.tsv` | je Abruf URL, Zeitpunkt, HTTP-Status, Zahl der Datensätze, SHA-256 |
| `audit_plausibilitaet.tsv` | Haushalte 2017 nicht übernommen; 30 Hinweise „Summe weicht ab“, bei denen ganz Bonn leicht über der Summe der Bezirke liegt (Beschäftigte, Bedarfsgemeinschaften, Fertigstellungen, eine Baugenehmigung); Werte unverändert |

`zuordnung.tsv` folgt in Phase 2 (Raumabgleich).

## Regeln (Entscheidungen des Auftraggebers 10.11.2026)

- Werte werden unverändert übernommen, ohne Schätzung. Typ und Einheit stammen aus dem Metatext. „Zahl der Nationalitäten“ ist eine Anzahl, lässt sich aber nicht über Gebiete summieren; die Einheit vermerkt das.
- NaN wird zu `geheim`, wenn es sich um Daten der Bundesagentur in einem bewohnten Bezirk handelt (2 Werte). Sonst wird NaN zu `fehlt`, auch in den drei nahezu unbewohnten Bezirken.
- Haushalte 2017 haben überall den Status `fehlt` (Quellfehler).
- Zähler und Nenner stehen dort, wo beide im Atlas vorkommen: Zuwandereranteil, Ausländeranteil, Bedarfsgemeinschaften je 1.000 Haushalte, geförderte Wohnungen.
- Wegweiser: nur Friendly-URLs. Ändert sich `info.version`, bricht der Lauf ab; danach `STRUKTURDATEN_NEUE_VERSION=1`.

## Abweichungen vom Plan

- Die Quellen stehen in `meta.json`, `data/LICENSE-DATA.md` und der README, nicht in `config.SOURCES`. Diese Tabelle speist die Datenbank der Vorlagen, und die Strukturdaten erscheinen noch nicht auf der Seite.
- Die Geometrie der Stadt (`OD=4859`) antwortete am 10.11.2026 mit HTTP 502/504. Verwendet ist die Kartengeometrie des Atlas (Stand 2016), gekennzeichnet in `meta.json` und je Fläche. Ein neuer Lauf nimmt die Geometrie der Stadt, sobald sie erreichbar ist.
- Für ganz Bonn gibt es keine eigene Geometrie; sie ergibt sich aus den Stadtbezirken.

## Prüfung

- `tests/test_strukturdaten.py`:
  - NaN-Regeln, Ausschluss 2017, Verteilungen, Summenprüfung, Umrechnung der Geometrie, Wegweiser-Reihen
  - Prüfung der Dateien im Repository gegen den Vertrag
- `live.yml` meldet einen neuen Stand des Atlas als Hinweis.

## Offen

- Genaue Lizenzbezeichnung aus der schriftlichen Antwort der Stadt (`LIZENZ_BONN_URL` ist leer)
- Wanderungsdaten (Bezugsweg)
- Phase 2: Raumabgleich mit der aktuellen Geometrie
