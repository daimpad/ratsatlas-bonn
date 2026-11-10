# Strukturdaten Bonn – Phase 2 (Raumabgleich)

Stand 10.11.2026 · Entscheidungen des Auftraggebers vom 10.11.2026:
- Phase 2 beginnt jetzt auf der Geometrie des Atlas (Stand 2016) und wird neu berechnet, sobald stadtplan.bonn.de die aktuelle Geometrie liefert.
- `zuordnung.tsv` erhält die Spalte `einwohneranteil`; der Datenvertrag heißt damit Entwurf 1.1.
- Werte je Ortsteil werden nach den Vertragsregeln gebildet.

## Verfahren

- **Verschneidung:** Jeder statistische Bezirk wird mit den 51 Ortsteilen der Stadt verschnitten. Dazu kommt der Anteil der Einwohner nach dem Zensus 2022 (100-m-Zellen, Mittelpunkt im Gebiet; `data/kontext/zensus_bonn.tsv`).
- **Zuordnung eines Bezirks:** Ein Bezirk „liegt im Ortsteil“, wenn dort mindestens 97 % seiner Einwohner wohnen (Konfidenz hoch). Geteilte Bezirke werden im Audit gemeldet und keinem Ortsteil zugeordnet.
- **Sauber zusammengesetzter Ortsteil:** Mindestens 95 % seiner Einwohner wohnen in Bezirken, die in ihm liegen.
- **Werte je Ortsteil** (`werte.tsv`, Raumebene `ortsteil`, Status `abgeleitet`, Quellobjekt nennt die Bezirke):
  - Ein Bezirk: Alle Werte werden unverändert übernommen.
  - Mehrere Bezirke: Anzahlen werden summiert, Anteile aus Zähler und Nenner berechnet (Zuwanderer- und Ausländeranteil, geförderte Wohnungen); die übrigen Kennzahlen werden nicht gebildet.
  - Ist ein Teil geheim oder fehlt er, erhält der Wert den Status `fehlt`.
  - Nahezu unbewohnte Bezirke ohne Werte zählen in Summen nicht mit (betrifft Röttgen mit 129 Kottenforst).
- **Befund zur Rechenregel:** „Bedarfsgemeinschaften je 1.000 Haushalte“ lässt sich in 2012, 2013, 2017, 2021 und 2023 nicht aus Bedarfsgemeinschaften und Haushalten nachrechnen. Die Quelle verwendet dort offenbar eine andere Zahl der Haushalte. Dieser Anteil wird deshalb nicht neu gebildet. Die übrigen drei Anteile stimmen in allen Bezirken und Jahren auf 0,05 genau.

## Ergebnis

| Ergebnis | Zahl |
|---|---|
| Bezirke, die in einem Ortsteil liegen | 50 von 65 |
| sauber zusammengesetzte Ortsteile | 30 von 51; davon 22 aus einem Bezirk, 8 aus mehreren (Alt-Godesberg, Bonn-Zentrum, Endenich, Mehlem, Plittersdorf, Röttgen, Tannenbusch, Weststadt) |
| Werte je Ortsteil | 17.482, davon 30 mit Status `fehlt` |
| Beispiel Endenich 2025 | 14.847 Einwohner = 120 Neu-Endenich (5.601) + 121 Alt-Endenich (9.246) |

Dateien:
- `zuordnung.tsv`
- `audit_raumabgleich.tsv` mit 50 Bezirken „liegt im Ortsteil“, 46 Zeilen „geteilt, nicht zugeordnet“ und 38 Randanteilen
- `raum/ortsteil.geojson`

## Grenzen

- Die Werte je Ortsteil zählen nur die Bezirke, die im Ortsteil liegen. Bis zu 5 % der Einwohner eines Ortsteils können daher fehlen; die Einwohnerzahl des Ortsteils wird also leicht unterschätzt.
- Geometrie von 2016 und Zensus 2022 sind zwei verschiedene Stände. Das Ergebnis ist vorläufig, bis die aktuelle Geometrie der Stadt vorliegt.
- 21 Ortsteile, vor allem in Beuel und Duisdorf, haben keine eigenen Werte. Die Seite wird dort die beteiligten Bezirke nennen (Phase 3).
