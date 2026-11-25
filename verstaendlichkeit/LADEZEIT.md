# Karte mobil schneller – Schritt 1 (02.11.2026)

**Grundlage:** `phase0/BERICHT.md`, Abschnitt 1. Ziel des Auftraggebers (02.11.2026) ist der Richtwert von 2,5 s für das größte Element (LCP, mobil). Über Schritt 2 (Gebietsdaten teilen) wird nach der Messung entschieden.

## Änderungen
- **Karte vor den Daten:** Karte und Kacheln werden angelegt, bevor die übrigen Startdaten da sind (`createMap`, Ausschnitt ganz Bonn). Ein Gebiet im Link setzt seinen Ausschnitt, sobald die Flächen geladen sind (`fruehAnsicht`).
- **Gebietsdatei früher:** Nennt der Link ein Gebiet, fordert der Start dessen Datei gleich mit an.
- **Daten nachrangig:** Zeitleiste, Baustellen, Kontext und Mängelmelder laden mit niedriger Priorität (Priority Hints) und nicht mehr vorab.
- **Vorverbindung** zu `tile.openstreetmap.org`.
- **Stile zusammengefasst:** Leaflet und MarkerCluster stehen jetzt in einer Datei mit Integritätsprüfung (`vendor/leaflet/karte.min.css`).

## Messung
Lighthouse 12.8.2 mobil (simuliert 150 ms RTT, 1,6 Mbit/s, CPU × 4). Lokale Kopie mit gzip, je 3 Läufe, Median:

| Seite | | Score | FCP | LCP | TBT | Übertragen |
|---|---|---|---|---|---|---|
| Start | vorher | 76 | 1,6 s | 5,8 s | 165 ms | 845 KB |
| Start | nachher | 76 | 1,3 s | 6,0 s | 129 ms | 846 KB |
| Endenich | vorher | 57 | 1,6 s | 6,0 s | 883 ms | 861 KB |
| Endenich | nachher | 62 | 1,3 s | 5,9 s | 666 ms | 860 KB |

**Ergebnis:** Der erste sichtbare Inhalt kommt früher, und die Blockierzeit im Gebiet sinkt um ein Viertel. Das LCP bleibt gleich.

**Warum das LCP gleich bleibt:**
- Das größte Element ist eine OSM-Kachel.
- Beim Start werden 15 Kacheln mit zusammen 515 KB geladen, das sind 61 % aller Daten.
- Bei 1,6 Mbit/s teilen sich die Kacheln die Bandbreite, deshalb ist die letzte erst spät fertig.

**Gegenprobe, nur lokal und nicht übernommen (berichtigt 02.11.2026):**
- Die Gegenprobe mit CARTO Positron hat nicht die echte Karte gemessen. CARTO verlangt inzwischen einen API-Schlüssel. Ohne Schlüssel liefert jede Kachel nur den Platzhalter „API KEY REQUIRED“ mit rund 2 KB.
- Die zuerst genannten Werte (362 KB, LCP 3,8 s bzw. 4,4 s) gelten deshalb nur für diese Platzhalter und sind ungültig.
- Den Vergleich der Kartenquellen mit echten Kacheln enthält `kartenquellen/BERICHT.md` (in diesem Ordner).
- Ein Wechsel der Kartenquelle ist eine Entscheidung des Auftraggebers: Es käme ein weiterer Anbieter mit Nutzungsbedingungen hinzu, und Datenschutzerklärung und Quellenangabe müssten angepasst werden.

## Schritt 1b: Daten nach den Kacheln (02.11.2026)
Entscheidung des Auftraggebers vom 02.11.2026: Zeitleiste, Gebietsflächen und weitere Daten laden erst nach den Kacheln.

**Umsetzung:**
- Der Start lädt zuerst nur `index.json`. Die Datei ist klein, wird vorab angefordert und enthält jetzt den Umriss (`bbox`) jedes Ortsteils und Stadtbezirks.
- Daraus ergibt sich der erste Kartenausschnitt, und die Kacheln laden sofort.
- Glossar, Flächen, Zeitleiste, Baustellen, Kontext, Mängelmelder und die Gebietsdatei aus dem Link folgen, sobald die sichtbaren Kacheln geladen sind. Länger als 2,5 s wartet der Start nicht.
- Vorab angefordert werden nur noch `index.json` und die Schrift.

**Messung** (wie oben, je 3 Läufe):

| Seite | | Score | FCP | LCP | TBT | Übertragen |
|---|---|---|---|---|---|---|
| Start | Schritt 1 | 76 | 1,3 s | 6,0 s | 129 ms | 846 KB |
| Start | Schritt 1b | 92 | 1,3 s | 3,1 s | 115 ms | 846 KB |
| Endenich | Schritt 1 | 62 | 1,3 s | 5,9 s | 666 ms | 860 KB |
| Endenich | Schritt 1b | 69 | 1,3 s | 4,2 s | 676 ms | 861 KB |

**Ergebnis:**
- Die übertragene Menge bleibt gleich, aber die Kacheln teilen die Bandbreite nicht mehr mit den übrigen Daten.
- Der Richtwert von 2,5 s ist auf der Startseite fast erreicht.
- Größter verbleibender Hebel ist die Kartenquelle. Die Bedingungen der Anbieter werden geprüft, bevor etwas umgestellt wird.
- Die Blockierzeit im Gebiet (rund 670 ms) betrifft Schritt 2.

## Graue Karte vom eigenen Server (02.11.2026)
Entscheidung des Auftraggebers vom 02.11.2026: Die graue Standardansicht zeigt eigene Rasterkacheln aus OSM-Daten (Weg B, `kartenquellen/OSM_GRAU.md`). „Farbige Karte“ bleibt bei OpenStreetMap.

**Messung** (Lighthouse mobil, lokal mit gzip, je 5 Läufe; vorher = Stand `main` mit OSM-Kacheln):

| Seite | | Score | FCP | LCP | TBT | Übertragen |
|---|---|---|---|---|---|---|
| Start | vorher | 83 | 1,3 s | 4,7 s | 140 ms | 847 KB |
| Start | graue Kacheln | 91 | 1,3 s | 3,0 s | 160 ms | 473 KB |
| Endenich | vorher | 69 | 1,3 s | 4,1 s | 667 ms | 861 KB |
| Endenich | graue Kacheln | 76 | 1,3 s | 3,4 s | 554 ms | 553 KB |

**Ergebnis:**
- Beim Start werden 374 KB weniger übertragen.
- Die Zeiten hängen nicht mehr vom OSM-Server ab; vorher schwankte die LCP zwischen 2,3 und 5,4 s.
- Der Richtwert von 2,5 s ist noch nicht erreicht. Die Blockierzeit im Gebiet betrifft Schritt 2 (Gebietsdaten aufteilen).

## Schritt 2: Rechenarbeit im Gebiet (02.11.2026)
Entscheidung des Auftraggebers vom 02.11.2026: zuerst messen, dann die Gebietsdatei teilen und die Liste in Schritten zu 50 zeigen. Nach der Messung (unten) entschied der Auftraggeber, zuerst nur kleine Eingriffe vorzunehmen und das Teilen der Datei nur anzugehen, wenn der Richtwert danach noch verfehlt wird.

**Messung der Rechenarbeit** (CPU-Profil beim Öffnen von Endenich, Telefonbreite, vierfach gedrosselt; Selbstzeit je Funktion):

| Stelle | vorher | nachher | Ursache |
|---|---|---|---|
| Zeitleiste zeichnen (`draw`) | 414 ms | 120–150 ms | Monatsnamen der Achse mit `toLocaleDateString` je Strich |
| Datum formatieren (`fmtDate`) | 200 ms | – | `toLocaleDateString` mit Optionen baut den Formatierer bei jedem Aufruf neu |
| Farbe der Punkte (`color`) | 119 ms | – | `getComputedStyle` je Punkt |
| Breite der Flächen (`widthOf`) | rund 100 ms | – | `getComputedStyle` erzwang eine Stilberechnung |
| Gebietsdatei auswerten (`loadArea`) | 123 ms | 100–130 ms | unverändert; das Teilen der Datei spart hier höchstens 60–80 ms |

**Änderungen:**
- Formatierer für Datum, Tag, Monat, Zahl und Prozent werden einmal angelegt (`app.js`, `timeline.js`).
- Die Farben der Punkte werden je Name einmal gelesen.
- Die Breite von Liste und Vorgang wird aus dem gesetzten Wert oder der Vorgabe gelesen, ohne Stilberechnung.
- Die Liste zeigt 50 statt 200 Einträge; „Weitere 50 anzeigen“ setzt den Fokus auf den ersten neuen Eintrag. Dafür gibt es einen neuen Browser-Test.

**Lighthouse mobil** (lokal mit gzip, je 5 Läufe, Median; vorher = Stand `main` mit grauen Kacheln):

| Seite | | Score | FCP | LCP | TBT | Übertragen |
|---|---|---|---|---|---|---|
| Start | vorher | 84 | 1,6 s | 3,9 s | 223 ms | 473 KB |
| Start | Schritt 2 | 92 | 1,3 s | 3,0 s | 138 ms | 474 KB |
| Endenich | vorher | 67 | 1,3 s | 4,6 s | 618 ms | 553 KB |
| Endenich | Schritt 2 | 86 | 1,3 s | 2,8 s | 362 ms | 554 KB |

**Ergebnis:**
- Im Gebiet sinkt die Blockierzeit um rund 250 ms, die LCP liegt bei 2,8 s; der Wert „vorher“ streute in dieser Messreihe stärker als zuvor (3,4 s in der Messung zur grauen Karte).
- Der Richtwert von 2,5 s ist noch knapp verfehlt. Das Teilen der Gebietsdatei bleibt als nächster Schritt möglich; nach der Messung spart es im Gebiet höchstens 60–80 ms Rechenzeit.

## Messung 25.11.2026 (live, nach den Prüfungen vom November)

Lighthouse 12.8.2 mobil (simuliert 150 ms RTT, 1,6 Mbit/s, CPU × 4), Hauptadresse mit Komprimierung, je 5 Läufe, Median:

| Seite | LCP | FCP | TBT |
|---|---|---|---|
| Start (ganz Bonn) | 2,36 s | 0,97 s | 65 ms |
| Endenich | 2,26 s | 1,25 s | 261 ms |
| Themenseite Verkehr (2 Läufe) | 1,3 s | – | 37–142 ms |

- Der Richtwert von 2,5 s für das größte Element ist auf Start und Gebiet erreicht. Eine erste Messreihe mit
  eingeschalteter Software-Grafik (`--use-gl=angle --use-angle=swiftshader`, nötig nur für die 3D-Seite) ergab
  2,7 s, 2,9 s und eine Blockierzeit der Themenseite von 2,2 s; diese Werte sind durch die Software-Grafik verfälscht.
- `defer` für die Skripte der Karte (Lighthouse: „render-blocking“) geprüft und verworfen: FCP lokal 1,56 → 1,21 s,
  aber die Skripte laden dann mit niedriger Priorität und die Kacheln (LCP) beginnen später; mit
  `fetchpriority="high"` verschlechtert sich dafür FCP (1,5 → 2,0 s). Lokal schwankte LCP stark (3,5–9,8 s), die
  Messung an der Hauptadresse ist maßgeblich.
- Kein weiterer Eingriff nötig; das Teilen der Gebietsdatei bleibt zurückgestellt.
