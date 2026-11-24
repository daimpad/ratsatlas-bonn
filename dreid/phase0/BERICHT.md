# 3D-Darstellung – Phase 0

Stand 24.11.2026 · Entscheidung des Auftraggebers vom 24.11.2026: Prüfung einer eigenen 3D-Seite nach dem Vorbild des Stadtmonitors Witzenhausen. Die Hauptkarte bleibt Leaflet; Produktionscode entsteht noch nicht.

## 1. Ergebnis in Kürze

- **Machbar mit offenen Daten und ohne fremde Dienste.**
  - Gebäudehöhen kommen aus dem 3D-Gebäudemodell LoD1 von Geobasis NRW (dl-de/zero-2.0). Der Ratsatlas würde sie selbst aufbereiten und vom eigenen Server ausliefern.
  - Dargestellt wird mit MapLibre GL auf einer eigenen Seite.
- **Der Prototyp zeigt zwei Ansichten** (Bilder in `bilder/`):
  1. **Endenich:** 3.561 Gebäude in Grau; die 46 Vorlagen der letzten 12 Monate stehen an 23 Orten als Säulen. Die Höhe folgt der Zahl der Vorlagen, die Farbe dem Thema.
  2. **Ganz Bonn:** Säulen je Ortsteil nach den Vorlagen der letzten 12 Monate.
- **Grenzen:**
  - WebGL ist nötig, sonst bleibt die Seite leer.
  - Die Karte ist für Vorleseprogramme nicht lesbar; eine Liste oder Tabelle bleibt die gleichwertige Alternative.
  - Die Seite lädt zusätzlich die Bibliothek MapLibre, rund 465 KB komprimiert.

## 2. Vorbild Stadtmonitor Witzenhausen

- **Technik:** Grundrisse aus ALKIS, hochgezogen auf die Höhe aus LoD2-Modellen. Ausgeliefert als eine PMTiles-Datei mit MapLibre GL, ohne Dächer und Gelände.
- **Herkunft:** Laut README stammen die Grundmodule aus der RIS-Karte Bonn (Code MIT); die 3D-Ansicht ist dort eine eigene Seite.
- **Hinweis zur Prüfung:** Die Live-Seite habe ich nicht geprüft; die Angaben stammen aus dem Repository `isabell-rzepecki/wiz-stadtmonitor`.

## 3. Daten (gemessen)

| | Wert |
|---|---|
| Kacheln LoD1 für Bonn (1 km², CityGML) | 183, zusammen 1,33 GB |
| Aufbereitung (Download, Grundriss und Höhe je Gebäude) | rund 6 Minuten, Skript `lod1_auszug.py` |
| Gebäude und Gebäudeteile mit Gemeindeschlüssel Bonn | 114.485 (nach Entfernen doppelter an Kachelgrenzen) |
| Höhe (oberste minus unterste Kante) | Median 5,7 m, höchstes 156,6 m |
| ganz Bonn als eine GeoJSON-Datei | 28,1 MB, komprimiert 4,6 MB – zu groß für eine Datei |
| Endenich als GeoJSON | 0,86 MB, komprimiert 138 KB |
| MapLibre GL 6.19 (Skript, Worker, Stile) | komprimiert 298 + 157 + 10 KB |

Für ganz Bonn braucht es Vektorkacheln, also eine PMTiles-Datei wie in Witzenhausen. Dann lädt eine Ansicht nur die sichtbaren Kacheln. Erzeugt würde sie mit tippecanoe im Workflow, vierteljährlich wie die grauen Kacheln. Die genaue Größe wird erst dort gemessen; die komprimierte GeoJSON-Datei lässt etwa 5 bis 10 MB für alle Zoomstufen erwarten (Schätzung).

## 4. Datenschutz und Quellentreue

- **Gebäude:** Sie tragen keine Angaben zu Personen. Übernommen werden nur Grundriss und Höhe; Gebäudefunktion und Adressen nicht.
- **Vorlagen:** Sie stehen nur dort, wo sie auch auf der Hauptkarte stehen (Straße, Objekt, Punkt der Stadt), mit derselben Maskierung. Säulen sind Zählungen, keine Bewertungen.
- **Einordnung im Text:** Die Höhe einer Säule bedeutet nicht Bedeutung. Das muss auf der Seite stehen.
- **Externe Anfragen:** keine. Hintergrund sind die eigenen grauen Kacheln, Gebäude und Bibliothek kommen vom eigenen Server. Die Datenschutzerklärung bleibt unverändert.

## 5. Barrierefreiheit (Prototyp)

- **axe bei 1440 und 390 px:** ein Befund, „link-in-text-block“ im Quellenvermerk von MapLibre; leicht zu beheben.
- **Bedienung:** Ansicht wählen und zoomen geht mit Schaltflächen und Tastatur. Drehen und Neigen geht mit der Maus, auf dem Telefon mit zwei Fingern; zum Zurücksetzen braucht es eine Schaltfläche.
- **Alternative für Vorleseprogramme:** Die 3D-Fläche bekommt eine kurze Beschreibung. Daneben steht eine Tabelle mit denselben Zahlen (Vorlagen je Ortsteil) und Links in die Hauptkarte.
- **Reduzierte Bewegung:** Kamerafahrten werden abgeschaltet.

## 6. Vorschlag für Phase 1: Seite `3d/` „Bonn in 3D“

1. Gebäude für ganz Bonn als PMTiles: Pipeline-Schritt auf Knopfdruck, Workflow vierteljährlich, Ablage wie die Kacheln über den Branch `deploy`.
2. Ansicht „Vorlagen vor Ort“: Säulen der letzten 12 Monate, Farbe nach Thema, Klick öffnet den Vorgang auf der Hauptkarte.
3. Ansicht „Ganz Bonn“: Säulen je Ortsteil, dazu die Tabelle aller Ortsteile.
4. Ohne WebGL ein Hinweis mit Link zur Hauptkarte; auf dem Telefon zuerst flach (Neigung 0), 3D auf Wunsch.
5. Link im Menü „Themen“ (Kachel) und im Fuß der statischen Seiten; Quellen und Lizenz (Geobasis NRW, dl-de/zero-2.0) im Akkordeon.

## 7. Offene Entscheidungen

1. Phase 1 wie vorgeschlagen bauen?
2. LoD1 (Klötze, leicht) oder LoD2 mit Dächern? LoD2 wiegt 3,1 GB roh und bräuchte 3D Tiles mit zusätzlicher Bibliothek. Vorschlag: LoD1.
3. Welche Ansichten: beide, oder nur „Vorlagen vor Ort“?
