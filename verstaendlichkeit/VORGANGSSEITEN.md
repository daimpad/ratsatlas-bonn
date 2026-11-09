# Seiten je Vorgang (09.11.2026)

Grundlage: Phase 0, `phase0/BERICHT.md`, Abschnitt 4 (Option 4, gestufte Einführung).

## Entscheidungen des Auftraggebers (09.11.2026)

- Umfang Stufe 1: Regel der Vorgangsfeeds – Vorlagen ab dem 1. Januar des Vorjahres des Datenstands oder noch „offen“ bzw. „in Beratung“.
- Vorlagen aus der Einwohnerschaft (Bürgeranträge, Anregungen und Beschwerden, Einwohnerfragen, Bürgerbriefe) und alle mit ihnen verbundenen Vorlagen erhalten keine Seite (Kette wie `chat.einwohner`, ohne Bauordnung und Naturschutz; deren Titel sind maskiert).

## Umsetzung

- `publish.has_page` legt die Regel fest; der Export setzt das Feld `seite` in den Gebietsdateien. Die Seitenerzeugung und der Link „Seite zu dieser Vorlage“ im Vorgang verwenden dasselbe Feld.
- `pipeline/vorgangsseiten.py` (Schritt `seo`) schreibt `vorgang/<drucksache>/index.html`: Titel (maskiert), Art, Datum, federführende Stelle, Einreichende (abgeleitet), Stand mit Erklärung, Ort nur mit Namen (abgeleitet gekennzeichnet, Ortsteil verlinkt), Beratungsfolge mit wörtlichem Ergebnis, Bezüge (verlinkt, wenn das Ziel eine Seite hat), Links zu Karte, Original, PDF und Feed, Begriffe, Quellen. Ohne Skripte, ohne Kurzfassungen, ohne Erzeugungszeitpunkte.
- `sitemap.xml` ist ein Index über `sitemap-seiten.xml` und `sitemap-vorgaenge.xml`; `lastmod` ist das jüngste Datum aus der Quelle (Vorlage, Beratung, Folgevorlage). Die eingereichte Adresse in der Search Console bleibt gleich.

## Messung (lokal, Datenstand 02.11.2026)

| | Wert |
|---|---|
| Vorlagen nach der Regel der Feeds | 8.278 |
| davon Einwohnerschaft und verbundene Vorlagen | 1.345 |
| Seiten | 6.933 |
| Größe | 36,1 MB, Median 5,2 KB, größte 36,6 KB |
| `sitemap-vorgaenge.xml` | 0,65 MB |
| Laufzeit des Schritts `seo` | rund 6 s |

## Prüfung

- `tests/test_vorgangsseiten.py` (Regel, Inhalt, Links, Sitemap), `tests/browser/vorgang.test.mjs` (Link aus dem Vorgang, Rückweg zur Karte, axe bei 1440 und 390 px ohne Verstöße, kein waagrechter Bildlauf).
- `live.yml` prüft `sitemap-vorgaenge.xml` und die erste Seite daraus.

## Offen

- Search Console nach vier bis acht Wochen auswerten (aufgenommen, „gecrawlt – nicht indexiert“); danach Entscheidung über Stufe 2 (weitere Vorlagen) oder Kurzfassungen auf den Seiten.
- Die Titelregel der Einwohnerschaft (Wörter wie „Einwohner“ oder „Anregung“ im Titel) schließt auch einzelne Verwaltungsvorlagen aus; das ist gewollt vorsichtig.
