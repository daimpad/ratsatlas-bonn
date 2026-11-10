# Strukturdaten Bonn – Neuberechnung mit der aktuellen Geometrie

Stand 10.11.2026 · Entscheidungen des Auftraggebers vom 10.11.2026: erst Vergleich, dann Freigabe; Hinweis in der täglichen Prüfung; kein Archivstand als Zwischenweg.

## Ausgangslage

Die Geometrie der statistischen Bezirke der Stadt (`stadtplan.bonn.de/geojson?OD=4859`, CC0) antwortet seit dem 10.11.2026 mit HTTP 502/504, ebenso die übrigen GeoJSON-Abrufe von stadtplan.bonn.de. Verwendet ist die Kartengeometrie des Strukturdatenatlas (Stand 2016). Die Feldnamen der Datei der Stadt sind unbekannt.

## Vorbereitet

- **Strenge Prüfung** (`stadt_geometrie`): Die Datei gilt nur als brauchbar, wenn
  - sie genau 65 Flächen enthält,
  - ein Feld genau die 65 Bezirksnummern des Atlas enthält (Name des Feldes beliebig, Zahl oder Text),
  - alle Koordinaten in WGS84 im Raum Bonn liegen,
  - jede Fläche nicht leer ist und
  - die Bezirke mindestens 95 % des Stadtgebiets abdecken. Die Kartengeometrie des Atlas erreicht wegen ihres Pixelrasters 96,4 %.
  Sonst bleibt die Geometrie von 2016, und `meta.json` nennt den Grund (`geometrie_stadt`).
- **Vergleich** (`audit_geometrie_vergleich.tsv`, langes Format: Ebene, Raum, Merkmal, alt, neu, Befund):
  - je Bezirk: Fläche (genähert), Überdeckung der beiden Flächen, Einwohner nach Zensus 2022, zugeordneter Ortsteil;
  - je Ortsteil: zusammengesetzte Bezirke, Zahl der Werte und geänderte Werte.
  Die Zusammenfassung steht in `meta.json` (`geometrie_vergleich`).
- **Freigabe:** `GEOMETRIE_FREIGEGEBEN = False` in `pipeline/strukturdaten.py`. Bis zur Freigabe bleiben Flächen, Zuordnung und Werte je Ortsteil unverändert.
- **Hinweis:** `live.yml` meldet täglich, sobald `OD=4859` 65 Flächen liefert und das Repository noch die Geometrie des Atlas nutzt.

## Ablauf, sobald der Hinweis erscheint

1. `python -m pipeline strukturdaten` ausführen. Der Schritt prüft die Datei und schreibt den Vergleich.
2. Vergleich im Gespräch durchsehen: Bezirke mit Überdeckung unter 95 %, geänderte Ortsteile, geänderte Werte je Ortsteil.
3. Nach Freigabe `GEOMETRIE_FREIGEGEBEN = True` setzen, den Schritt erneut ausführen und einen Pull Request mit den neuen Dateien öffnen.

## Prüfung

- Tests mit erfundenen Flächen: Feldnamen und Nummern als Zahl oder Text; Abbruch bei fehlenden Flächen, fremden Nummern, anderem Koordinatensystem und Lücken; Vergleich mit verschobenem Bezirk.
- Gegenprobe mit echten Flächen: Die Kartengeometrie des Atlas, als Datei der Stadt behandelt, besteht die Prüfung. Der Vergleich mit sich selbst ergibt keine Abweichung, und der ganze Schritt liefert mit und ohne Freigabe dieselben Werte.
