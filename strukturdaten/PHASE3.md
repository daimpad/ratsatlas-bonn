# Strukturdaten Bonn – Phase 3 (Darstellung)

Stand 10.11.2026 · Entscheidungen des Auftraggebers vom 10.11.2026:
- zwölf ausgewählte Kennzahlen für die Flächenfarbe
- Flächen auf Ebene der 65 statistischen Bezirke
- Zensus und Strukturdaten getrennt nebeneinander
- Vergleich der Städte im Steckbrief „ganz Bonn“

## Umsetzung

- **Daten:** Der Schritt `strukturdaten-seite` (täglich nach `kontext`) schreibt `export/bonn/strukturdaten.json` mit 206 KB, komprimiert 56 KB. Die Seite lädt die Datei erst, wenn Steckbrief oder Flächenfarbe sie brauchen. Enthalten sind:
  - 15 Kennzahlen mit allen Jahren
  - Werte je Bezirk, Ortsteil, Stadtbezirk und ganz Bonn
  - vereinfachte Flächen der Bezirke (etwa 5 m)
  - Zuordnung zu den Ortsteilen
  - Vergleichswerte des Wegweisers
- **Flächen färben nach:** neue Gruppe „Strukturdaten (statistische Bezirke)“ mit Bevölkerungsdichte, Durchschnittsalter, Jugend- und Altenquotient, Kindern unter 6, 75 Jahren und älter, Ausländeranteil, Einpersonenhaushalten, Haushalten mit Kindern, Haushalten mit Alleinerziehenden, Arbeitslosenquote und Leistungsberechtigten nach SGB II.
  - Die Karte zeigt dann die 65 Bezirke statt der Ortsteile. Ein Klick auf einen Bezirk öffnet den Ortsteil, in dem die meisten seiner Einwohner wohnen.
  - Jahr wählbar; Stufen als Fünftel der Bezirke im Jahr oder als feste Grenzen über alle Jahre (`sjahr=`, `sstufen=fest` in der Adresse).
  - Schraffiert: in der Quelle geheim gehalten. Grau: ohne Wert.
  - Die Legende erklärt die Kennzahl (Metatext) und enthält die Tabelle aller Bezirke. Die Tabelle ist zuerst nach Nummer geordnet, damit keine Rangfolge vorgegeben wird, und lässt sich nach dem Wert sortieren.
- **Steckbrief „Strukturdaten zu …“** in der Liste, unter „Zahlen zu …“ (Zensus):
  - Ortsteil, sauber zusammengesetzt: Ortsteil (abgeleitet), Stadtbezirk und ganz Bonn. Bei mehreren Bezirken kommen sie aufklappbar dazu.
  - Ortsteil, nicht sauber zusammengesetzt: die Bezirke mit Einwohnern dort und ihr Anteil.
  - Stadtbezirk: Stadtbezirk und ganz Bonn.
  - Ganz Bonn: dazu die Tabelle „Bonn, Köln und Wuppertal im Vergleich“ (Wegweiser) mit Hinweis auf abweichende Definitionen.
  - Je Kennzahl gibt es eine Erklärung zum Aufklappen, eine kleine Linie der Zeitreihe (mit Text für Vorleseprogramme), Jahr und Einheit.
- **Hinweise:** kein Urteil und keine Rangfolge; dass Vorlagen und Kennzahlen am selben Ort zusammentreffen, begründet keinen Zusammenhang. Quelle und Stand stehen im Steckbrief, in der Legende und unter „Quellen, Lizenzen und Datenstand“.

## Prüfung

- `tests/browser/struktur.test.mjs`:
  - 65 Flächen, Jahr und Stufen in der Adresse
  - Tabelle zuerst nach Nummer, dann sortierbar
  - Rückkehr zur Zahl der Vorlagen
  - Steckbrief für Endenich, Beuel-Mitte und ganz Bonn
  - axe ohne Verstöße bei 1440 und 390 px, kein waagrechter Bildlauf
- `tests/test_strukturdaten.py`: Klasse `Seite` (kompakte Datei aus den Dateien im Repository).
- Die übrigen Browser-Tests (Start, Karte, Begriffe, Vorgänge) laufen weiter ohne Fehler.

## Offen

- Neuberechnung von Raumabgleich und Flächen, sobald stadtplan.bonn.de die aktuelle Geometrie liefert.
- Phase 4: Verifikation (Stichprobe von 20 Werten gegen die Quelle) und Datenpaket.
