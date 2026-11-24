# Zu- und Wegzüge – Phase 0

Stand 24.11.2026 · Entscheidung des Auftraggebers vom 24.11.2026: eigene Seite mit öffentlichen Daten für ganz Bonn; der Saldo je Ortsteil kommt erst nach der Lieferung der Stadt (`strukturdaten/WANDERUNG.md`). Diese Phase prüft nur, Produktionscode entsteht noch nicht.

## 1. Ergebnis in Kürze

- **Kleinräumig gibt es keine öffentlichen Daten.** Für Stadtbezirke, Ortsteile und statistische Bezirke sowie für Umzüge innerhalb Bonns hilft nur die Lieferung der Statistikstelle.
- **Ströme zwischen Kreisen 2025 sind offen und vollständig lesbar.**
  - Quelle ist die Kreiswanderungsmatrix der Statistischen Ämter, Datei `KWM_GES_NAT_ALT_2025.zip` (8,1 MB).
  - Sie enthält Zuzüge, Fortzüge und Saldo je Kreispaar, nach Alter, Geschlecht und Staatsangehörigkeit.
  - Für 2022 bis 2024 gibt es nur Salden.
- **Für eine Zeitreihe ohne Konto taugt nur der Wegweiser Kommune.**
  - Er bietet Zuzüge, Fortzüge und Saldo von 2006 bis 2023, dazu Bildungs-, Familien- und Alterswanderung.
  - Alle Werte sind gleitende Mittel über 4 Jahre und auf je 1.000 Einwohner gerechnet. Absolute Zahlen je Jahr gibt es dort nicht.
- **Absolute Zahlen je Jahr** führt IT.NRW (Landesdatenbank, Tabellen 12711). Die Schnittstelle verlangt ein Konto; ob es kostenlos ist, ist ungeprüft.
- **Ausland fehlt in der Matrix.** Die Matrix enthält nur Kreise in Deutschland; das Ausland steht nur bei IT.NRW (2025, nach Staaten).

## 2. Befunde aus der Matrix 2025 (Bonn, Kreis 05314)

| | Zuzüge nach Bonn | Fortzüge aus Bonn | Saldo |
|---|---:|---:|---:|
| aus/in andere Kreise Deutschlands | 14.687 | 17.463 | −2.776 |
| davon NRW | 9.339 | 11.960 | −2.621 |
| davon Rheinland-Pfalz | 1.437 | 1.646 | −209 |

Nach Alter:

| Altersgruppe | Saldo |
|---|---:|
| unter 18 Jahre | −1.013 |
| 18 bis unter 25 Jahre | +980 |
| 25 bis unter 30 Jahre | −626 |
| 30 bis unter 50 Jahre | −1.719 |
| 50 bis unter 65 Jahre | −308 |
| 65 Jahre und älter | −164 |

- **Partner:** Bonn tauscht mit 380 Kreisen. 31 davon haben mindestens 100 Zuzüge oder Fortzüge. Die 20 größten stehen in `partner_2025.tsv`.
  - Rhein-Sieg-Kreis: 3.450 Zuzüge, 5.079 Fortzüge.
  - Köln: 1.465 Zuzüge, 1.637 Fortzüge.
  - Ahrweiler: 375 Zuzüge, 720 Fortzüge.
- **Geheimhaltung:** 404 von 2.660 Zellen mit Zuzügen sind leer (Cell-Key-Verfahren); selbst gebildete Summen können leicht abweichen.
- **Einordnung:** Innerhalb Deutschlands verliert Bonn Einwohner, vor allem Familien an das Umland. Die Stadt nennt für 2025 trotzdem insgesamt +670 (Melderegister). Den Unterschied machen Zuzüge aus dem Ausland, die in der Matrix fehlen. Die Seite muss das sagen, sonst entsteht ein falsches Bild. Melderegister und amtliche Statistik dürfen nicht gemischt werden.

## 3. Wegweiser Kommune (je 1.000 Einwohner, gleitendes Mittel über 4 Jahre)

| Jahr | Zuzüge | Fortzüge | Saldo | Bildungswanderung | Familienwanderung |
|---|---:|---:|---:|---:|---:|
| 2018 | 94,1 | 85,4 | 8,7 | 85,6 | −0,3 |
| 2020 | 82,6 | 77,4 | 5,1 | 72,0 | −4,3 |
| 2023 | 79,3 | 74,2 | 5,1 | 63,6 | −3,0 |

Diese Werte schließen das Ausland ein und stimmen in der Richtung mit dem Melderegister überein. Der Ratsatlas lädt den Wegweiser schon für die Strukturdaten (`pipeline/strukturdaten.py`); die neuen Kennzahlen lassen sich dort ergänzen.

## 4. Lizenzen

- **Kreiswanderungsmatrix:** Datenlizenz Deutschland – Namensnennung 2.0, laut der Seite „Open Data“ des Statistikportals; die Seite der Matrix selbst nennt keine Lizenz. Namensnennung ist Pflicht, Vorschlag: „Statistische Ämter des Bundes und der Länder, Kreiswanderungsmatrix 2025, dl-de/by-2-0“. Neue Zeile in `config.SOURCES`, `data/LICENSE-DATA.md` und im Quellen-Akkordeon.
- **Wegweiser Kommune:** wie bisher, Nennung „Bertelsmann Stiftung, wegweiser-kommune.de“.

## 5. Vorschlag für die Seite `zu-und-wegzuege/`

1. **Kopf:** die Zahlen 2025 für ganz Bonn in drei Kacheln (Zuzüge, Fortzüge und Saldo innerhalb Deutschlands), mit dem Hinweis auf das Ausland.
2. **Wohin und woher:**
   - Balken der 15 größten Partnerkreise, Zuzüge und Fortzüge gegenüber;
   - dazu eine kleine Karte der Region mit Kreisflächen nach Saldo, statt Pfeilen;
   - Tabelle aller Partner mit mindestens 100 Zügen als Alternative für Vorleseprogramme.
3. **Wer zieht:** Saldo nach Altersgruppen als Balken, in einfachen Worten: Junge Erwachsene ziehen zu, Familien ziehen ins Umland.
4. **Entwicklung:** Linie 2006–2023 aus dem Wegweiser (je 1.000, gleitendes Mittel), klar als solche bezeichnet.
5. **Grenzen und Quellen:**
   - keine Ortsteile, kein Ausland in der Matrix;
   - Melderegister und amtliche Statistik getrennt;
   - Lizenz im Akkordeon.
6. **Später:** Saldo je Ortsteil auf der Hauptkarte, sobald die Lieferung der Stadt vorliegt.

Technik wie die übrigen statischen Seiten:
- Pipeline-Schritt `wanderung` lädt die ZIP-Datei einmal im Jahr (Knopfdruck) und legt einen Auszug für Bonn in `data/wanderung/` ab, ohne die Matrix für ganz Deutschland.
- Seite im Schritt `seo`, Grafiken als SVG wie beim Haushalt, Link im Menü „Themen“ unter „Zahlen zum Gebiet“.

## 6. Offene Entscheidungen

1. Seite wie in Abschnitt 5 bauen?
2. Die Wegweiser-Zeitreihe aufnehmen, obwohl sie nur gleitende Mittel je 1.000 zeigt, oder ein Konto bei IT.NRW für absolute Zahlen anlegen (Aufgabe des Auftraggebers)?
3. Kreiskarte der Region: welcher Umkreis? Vorschlag: NRW und Rheinland-Pfalz; Kreise außerhalb nur in Balken und Tabelle.
