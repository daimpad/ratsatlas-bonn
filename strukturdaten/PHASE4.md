# Strukturdaten Bonn – Phase 4 (Verifikation und Auslieferung)

Stand 10.11.2026 · Freigabe des Auftraggebers: „ja, Phase 4 beginnen“ (10.11.2026)

## Verifikation

Schritt `python -m pipeline strukturdaten-verifikation` (auf Knopfdruck, nicht im täglichen Lauf) → `data/strukturdaten/audit_verifikation.tsv`. Die Stichprobe ist mit festem Startwert gezogen (`SEED`) und wird gegen Quellen geprüft, die nicht der Atlas selbst sind:

| Teil | Gegenquelle | Werte | Ergebnis |
|---|---|---|---|
| A | Bezirksblätter „Soziodemographische Indikatoren“ (PDF, Stichtag 31.12.2025), vier Bezirke je zwei Kennzahlen | 8 | gleich |
| B | Jahresübersichten „Bevölkerung in Bonn“ 2020 und 2024 (PDF), je drei Werte | 6 | gleich, davon 2 gerundet (die Übersicht nennt die Dichte ganzzahlig: 5.813 statt 5.812,9; 1.269 statt 1.268,8) |
| B2 | Jahresübersicht 2024, Zeilen der zusammengefassten Bezirke | 3 | gleich |
| C | Endenich (abgeleitet): Summe der Bezirksblätter 120 und 121, Ausländeranteil aus Zähler und Nenner | 2 | gleich |
| D | Bezirksblatt: Spalten Stadtbezirk und Stadt Bonn | 2 | gleich |
| E | Wegweiser Kommune über den CSV-Export (zweiter Abrufweg) | 2 | gleich |

Ergebnis: 23 von 23 Werten gleich, davon 2 nur nach Rundung der Gegenquelle.

## Befund: zusammengefasste Bezirke

Die Jahresübersicht weist drei nahezu unbewohnte Bezirke zusammen mit dem Nachbarbezirk aus: „127 Röttgen u. Kottenforst (129)“, „381 Geislar u. Siegaue (380)“, „388 Holtorf u. Ennert (389)“. Die Werte des Atlas für 127, 381 und 388 stimmen mit diesen Zeilen überein. Bisher hieß es, die drei Bezirke seien „in der Quelle ohne Werte“. Berichtigt:
- `meta.json`: Ihre Einwohner sind in den Werten der Bezirke 127, 381 und 388 enthalten.
- Karte: Tooltip „ohne eigenen Wert: in Bezirk … enthalten“; Legende entsprechend.
- Werte und Status bleiben unverändert (`fehlt`, wie im Datenvertrag); keine Umverteilung.
- Raumabgleich: 129 liegt wie 127 in Röttgen; 380 (überwiegend Schwarzrheindorf/Vilich-Rheindorf) und 389 (überwiegend Holtorf) haben laut Zensus zusammen weniger als 100 Einwohner. Die Wirkung auf die Werte je Ortsteil ist daher gering; bei der Neuberechnung mit der aktuellen Geometrie wird sie ausgewiesen.

## Auslieferung

- Datenpaket: Ordner `strukturdaten/` (alle Dateien nach dem Datenvertrag mit Audits) und `berichte/strukturdaten/` (Phasen 0 bis 4); `bonn/strukturdaten.json` wie bisher; Abschnitt im LIESMICH.
- DCAT: Distribution „Strukturdaten je statistischem Bezirk (JSON)“, Lizenz CC0 (Freigabe der Stadt: CC0 bzw. dl-de/zero-2.0).
- Lizenzhinweise: `LICENSE-DATA.md` (mit `audit_verifikation.tsv`), README, Quellen auf der Seite und `meta.json`.
- Datenstand: `meta.json` (`datenstand`, `abrufdatum`), auf der Seite in Legende und Steckbrief.

## Offen

- Neuberechnung des Raumabgleichs mit der aktuellen Geometrie, sobald `stadtplan.bonn.de/geojson?OD=4859` antwortet.
- Genaue Lizenzbezeichnung aus der schriftlichen Antwort der Stadt.
- Wanderungsdaten (Bezugsweg).
