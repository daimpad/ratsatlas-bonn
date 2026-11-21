# Paket C: Ladezeit und Größe (21.11.2026)

Umsetzung zu `BERICHT_2026-11.md`, Nr. 18, 20, 38, 39, 40.

| Nr. | Umgesetzt |
|---|---|
| 18 | Assistent: Gestreamter Text wird höchstens einmal je Bild der Anzeige gesetzt; mitgescrollt wird nur, wenn die Ansicht unten steht. |
| 38 | `strukturdaten.json` (212 KB) lädt erst beim Aufklappen des Kastens „Strukturdaten zu …“ oder wenn die Flächen danach gefärbt werden, nicht mehr bei jedem Start und Gebietswechsel. |
| 39 | Bilder der Themenseiten zum Teilen als PNG mit Farbpalette (64 Farben): zehn Bilder 0,7 statt 2,3 MB je Tag im Branch `deploy`, gleich lesbar. |
| 40 | Gebietsdateien: Feld `process` nur noch mit Gremium, Ergebnis und Rolle (die Seite liest nichts anderes daraus; alles Übrige steht in `steps`). Endenich 2,53 statt 2,80 MB, komprimiert 216 statt 234 KB. |
| 20 | Nur Hinweis in `live.yml`, wenn `vorlagen.geojson` unkomprimiert ausgeliefert wird. Die Komprimierung selbst ist eine Einstellung in Plesk (wie die Kopfzeilen): nginx liefert statische Dateien an Apache und `deploy/htaccess` vorbei aus. |

Nicht umgesetzt:

- `zeit.json` erst beim Öffnen der Zeitleiste laden (Teil von Nr. 38): Die Datei wird schon mit niedriger Priorität geladen; die Zeitleiste und der Zeitraum aus dem Link hängen am Start daran. Gewinn rund 50 KB Übertragung, Umbau des Starts nötig.
- Bilder der Themenseiten nur bei geändertem Inhalt neu schreiben (Variante zu Nr. 39): bräuchte den Vergleich mit dem vorigen Stand im Branch `deploy`; die Verkleinerung erreicht zwei Drittel der Einsparung ohne diese Kopplung.

Messung vor und nach diesem Paket: siehe Pull Request.
