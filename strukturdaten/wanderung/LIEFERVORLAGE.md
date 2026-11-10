# Wanderungsdaten für den Ratsatlas Bonn – Vorschlag für die Lieferung

Entwurf vom 10.11.2026 · Versand durch den Auftraggeber · Grundlage: Freigabe der Stadt Bonn (Wanderungsdaten, ohne Pflicht zur Namensnennung)

Wir schlagen eine Tabelle je Lieferung vor (`vorlage_wanderung.tsv`; die Zahlen darin sind erfunden). Andere Formate (Excel, CSV mit Semikolon) übernehmen wir ebenso, wenn Spalten und Bedeutung gleich sind.

| Spalte | Inhalt |
|---|---|
| `raumebene` | `statistischer_bezirk`, `stadtbezirk` oder `gesamtstadt` |
| `raum_id` | Nummer wie im Strukturdatenatlas (z. B. `110`), Stadtbezirk `1`–`4`, ganz Bonn `bonn` |
| `jahr` | Berichtsjahr |
| `zuzuege_aussen` | Zuzüge über die Stadtgrenze in das Gebiet |
| `fortzuege_aussen` | Fortzüge über die Stadtgrenze aus dem Gebiet |
| `zuzuege_innen` | Umzüge innerhalb Bonns in das Gebiet (aus anderen Gebieten derselben Ebene) |
| `fortzuege_innen` | Umzüge innerhalb Bonns aus dem Gebiet |

- **Kleine Fallzahlen:** Nicht veröffentlichte Werte bitte mit `*` kennzeichnen. Leere Zellen lesen wir als „kein Wert“.
- **Jahre:** gern alle verfügbaren Jahre, mindestens die Jahre des Strukturdatenatlas (2014 bis 2025).
- **Ebenen:** Stadtbezirke und ganz Bonn bitte gesondert liefern. Umzüge innerhalb eines Stadtbezirks erscheinen dort nicht, die Werte lassen sich daher nicht aus den Bezirken aufsummieren.
- **Zusammengefasste Bezirke:** wie im Atlas (129 in 127, 380 in 381, 389 in 388) oder einzeln, mit Hinweis.
- **Was wir daraus machen:** Wir übernehmen die Werte unverändert. Saldo und Saldo je 1.000 Einwohner berechnen wir selbst und kennzeichnen sie als abgeleitet. Werte je Ortsteil bilden wir nur dort, wo sich ein Ortsteil sauber aus Bezirken zusammensetzt. Umzüge innerhalb Bonns summieren wir dabei nicht, weil sie zwischen Bezirken desselben Ortsteils doppelt zählen würden.

Rückfrage an die Statistikstelle: Weichen Definitionen ab, etwa beim Stichtag, bei Personen in Sammelunterkünften oder bei Umzügen innerhalb eines Bezirks? Dann nehmen wir das in die Beschreibung auf.
