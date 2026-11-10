# Strukturdaten Bonn – Phase 0 (Exploration)

Stand 10.11.2026 · Grundlage: Prompt „Ratsatlas Bonn – Strukturdaten“ v0.1 · ohne Produktionscode

Entscheidungen des Auftraggebers vom 10.11.2026:
- Phase 0 für Bonn beginnt jetzt. Den Datenvertrag „Strukturdaten v1“ legt Bonn als Entwurf an, Köln übernimmt ihn.
- Phase 0 schlägt vor, wie sich die Strukturdaten zur vorhandenen Kontextebene verhalten.
- Die Stadt Bonn hat die Veröffentlichung freigegeben (Mitteilung des Auftraggebers 10.11.2026), und zwar ohne Pflicht zur Namensnennung (CC0 bzw. dl-de/zero-2.0). Die Freigabe umfasst:
  - die Werte des Strukturdatenatlas,
  - daraus abgeleitete Werte je Ortsteil,
  - Wanderungsdaten.

  Damit entfällt der Lizenzvorbehalt aus dem Prompt; die Werte können unter `data/strukturdaten/` liegen.

Dateien in diesem Ordner:
- `audit_quellen.tsv`: Quellen mit Prüfstand
- `indikatoren_phase0.tsv`: 58 Indikatoren ohne Werte, mit Typvorschlag
- `raumabgleich_phase0.tsv`: statistischer Bezirk → Ortsteil, nach Fläche und nach Einwohnern

## 1 Kurzfassung

- **Umfang:** Der Strukturdatenatlas liefert 58 Indikatoren in 9 Themen für 65 statistische Bezirke. Dazu kommen Vergleichswerte für die 4 Stadtbezirke und ganz Bonn. Die Zeitreihen reichen meist von 2014 bis 2025, beim Arbeitsmarkt und SGB II von 2012 bis 2024, beim Gebäudebestand und der Bautätigkeit von 2011 bis 2025.
- **Lesbarkeit und Abgleich:** Die Daten sind maschinenlesbar. Bei Einwohnern, Wohnungen und Haushalten (außer 2017) stimmen die Summen der Bezirke genau mit den Werten für ganz Bonn überein.
- **Typen:** Die Namen einiger Indikatoren täuschen. „Personen in Bedarfsgemeinschaften“ ist zum Beispiel ein Wert je 1.000 Einwohner. Typ und Einheit müssen daher aus dem Metatext kommen, nicht aus dem Namen.
- **Raumabgleich:** 50 von 65 statistischen Bezirken liegen mit mindestens 97 % ihrer Einwohner in einem Ortsteil. Für 30 von 51 Ortsteilen lassen sich Werte sauber aus ganzen Bezirken bilden. Endenich entspricht annähernd 120 Neu-Endenich ∪ 121 Alt-Endenich; 1 % der Einwohner von 122 Poppelsdorf wohnt ebenfalls in Endenich. Die übrigen Ortsteile, vor allem in Beuel und Duisdorf, schneiden Bezirke.
- **Wegweiser Kommune:** Die Schnittstelle ist erreichbar, die Daten stehen unter CC0 und reichen meist bis 2023. Zehn bis zwölf Indikatoren haben ein Gegenstück in der Stadtstatistik (Abschnitt 5).
- **Empfehlung:** Die Daten werden nach dem Vertrag abgelegt. In der Oberfläche wird die vorhandene Ebene „Zahlen“ erweitert, statt eine zweite Ebene neben sie zu stellen (Abschnitt 6).

## 2 Stand im Repository

| Raumebene | Verwendung heute |
|---|---|
| 51 Ortsteile (CC0) | Geokodierung der Vorlagen, Gebietsauswahl, Gebietsseiten, Kontextdaten (`kontext.json`) |
| 4 Stadtbezirke (CC0) | Vorlagen ohne genaueren Ort, Vergleichswerte der Kontextdaten, „Mitmachen“ |
| 100-m-Gitter Zensus 2022 | Einwohner und Altersanteile je Ortsteil (`data/kontext/zensus_bonn.tsv`) |
| statistische Bezirke | nicht verwendet |

Die Kontextebene zeigt je Ortsteil: Einwohner (Zensus 2022), Anteile unter 18 und ab 65, Miete, Bodenrichtwert, Haltestellen, Kitas, Hitze, Überschwemmung und Wahlbeteiligung. Diese Werte erscheinen als Flächenfarbe (`flaechen=kontext-…`), im Steckbrief „Zahlen zu …“ und im Vorgang unter „Zum Ortsteil“.

## 3 Strukturdatenatlas

**Aufbau.**
- `data.js` beschreibt Raumeinheiten, Themen und Indikatoren.
- `Statistische_Bezirke-t0.js` bis `-t8.js` enthalten je Indikator und Jahr `values`: 65 Werte in der Reihenfolge der Bezirke.
- `comparisonValues` enthält 5 Werte: 4 Stadtbezirke und ganz Bonn.
- `properties.metatext` enthält die Definition mit Stichtag.
- Die Dateien sind ohne Cache-Parameter abrufbar und wurden zuletzt am 03.02.2026 geändert.

**Typen (Vorschlag in `indikatoren_phase0.tsv`):**

| Typ | Zahl |
|---|---|
| anteil | 20 |
| anzahl | 19 |
| quote | 11 |
| mittelwert | 3 |
| dichte | 1 |
| kategorie | 4 |

- Die vier Kategorien sind „Häufigster Zuwanderungshintergrund“ und drei Verteilungen (Gebäudegröße, Wohnungsgrößen, Baualtersklassen). Bei den Verteilungen stehen die Kategorien in der Quelle im Feld des Jahres und gelten nur für 2025.
- Bei „Personen in Bedarfsgemeinschaften“, „Kinder in Bedarfsgemeinschaften“ und „Leistungsberechtigte“ täuscht der Name: Es sind Quoten je 1.000 Einwohner, je 1.000 Kinder und je 1.000 Erwerbsfähige.
- Drei Indikatoren haben keinen Metatext: 30–64-Jährige, 65–74-Jährige, fertiggestellte Wohngebäude.

**Fehlende Werte („NaN“).**
- Fast alle NaN stehen in drei nahezu unbewohnten Bezirken: 129 Kottenforst, 380 Siegaue, 389 Ennert, über alle Reihen. Nach dem Zensus 2022 leben dort 23, 24 und 69 Menschen. Ob die Werte wegen Geheimhaltung oder aus anderen Gründen fehlen, sagt die Quelle nicht. Vorschlag: `status=fehlt` mit dem Hinweis „in der Quelle nicht ausgewiesen“, bis die Statistikstelle den Grund nennt.
- Außerdem gibt es drei Einzelzellen: 141 Gronau-Bundesviertel 2013 (Bedarfsgemeinschaften, Größe) und 118 Bonner Talviertel 2020 (Baugenehmigungen).
- Die Metatexte der Daten der Bundesagentur für Arbeit nennen „* = Fallzahl unter 10“. Die Quelle schreibt aber NaN statt „*“, geheim und fehlend sind dort also nicht unterscheidbar. Vorschlag: NaN in bewohnten Bezirken bei Daten der Bundesagentur gilt als `geheim`, sonst als `fehlt`.

**Plausibilität.** Ich habe 234 Reihen von Anzahlen gegen die Werte für ganz Bonn geprüft:
- **Haushalte 2017 sind in der Quelle fehlerhaft.** Elf Bezirke tragen etwa den doppelten oder einen vielfachen Wert, zum Beispiel 495 Lengsdorf mit 62.116 statt rund 2.600. Die Summe beträgt 239.986, der Wert für ganz Bonn 170.072, und auch die Vergleichswerte der Stadtbezirke passen nicht. Vorschlag: Die Reihe nicht übernehmen und der Statistikstelle melden.
- Bei den sozialversicherungspflichtig Beschäftigten, den Bedarfsgemeinschaften und den fertiggestellten Wohnungen liegt der Wert für ganz Bonn leicht über der Summe der Bezirke (bis 1,3 %). Erklärbar ist das durch Fälle ohne Bezirkszuordnung. Die Werte bleiben unverändert, mit Hinweis.

## 4 Raumabgleich (vorläufig)

- **Geometrie:** Die Geometrie der statistischen Bezirke auf stadtplan.bonn.de (`OD=4859`) antwortete am 10.11.2026 mit HTTP 502. Für Phase 0 habe ich die Kartengeometrie des Atlas umgerechnet (`_STA_2016.shp1.js`, Stand 2016). Ihre Fläche ergibt 96,4 % der Ortsteilflächen, der Unterschied geht auf das Raster und den Stand zurück. Vor Phase 2 muss die Geometrie mit der aktuellen Fassung verglichen werden.
- **Gewichtung:** Ich habe nach Einwohnern gewichtet. Grundlage sind die Mittelpunkte der Zensus-Zellen, die schon im Repository liegen. Die Fläche allein täuscht bei Wald, Rheinaue und Gewerbe.

| Ergebnis | Zahl |
|---|---|
| Bezirke mit ≥ 97 % der Einwohner in einem Ortsteil | 50 von 65 |
| Ortsteile, deren Einwohner zu ≥ 95 % in ganz zugehörigen Bezirken wohnen | 30 von 51 |
| geteilte Bezirke | 15, darunter 114, 119, 372–374, 384, 387, 497 |

**Endenich:** 120 und 121 liegen vollständig in Endenich. Vom Bezirk 122 Poppelsdorf fallen 8 % der Fläche und 1 % der Einwohner nach Endenich. Endenich entspricht also annähernd, aber nicht genau 120 ∪ 121.

**Folge für den Datenvertrag:** Anzahlen lassen sich nach Einwohneranteilen auf Ortsteile verteilen (`status=abgeleitet`), Anteile und Quoten nur mit Zähler und Nenner. Für die 21 Ortsteile mit geteilten Bezirken wäre jeder abgeleitete Wert eine Schätzung. Vorschlag: Werte je Ortsteil nur für die 30 sauber zusammengesetzten Ortsteile. Für die übrigen zeigt die Seite die beteiligten Bezirke.

## 5 Wegweiser Kommune

- **Schnittstelle:** Die OpenAPI-Beschreibung meldet `info.version` 3.12.0, `rest/statistics/version` meldet 2026-10-15T08:45:18Z. Es gibt 393 Indikatoren. Der CSV-Export (`rest/export/{a}+{b}+bonn+koeln+wuppertal+2023.csv`) nennt im Fuß „Creative Commons Zero 1.0“.
- **Regionen:** `bonn` (05314000), `koeln` (05315000) und `wuppertal` (05124000).
- **Unterschiedliche Bevölkerungsbegriffe:** Der Wegweiser nennt für Bonn 2023 335.789 Einwohner (Fortschreibung der amtlichen Statistik), die Statistikstelle 338.224 (Melderegister, Hauptwohnsitz ohne Sammelunterkünfte). Beide Zahlen gehören deshalb getrennt angezeigt.

Vorschlag für die Vergleichsebene; die Friendly-URLs sind aus `rest/indicator/list` geprüft:

| Friendly-URL | Gegenstück Statistikstelle | Hinweis |
|---|---|---|
| `bevoelkerung` | Einwohner (i0) | andere Zählweise, siehe oben |
| `bevoelkerungsentwicklung-ueber-die-letzten-5-jahre` | – | nur Gesamtstadt |
| `durchschnittsalter` | Durchschnittsalter (i9) | – |
| `altenquotient` | Altenquotient (i10) | gleiche Definition (65+ je 100 der 20–64-Jährigen) |
| `jugendquotient` | Jugendquotient (i11) | gleiche Definition |
| `auslaenderanteil` | Ausländeranteil (i23) | – |
| `sgb-ii-quote` | Leistungsberechtigte (i41) | Bezug: unter 65 bzw. 15–66 Jahre |
| `kinderarmut` | Kinder in Bedarfsgemeinschaften (i40) | unter 15 bzw. unter 18 Jahre |
| `einpersonen-haushalte` | Einpersonenhaushalte (i26) | Wegweiser bis 2022 |
| `haushalte-mit-kindern` | Haushalte mit Kindern (i27) | Wegweiser bis 2022 |
| `arbeitslose-an-den-svb` | Arbeitslosenquote (i29) | im Wegweiser keine „Arbeitslosenquote“; Definition abweichend |
| `wanderungssaldo` | Wanderungsdaten | kleinräumige Lieferung offen |

## 6 Verhältnis zur vorhandenen Kontextebene

| Weg | Vorteil | Nachteil |
|---|---|---|
| A: eigene Ebene laut Prompt (Panel und Choroplethen auf 65 Bezirken) | entspricht dem gemeinsamen Kern für Bonn, Köln und Wuppertal | zwei ähnliche Bedienwege für „Zahlen“; Einwohner doppelt (Zensus 2022 und Melderegister 2025) |
| B: vorhandene Ebene erweitern (Auswahl der Raumebene: Ortsteil oder statistischer Bezirk; neue Kennzahlen in derselben Liste) | ein Bedienweg; bekannte Legende, Steckbrief und „Zum Ortsteil“ bleiben | das Frontend muss beide Datenquellen lesen |
| C (Empfehlung): Datenvertrag v1 für die Ablage, Darstellung wie B | Daten wiederverwendbar für Köln und den späteren Kern, Bedienung einheitlich; Einwohner und Altersanteile je Ortsteil später aus dem Melderegister statt aus dem Zensus (nur für die 30 sauber zusammengesetzten Ortsteile) | Anpassung der Flächenauswahl und des Steckbriefs; der Prompt sieht ein eigenes Panel vor |

## 7 Für Phase 1 zu entscheiden

1. Weg A, B oder C (Abschnitt 6).
2. NaN-Regel: bei Daten der Bundesagentur `geheim`, sonst `fehlt`; die drei nahezu unbewohnten Bezirke `fehlt` mit Hinweis. Dazu eine Rückfrage an die Statistikstelle.
3. Haushalte 2017: nicht übernehmen und der Statistikstelle melden.
4. Werte je Ortsteil nur für sauber zusammengesetzte Ortsteile, oder nach Einwohnern verteilt mit Kennzeichnung „geschätzt“.
5. Auswahl der Wegweiser-Indikatoren (Abschnitt 5).
6. Wanderungsdaten: Wie kommen sie zu uns (Lieferung als Datei oder Abruf)?
7. Die genaue Lizenzbezeichnung aus der schriftlichen Antwort der Stadt für `data/LICENSE-DATA.md`: CC0 oder dl-de/zero-2.0.

## 8 Grenzen

- Der Raumabgleich beruht auf der Geometrie von 2016 und auf Zensus-Zellen von 2022 (Mittelpunktregel). Er ist vorläufig, bis die aktuelle Geometrie erreichbar ist.
- Die Typvorschläge sind aus Namen und Metatexten erschlossen und nicht von der Statistikstelle bestätigt.
- Werte stehen in diesem Bericht nur als Beispiele für Prüfungen. Die Wegweiser-Werte habe ich nur für Bevölkerung und Durchschnittsalter 2023 abgerufen.
