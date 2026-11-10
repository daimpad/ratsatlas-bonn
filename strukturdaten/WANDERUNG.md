# Strukturdaten Bonn – Wanderungsdaten (vorbereitet)

Stand 10.11.2026 · Entscheidungen des Auftraggebers vom 10.11.2026: Bezugsweg noch offen; Zu-, Fortzüge und Saldo je statistischem Bezirk (ohne Herkunft und Ziel, keine Erweiterung des Datenvertrags); kurze Liefervorlage für die Statistikstelle.

## Ausgangslage

Die Stadt hat Wanderungsdaten freigegeben (Mitteilung des Auftraggebers 10.11.2026). Kleinräumig sind sie nirgends öffentlich abrufbar: Der Strukturdatenatlas enthält keine Zu- und Fortzüge, der Wegweiser Kommune nur den Saldo für ganz Bonn (`wk-wanderungssaldo`, bereits übernommen).

## Vorbereitet

- **Liefervorlage** `strukturdaten/wanderung/LIEFERVORLAGE.md` mit `vorlage_wanderung.tsv` (Zahlen erfunden). Versand durch den Auftraggeber.
- **Import** (`wanderung()` in `pipeline/strukturdaten.py`): Liegt `data/strukturdaten/lieferung/wanderung.tsv` vor, übernimmt der Schritt `strukturdaten` die Werte als Indikatoren `bonn-wan-…` des Datenvertrags. Lieferdatum und Stand stehen in `lieferung/STAND.json`.
  - Übernommen unverändert: Zu- und Fortzüge über die Stadtgrenze und innerhalb Bonns; `*` wird zu `geheim`, leer zu `fehlt`.
  - Abgeleitet: Saldo und Saldo je 1.000 Einwohner (Einwohner des Atlas am 31.12. desselben Jahres).
  - Je Ortsteil nur für die sauber zusammengesetzten Ortsteile: Zählungen über die Stadtgrenze und Saldo summiert, Saldo je 1.000 aus Zähler und Nenner. Umzüge innerhalb Bonns werden nicht summiert, weil sie zwischen Bezirken desselben Ortsteils doppelt zählen würden.
  - Abbruch bei unbekannten Gebieten oder Jahren, doppelten Zeilen, fehlenden Spalten und Zahlen, die keine ganzen Zahlen ≥ 0 sind.
  - Hinweise in `audit_plausibilitaet.tsv`: Umzüge innerhalb Bonns gleichen sich über alle Bezirke nicht aus; Summe der Bezirke weicht von der gelieferten Zahl für ganz Bonn ab.
- **Seite:** noch keine Anzeige. Die Daten stehen nach Eingang im Datenpaket; über Flächenfarbe und Steckbrief wird danach entschieden.

## Ablauf nach Eingang

1. Datei als `data/strukturdaten/lieferung/wanderung.tsv` ablegen (anderes Format: vorher umwandeln, Spalten wie in der Vorlage), `STAND.json` ausfüllen.
2. `python -m pipeline strukturdaten` ausführen und Plausibilitätshinweise im Gespräch prüfen.
3. Über die Anzeige entscheiden.

## Prüfung

- Tests mit erfundenen Lieferungen: Werte, Saldo, Geheimhaltung, Tausenderpunkt, Semikolon, Plausibilität, Abbruchfälle, Ortsteile.
- Gegenprobe mit der Vorlage als Lieferung: Vertragsprüfung ohne Fehler; ohne Lieferung bleiben alle Dateien unverändert.
