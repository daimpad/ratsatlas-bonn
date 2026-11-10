# Haushalt – Phase 0 zu Option 7: Einzelmaßnahmen aus Teilfinanzplan B (10.11.2026)

**Anlass:** Option 7 aus `haushalt/phase0/ERWEITERUNG.md` („Einzelmaßnahmen aus Teilfinanzplan B, später; über Straßennamen evtl. auf der Karte“). Nur Prüfung, kein Produktionscode.

**Datenstand:** 34 PDF der Produktbereiche (17 je Ausgabe 2023/2024 und 2025/2026); SHA-256 aller 34 Dateien gleich `data/haushalt/STAND.json`. Die Dateien lagen aus einer früheren Sitzung vor, bonn.de wurde nicht erneut abgerufen. Dazu Haushaltssatzung (`hhsatz.pdf`) und Vorbericht (`vorbe.pdf`) 2025/2026 aus der Sitzung vom 01.11.2026. Gelesen mit `pdftotext -bbox`; die Prüfskripte liegen nur in der Sitzung. Stichprobe: `haushalt/phase0/einzelmassnahmen_stichprobe.tsv` (60 Maßnahmen).

## Ergebnis: vollständig lesbar, Summen gleich Teil A; rund 35–40 % der Maßnahmen mit Ansatz lassen sich auf Straße, Gebäude oder Ortsteil verorten
| Prüfung | 2023/2024 | 2025/2026 |
|---|---|---|
| Seiten mit Teil B / Maßnahmen gelesen | 304 / 925 | 293 / 882 |
| je Zeile: Spalte 12 = Spalten 4, 6, 8–11 (Toleranz 2 €) | 2.080 von 2.080 | 1.988 von 1.989 |
| je Maßnahme: Zeile 12 = Einzahlungen − Auszahlungen, 12 Spalten | 917 von 917 | 874 von 876 |
| Summe der Maßnahmen je PG = Teil A, Zeilen 1, 2, 4, 5, 7, 8, 9, 11, 12, Spalten 1–4, 6 | 3.824 von 3.825 (eine Zelle 3 €) | 3.780 von 3.780 |
| Saldo der Maßnahmen je PG = Teil A Zeile 14 ohne Finanzanlagen (Zeilen 3, 10), Toleranz 3 € | 425 von 425 | 420 von 420 |

Die drei Abweichungen liegen auf zwei der schon bekannten versetzten Seiten (PB02 S. 42, PB12 S. 48; Abschnitt 2). Abweichungen von 1–2 € (17 Zeilen) sind Rundungen im PDF.

## 1. Lage, Aufbau, Umfang
- **Lage:** Teil B steht nur auf Ebene der Produktgruppen, in jedem PG-Abschnitt nach Teilergebnisplan (2 S.) und Teilfinanzplan A (1 S.), z. B. PB12.pdf 2025/2026: 1.12.01 S. 4–5 Ergebnisplan, S. 6 Teil A, S. 7 ff. Teil B. Kopf jeder Seite: „Teil B: Investitionseinzelmaßnahmen – Investitionsmaßnahmen oberhalb der festgelegten Wertgrenzen“.
- **Spalten (12):** 1–2 Ergebnis (2025/2026: 2022, 2023), 3 Ansatz Vorjahr (2024), 4 Ansatz 2025, 5 VE 2025, 6 Ansatz 2026, 7 VE 2026, 8–10 Planung 2027–2029, 11 „bisher bereitgestellt (einschl. Sp. 3)“, 12 „Gesamteinzahlung/-auszahlung (Sp. 4, 6, 8–11)“. 2023/2024 entsprechend zwei Jahre früher (Ansatz 2023, 2024, Planung 2025–2027).
- **Zeilen je Maßnahme** (nur gefüllte werden gedruckt; eigene Nummern, abweichend von Teil A): 1 Investitionszuwendungen, 2 Veräußerung von Sachanlagen, 3 Beiträge, 4 sonstige Einzahlungen, 6 Grundstücke/Gebäude, 7 Baumaßnahmen, 8 bewegliches Anlagevermögen, 9 aktivierbare Zuwendungen, 10 sonstige Auszahlungen, 12 Saldo. Zuordnung zu Teil A: 1→1, 2→2, 3→4, 4→5, 6→7, 7→8, 8→9, 9→11, 10→12, 12→14 (über die Prüfsummen bestätigt). Häufigkeit beider Ausgaben: Zeile 7 1.351-mal, 8 465-mal, 1 337-mal, übrige zusammen 123-mal.
- **Kennung:** Das PDF druckt keine Maßnahmennummer, nur eine Bezeichnung (höchstens 40 Zeichen; 44 Bezeichnungen mit genau 40 Zeichen sind sichtbar gekürzt, z. B. „Rheinuferpromenade 3.BA Städtebauförderu“, PB09.pdf 2025/2026 S. 14). Eine Maßnahme ist nur über Ausgabe, PG und Bezeichnung zu erkennen; 78 Bezeichnungen kommen je Ausgabe mehrfach vor (z. B. dieselbe Straße bei Kanalbau in PB 11 und Straßenbau in PB 12). 830 Paare aus PG und Bezeichnung stehen in beiden Ausgaben.
- **Wertgrenze:** In den PDF der Produktbereiche und im Vorbericht nicht beziffert (vorbe.pdf S. 4 nennt nur die Summenbildung). Die Haushaltssatzung 2025/2026 § 7 (hhsatz.pdf S. 4) nennt 2 Mio. € (Planungen vorab in die Gremien) und 250.000 € (neue Maßnahmen gesperrt); das sind Bewirtschaftungsregeln, keine Grenze für Teil B. Tatsächlich deckt Teil B alle investiven Ein- und Auszahlungen außer Finanzanlagen: Ansatz 2026 Auszahlungen 191.603.105 € in Teil B zu 368.565.904 − 176.962.800 = 191.603.104 € in Teil A (Summe der PG). Kleinere Beträge stehen in Sammelposten („Beschaffungen …“, „Kleinere Straßenbaumaßnahmen“, „Bezirksbudget …“); der kleinste Ansatz 2026 ist 1.000 €.
- **Berichtigung zu ERWEITERUNG.md:** Dort „185,8 von 191,6 Mio. €“ und „301 mit Ansatz“. Nach vollständigem Lesen: 191,6 von 191,6 Mio. € (Rundung 1 €); 305 Maßnahmen mit Auszahlungsansatz 2025 oder 2026, 315 mit irgendeinem Ansatz 2025 oder 2026 (auch Einzahlungen).
- **Größe (2025/2026):** 278 Maßnahmen mit Auszahlungsansatz 2026; die zehn größten tragen 41,5 % davon (2023/2024 für 2024: 56,3 %), 182 liegen unter 250.000 €. 59 Maßnahmen haben Verpflichtungsermächtigungen (VE 2025 49,7, VE 2026 79,1 Mio. €).

| PB | 2023/2024: Maßnahmen / mit Ansatz 2023 o. 2024 / Seiten | 2025/2026: Maßnahmen / mit Ansatz 2025 o. 2026 / Seiten |
|---|---|---|
| 01 Innere Verwaltung | 51 / 20 / 26 | 54 / 24 / 28 |
| 02 Sicherheit und Ordnung | 33 / 22 / 16 | 32 / 21 / 16 |
| 03 Schulträgeraufgaben | 32 / 23 / 12 | 27 / 22 / 11 |
| 04 Kultur und Wissenschaft | 23 / 14 / 13 | 23 / 13 / 13 |
| 05, 07, 10, 14, 16, 17 zusammen | 31 / 16 / 20 | 31 / 11 / 20 |
| 06 Kinder-, Jugend- und Familienhilfe | 48 / 11 / 16 | 44 / 10 / 15 |
| 08 Sportförderung | 66 / 29 / 19 | 52 / 28 / 15 |
| 09 Raumplanung, Stadtentw., Geoinfo | 23 / 7 / 9 | 31 / 19 / 13 |
| 11 Ver- und Entsorgung | 244 / 23 / 63 | 240 / 19 / 62 |
| 12 Verkehrsflächen und -anlagen, ÖPNV | 192 / 63 / 54 | 197 / 82 / 54 |
| 13 Natur- und Landschaftspflege | 171 / 68 / 47 | 143 / 61 / 39 |
| 15 Wirtschaft und Tourismus | 11 / 6 / 9 | 8 / 5 / 7 |
| **Summe** (105 PG je Ausgabe) | **925 / 302 / 304** | **882 / 315 / 293** |

Mehr als die Hälfte der Maßnahmen (2025/2026: 461) hat nur Werte in Spalte 11 („bisher bereitgestellt“), also keinen Ansatz und keine Planung mehr. Namen der PB wie in `produktbereiche.tsv`.

## 2. Lesbarkeit
- Ein Block je Maßnahme: Bezeichnung links bündig, darunter die Zeilen mit Nummer und Vorzeichen. Spalten über die Mitte der Spaltennummern im Kopf (1–12) und eine Verschiebung je Block (rechter Rand der Spalte 12). 2025/2026 sind Blöcke auf 20 Seiten um 1,7–4 pt versetzt, auf PB02 S. 42 um 9 pt; 2023/2024 nur pb11.pdf S. 40 (22 pt, nur Nullen betroffen). Kein Block reicht über einen Seitenumbruch (keine Seite beginnt mit Zeilen ohne Bezeichnung, außer den Fällen unten).
- **Maßnahmen ohne Zeile 12** (Einzahlungen = Auszahlungen, Saldo überall 0): 8 bzw. 6, alle in sich stimmig (z. B. PB03.pdf 2025/2026 S. 44). Ein Leser darf die nächste Bezeichnung daher nicht erst nach Zeile 12 erwarten.
- **Problemseiten, alle 2025/2026:**
  - PB02.pdf S. 42 „Fahrzeuge - Brandschutz“: Vorzeichen und Ziffern der Saldozeile auf zwei Zeilen getrennt; die Zeilen 1, 4, 8 sind lesbar, der Saldo muss nachgerechnet werden.
  - PB12.pdf S. 48: Maßnahme ohne Bezeichnung, Ziffern gesperrt („- 1.0 0 0“); Beträge 1.000, 1.000, 2.950, 4.950 €, Spalten unsicher (Planjahre, nicht Ansatz 2025/2026).
  - PB12.pdf S. 13: Bezeichnung „Effertzstr. BN“ ohne Zeilen direkt über „Endenicher Allee BN“; die Beträge gehören zu „Endenicher Allee BN“ (2023/2024, pb12.pdf S. 14: 848.548 + 73.483 € = 922.031 € bisher bereitgestellt).
  - PB12.pdf S. 18: zwei Bezeichnungen übereinander („Auerberger-Mitte BN“, „Mondorfer Str. BN“) über dem ersten Block, der zweite Block ohne Bezeichnung. Über 2023/2024 (pb12.pdf S. 18, „Mondorfer Str. BN“, Ansatz 2024 500.000 €) gehört der erste Block zu „Mondorfer Str. BN“, der zweite zu „Auerberger-Mitte BN“ (abgeleitet). Eine Lesung der Reihe nach vertauscht die Namen.
- Die in ERWEITERUNG.md genannten Seiten PB02 S. 54, PB06 S. 23, PB12 S. 53 und PB16 S. 19 lesen sich mit der Verschiebung je Block fehlerfrei. 2023/2024 hat keine dieser Störungen.
- **Folgerung:** Ein Leser braucht die Verschiebung je Block, das Zusammenfügen gesperrter Ziffern, die Prüfungen aus der Tabelle oben und eine feste Ausnahme für PB12 S. 18 (Namensfolge) mit Beleg.

## 3. Ortsbezug der Bezeichnungen (abgeleitet)
Abgleich mit den vorhandenen Regeln der Stufe B (`Gazetteer.locate`: Straßenverzeichnis `strassen_bonn.json`, Ortsteile, Stadtbezirke) und `Objekte.im_titel` (`objekte_bonn.json`). Das Kürzel am Ende (BN, BE, GO, HA) gilt als Stadtbezirk Bonn, Beuel, Bad Godesberg, Hardtberg und dient zur Unterscheidung gleicher Straßennamen; 559 der 882 Maßnahmen 2025/2026 tragen es.

| 2025/2026 | alle 882 | mit Ansatz 2025/2026 (315) | Auszahlungen Ansatz 2026 |
|---|---|---|---|
| Straße oder Gebäude erkannt | 447 | 88 | 36,1 Mio. € |
| nur Ortsteil | 45 | 11 | 8,6 Mio. € |
| nur Stadtbezirk (Kürzel) | 113 | 53 | 31,6 Mio. € |
| ohne Ortsbezug erkannt | 277 | 163 | 115,4 Mio. € |

- **Durchsicht der 99 Treffer mit Ansatz:** rund 7 zweifelhaft – „Bad Godesberg“ als Gebäude statt Stadtbezirk (3, z. B. „ISEK Bad Godesberg“), „Kölnstraße“ ohne Kürzel in mehreren Stadtbezirken (2), „Rheinufer“ (1), falsches Gebäude bei richtigem Ortsteil (1).
- **Nicht erkannt, aber benannt:** Bäder, Stadthalle, Brücken, Bäche, Kläranlagen, WCCB, Bahnhofsvorplatz, Bebauungspläne (22 Bezeichnungen mit Plannummer, 10 Nummern, davon 5 im Datensatz der rechtskräftigen Pläne), Abkürzungen wie „Siebengebirgstr.“ oder „Königswinterer Str“ ohne Punkt.
- **Stichprobe** (60 Maßnahmen mit Ansatz, zufällig, von Hand beurteilt): 2025/2026 ja 17, unklar 9, nein 14 von 40; 2023/2024 ja 9, nein 11 von 20. Unklar sind vor allem reine Stadtbezirkskürzel und Sammelposten.
- **Schätzung:** Von 315 Maßnahmen mit Ansatz 2025/2026 ließen sich rund 110–130 auf Straße, Gebäude oder Ortsteil verorten (≈ 35–40 %, darunter die meisten in PB 12, 08, 11, 13), weitere rund 50 nur auf den Stadtbezirk. Gemessen am Ansatz 2026 ist es weniger als ein Viertel; die großen Beträge stehen in Sammelposten und Pauschalen ohne Ort (z. B. „Gemeindestraßen“ 10,0 Mio. €, PB12.pdf S. 9; „Pauschale Bäderkonzept“ 11,0 Mio. €, PB08.pdf S. 25). Straßen sind Linien über mehrere Ortsteile, keine Punkte; eine Maßnahme sagt nichts über Lage oder Umfang der Bauarbeiten.

## 4. Datenschutz und Sonderfälle
- **Keine Namen von Privatpersonen** in den 924 verschiedenen Bezeichnungen. Personennamen kommen nur in Straßennamen und in einer nach einer Person benannten Stiftung vor (PB17.pdf 2025/2026 S. 13; die PG heißt ebenso, siehe ERWEITERUNG.md).
- **Verträge mit Einzelnen:**
  - „Leibrenten“ (Zeile 6, Erwerb von Grundstücken/Gebäuden): PB01.pdf 2025/2026 S. 90, nur „bisher bereitgestellt“ 92.662 €, kein Ansatz; 2023/2024 PB01 S. 86 und PB04 S. 34 (zusammen zwei Posten). Die Gegenseite sind bestimmbare Privatpersonen.
  - „Theater Zuschuss gem Intendantenvertrag“ (Zeile 7): 2023/2024 PB04.pdf S. 51 mit Ansatz 2024 5.088.462 €; 2025/2026 PB04.pdf S. 50 ohne Ansatz, Gesamt 23.261.539 €. Betrifft einen Vertrag mit einer Person in öffentlicher Funktion.
- Der Kopf jeder PG-Seite nennt eine verantwortliche Person; sie wird wie bisher nicht gelesen.
- **Vorschlag:** Bezeichnungen mit „Leibrente“ und „Intendantenvertrag“ nicht einzeln zeigen, nur in den Summen der PG (mit Hinweis „ein Posten zu einem Vertrag mit einer Einzelperson ist nur in der Summe enthalten“); Prüfung im Leser wie `maske.privat`. Bei der Auswahl „nur Maßnahmen mit Ansatz 2025/2026“ entfallen beide 2025/2026 ohnehin. Keine Verortung von Grunderwerb („Grundstücksmanagement“, „Flächenankauf“).

## 5. Mögliche Darstellung
1. **Liste auf `haushalt/`:** Abschnitt „Einzelmaßnahmen“ je PB und PG (aufklappbar, wie die Kacheln), Bezeichnung wörtlich, Ansatz 2025 und 2026, Ergebnis 2023, VE, Gesamtkosten; nur Maßnahmen mit Ansatz; Summe je PG mit Verweis auf Teil A.
   - Aufwand: 1–1,5 Tage (Leser mit Prüfsummen, Daten, Seite, Prüfbogen). Risiko: gering bei Beträgen; mittel bei der Deutung (Sammelposten, gekürzte und abgekürzte Bezeichnungen, „bisher bereitgestellt“, Ist liegt weit unter dem Ansatz).
2. **Wie 1, dazu Themenseiten:** je Themenseite die Maßnahmen des zugeordneten PB (z. B. PB 12 Verkehr, PB 03 Schule, PB 13 Klima, PB 04 Kultur) als kurze Liste mit Link auf `haushalt/`.
   - Aufwand: + ½ Tag. Risiko: gering; ein PB deckt sich nicht mit dem Thema (z. B. Schulbau beim SGB, nicht in Teil B).
3. **Wie 1, dazu Karte:** zuschaltbare Ebene „Investitionen (Haushalt)“ mit Straßen als Linie und Gebäuden als Punkt, nur Treffer mit Straße/Gebäude/Ortsteil, Konfidenz und Methode wie Stufe B, Stadtbezirkskürzel nur in der Liste; Link vom Vorgang nur bei belegter Verbindung (Drucksache), keine automatische Zuordnung zu Vorlagen.
   - Aufwand: + 1–1,5 Tage (Verortung, Ausnahmen, Prüfbogen der Verortung mit 30–50 Maßnahmen). Risiko: mittel (gleichnamige Straßen, Sammelposten, Linie wirkt wie Baustelle, Lage innerhalb einer langen Straße offen).

## Offene Entscheidungen für den Auftraggeber
1. Umfang: nur Maßnahmen mit Ansatz 2025/2026 (315) oder alle 882, auch solche nur mit „bisher bereitgestellt“? Auch 2023/2024 zum Vergleich?
2. Spalten: Ansätze und Ergebnisse wie bisher, dazu VE und Gesamtkosten? Planung 2027–2029 bleibt nach der Entscheidung vom 27.10.2026 außen vor?
3. Umgang mit „Leibrenten“ und „Intendantenvertrag“ wie in Abschnitt 4 vorgeschlagen?
4. Darstellung: Option 1, 2 oder 3; bei 3 auch Bäche und Bebauungspläne (Geltungsbereich) verorten?
5. Abkürzungen (BK, FH, ABK, BgA, S 13; 149-mal „BK“) erklären nur mit Fundstelle, sonst unaufgelöst lassen?
6. Ist 2024 der Einzelmaßnahmen: ob der Jahresabschluss 2024 eine Teilfinanzrechnung B enthält, ist nicht geprüft.
