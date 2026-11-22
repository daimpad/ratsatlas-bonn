# Archiv der Baustellen der Stadt Bonn

Dieser Branch wird täglich vom Workflow `baustellen.yml` im Repository [daimpad/ratsatlas-bonn](https://github.com/daimpad/ratsatlas-bonn) fortgeschrieben (Ratsatlas Bonn, https://bonn.ratsatlas.de/).

**Quelle:** Stadt Bonn, Schnittstellen unter stadtplan.bonn.de – Thema 14403 (Baustellen tagesaktuell), 14698 (geplant, 1 Jahr), 14755 (geplant, 30 Tage). **Lizenz:** CC0 1.0 (laut Auftraggeber; die Datensätze stehen seit 2026 nicht mehr im Katalog von opendata.bonn.de).

**Hinweise der Quelle:** Termine für Baubeginn und Bauende sind nicht verbindlich. Erfasst sind nur Baumaßnahmen mit nennenswertem Einfluss auf den Verkehr. Eine Baustelle ist kein Beleg dafür, dass ein Ratsbeschluss umgesetzt wird.

**Historie:** Die Stadt hält keine früheren Stände vor. Das Archiv beginnt mit dem ersten Abruf am 19.10.2026; was davor beendet wurde, fehlt.

| Datei | Inhalt |
|---|---|
| `baustellen.json` | Zustand je Baustelle (`baustelle_id`): Feeds, erstes und letztes Auftreten, aktiv bzw. entfallen, aktuelle Angaben, Änderungen mit Datum |
| `protokoll.tsv` | Ereignisse je Abruf: neu, geaendert (Feld, alt, neu), entfallen, wieder_da, abruf_fehlgeschlagen, abruf_leer (alle Feeds leer bei gemeldeten Baustellen: nichts gilt als entfallen) |
| `snapshots/JJJJ/MM/TT/thema_NNNNN.json` | Momentaufnahme eines Feeds, nur wenn sich der Inhalt gegenüber dem letzten Abruf geändert hat |
| `STAND.json` | letzter Abruf je Feed: Zeitpunkt, Versuche, Anzahl, Prüfsumme |

Eine Baustelle gilt nur als entfallen, wenn alle drei Feeds vollständig abgerufen wurden (der Dienst antwortet zeitweise mit HTTP 400). `adresse` enthält teils Hausnummern als Bezugspunkt der Baumaßnahme; der Ratsatlas zeigt Baustellen höchstens auf Straßenebene.
