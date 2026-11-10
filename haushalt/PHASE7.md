# Haushalt Option 7 – Phase 1a: Einzelmaßnahmen lesen und prüfen (10.11.2026)

Grundlage: `haushalt/phase0/EINZELMASSNAHMEN.md` mit den Entscheidungen des Auftraggebers vom 10.11.2026 (Liste auf `haushalt/` und den Themenseiten, ohne Karte; nur Maßnahmen mit Ansatz 2025 oder 2026; Spalten Ansatz 2025, Ansatz 2026, Gesamt; „Leibrenten“ und „Intendantenvertrag“ nur in der Summe; Abkürzungen nur mit Fundstelle). Plan freigegeben am 10.11.2026: erst Leser und Prüfbogen, Anzeige nach Freigabe.

## Umgesetzt
- `pipeline/massnahmen.py`, Schritt `haushalt-massnahmen` (einmalig, lokal, `pdftotext -bbox`, PDF über `HAUSHALT_PDF` mit SHA-256 laut `STAND.json`): Teilfinanzplan B des Haushaltsplans 2025/2026 je Produktgruppe → `data/haushalt/massnahmen.tsv` (je Maßnahme und Zeile die Spalten 4, 6, 12, mit Datei und Seite), Vermerk `massnahmen` in `STAND.json`.
- Gelesen 882 Maßnahmen, übernommen 315 (Ansatz 2025 oder 2026 ungleich 0); keine der beiden Bezeichnungen zu Einzelpersonen hat einen Ansatz.
- Prüfsummen über alle 882 Maßnahmen: Spalte 12 je Zeile 1.986 Prüfungen, Saldo je Maßnahme 10.572, Summe je Produktgruppe gegen Teilfinanzplan A 4.080; größte Abweichung 1 bzw. 2 € (Rundung im PDF). Ansatz 2026 der Auszahlungen 191.603.105 € wie in Phase 0.
- Fünf Stellen mit Beleg als Ausnahme (`AUSNAHMEN`, `OHNE_BLOCK`; PB02 S. 42 Saldo nachgerechnet, PB12 S. 13 und 18 Bezeichnungen ohne eigene Zeilen, PB12 S. 18 Bezeichnung abgeleitet, PB12 S. 48 Block ohne Bezeichnung ohne Ansatz). Ein Block ohne Bezeichnung, eine Bezeichnung ohne Zeilen oder eine Verschiebung über 12 pt an anderer Stelle bricht ab.
- Prüfbogen `data/export/haushalt/pruefbogen_haushalt_massnahmen.tsv` (Schritt `haushalt-pruefbogen-massnahmen`): 29 Zellen (größte und kleinste Ansätze, Einzahlungen, negativer Wert, Saldo, Ausnahmen, gekürzte und doppelte Bezeichnungen, leere Zelle, Stichprobe je Produktbereich), mit Link auf die Seite und dem Ergebnis eines zweiten Lesewegs über `pdftotext -layout`: 28 von 28 verglichenen Zellen gleich, eine nicht verglichen (abgeleitete Bezeichnung).
- `FREIGEGEBEN = False`: noch keine Anzeige. Tests `tests/test_massnahmen.py`.

## Phase 1b: Anzeige (10.11.2026)
- Prüfbogen vom Auftraggeber im Gespräch freigegeben am 10.11.2026 (Spalte `pruefung`), `FREIGEGEBEN = True`.
- `haushalt/`: je Produktgruppe (Ebene 3) aufklappbare Liste „Investitionsmaßnahmen (n)“ mit Ansatz 2025, Ansatz 2026 und Gesamt (Auszahlungen in Euro, Einzahlungen klein darunter) und Link auf die Seite im PDF; unter „Investitionen“ der Abschnitt „Einzelne Maßnahmen“ mit den zehn größten nach Auszahlungen 2026 und der Lesehilfe; Grenzen und Prüfung ergänzt. Nur zusammen mit den Investitionen (`ERWEITERUNG_FREIGEGEBEN`). Seite gepackt etwa 17 KB größer.
- Themenseiten mit Produktbereich: Abschnitt „Investitionsmaßnahmen im Produktbereich“ mit den acht größten und Link auf alle (`dossier._massnahmen`); Digitales ohne Produktbereich ohne Abschnitt.
- Abkürzungen (z. B. „BK“) bleiben unaufgelöst, da keine Fundstelle der Stadt vorliegt (Entscheidung 10.11.2026: nur mit Fundstelle erklären).
- Geprüft: Browser bei 1440 und 390 px, axe ohne Verstöße, kein waagerechter Bildlauf; Tests.
