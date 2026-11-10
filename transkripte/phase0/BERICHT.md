# Ratstranskripte – Schritt 0 (Prüfung)

Stand 10.11.2026 · Freigabe des Auftraggebers: „ja, Schritt 0 beginnen“; Mika Baumeister und bonn.biz sind vorab informiert (Mitteilung des Auftraggebers 10.11.2026).

Messung mit `messung.py`: GraphQL von OParl-Lite, eine Anfrage je Sekunde, ohne Transkripttext. Ergebnisse in `abdeckung.tsv` und `trefferquote.tsv`.

## Abdeckung

108 Sitzungen des Rates und des Hauptausschusses vom 01.01.2021 bis heute (Sitzungsliste der Stadt). Alle ließen sich einer Sitzung in OParl-Lite zuordnen.

| Jahr | Rat | Hauptausschuss |
|---|---|---|
| 2021 | 9 von 9 | 3 von 9 (nur „anstelle des Rates“) |
| 2022 | 10 von 11 | 0 von 7 |
| 2023 | 4 von 11 | 0 von 8 |
| 2024 | 4 von 10 | 0 von 8 |
| 2025 | 11 von 12 | 0 von 5 |
| 2026 | 12 von 13 | 0 von 5 |

Zusammen haben 53 von 108 Sitzungen eine Aufzeichnung, im Rat 50 von 66. Die jüngste Aufzeichnung ist vom 28.09.2026. Lücken bestehen im Rat 2023 und 2024. Ob dort Videos fehlen oder noch nicht zugeordnet sind, ist offen (Frage an bonn.biz).

## Suche nach der Drucksachennummer

20 Vorlagen mit öffentlicher Beratung in einer Sitzung mit Aufzeichnung (Zufallsauswahl, fester Startwert): 0 von 20 mit einem Treffer, auch über alle Sitzungen hinweg 0 Treffer. Drucksachennummern werden in den Sitzungen nicht gesprochen oder nicht als solche erkannt. Zur Gegenprobe arbeitet die Suche sonst: „Nordbrücke“ ergibt 85 Abschnitte, „Tagesordnungspunkt“ 475.

## Folgen für das Konzept

- Der Suchlink mit der Drucksachennummer entfällt; er führte immer ins Leere.
- Im Vorgang bleiben der Link zum Video der Sitzung und ein Link „Transkript durchsuchen“. Womit die Suche vorbefüllt wird, ist offen: leer oder mit einem Wort aus dem Titel (abgeleitet).
- Hauptausschuss: Aufzeichnungen gibt es nur 2021 für Sitzungen „anstelle des Rates“. Der Hinweis auf die Grenzen nennt das.

## Ansicht (Attrappe)

`transkript_vorgang_desktop.png` und `transkript_vorgang_telefon.png` zeigen die Vorlage 252458 (Rat, 12.03.2026). Die Zeile ist nur im Browser eingefügt und als „Entwurf“ markiert; der Code ist unverändert.
