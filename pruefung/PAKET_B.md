# Paket B: Korrektheit und Betrieb (21.11.2026)

Umsetzung zu `BERICHT_2026-11.md`, Nr. 8, 9, 11, 12, 29–37 und 44 (Nr. 3 und 10 liegen in Paket 1).

| Nr. | Umgesetzt |
|---|---|
| 8 | Karte: eigener Ablauf `zeigeMarker` statt `cluster.zoomToShowLayer`. Ein Listener hört einmal zu und prüft, ob Punkt und Auswahl noch gelten. Verhalten sonst wie bisher (hineinzoomen, gestapelte Punkte auffächern). |
| 9 | `index.json`: ein Fehler (Netz, Server, kaputte Antwort) wird einmal wiederholt, dann erscheint eine Meldung mit „Erneut versuchen“. Nur bei 404 startet der Pilot (lokale Vorschau). |
| 11 | `live.yml` prüft, dass der Abruf von `oparl-bonn` und `oparl-lite` höchstens zwei Tage alt ist. |
| 12 | Anker im Link: liegt die Vorlage in einem anderen Gebiet, öffnet die Seite es über den Suchindex; fehlt sie, steht ein Hinweis im Startfenster. |
| 29 | Fehlen Kacheln oder Archivdateien in einem Lauf, bleiben die des letzten Stands (mit Hinweis). `kurzfassungen` hängt an `build` statt an `deploy`. |
| 30 | Gescheitertes Nachladen (Soll-Modell, Planregister, zuschaltbare Flächen, Bebauungspläne, „Wer entscheidet“) wird beim nächsten Öffnen wiederholt. |
| 31 | Ohne geladenes Gebiet wirft die Liste nicht mehr; unvollständige `zeit.json` oder `baustellen.json` brechen den Start nicht ab. |
| 32 | Sitzungsspur der Zeitleiste: Bezirksvertretung des gewählten Gebiets, Rat, Hauptausschuss und die Ausschüsse für Mobilität und Planung über Namensmuster (auch der Nachfolge-Ausschuss ab 2026). |
| 33 | Baustellen: Stand „gemeldetes Ende verstrichen“ und Hinweis, wenn die Quelle länger als sieben Tage nicht erreicht wurde; antworten alle Feeds leer, gilt nichts als entfallen. |
| 34 | Abruf der OParl-Listen: höchstens eine Seite darf fehlen (bisher 10 %). |
| 35 | Gremium aus dem Sitzungsnamen auch mit Vorsätzen und Zusätzen; Titelmuster der Einwohnerschaft ohne die Wortteile „einwohner“, „anregung“, „beschwerde“; `fetch-aufzeichnungen --alle` erreichbar; Schreibweise der TSV-Dateien im LIESMICH des Datenpakets beschrieben (nicht vereinheitlicht: die Protokolle der Archive werden fortgeschrieben). |
| 36 | `haushalt/`: fehlerhaft kodierter Anker ohne Abbruch; Zeitraum außerhalb des Bestands bleibt geordnet; Prozesslinie im Assistenten lässt zuerst Folgevorlagen, dann Erläuterungen, zuletzt frühere Schritte aus, die Entscheidung bleibt. |
| 37 | `baustellen.yml`: rot nur, wenn beide Quellen scheitern, sonst Hinweis; Lauf um 03:37 UTC vor dem täglichen Lauf der Seite. `quellen.yml`: Ausfall der Wahlquellen als Hinweis. Zeitlimits für alle Jobs. |
| 44 | Browser-Test mit aktiver Content-Security-Policy. |

Folgen, die sichtbar werden:

- Durch das engere Titelmuster (Nr. 35) gelten rund 73 Drucksachen und ihre verbundenen Vorlagen nicht mehr als Eingaben der Einwohnerschaft. Sie erhalten eine eigene Seite; Hausnummern in ihren Titeln werden nicht mehr ausgelassen, soweit sie nicht aus anderem Grund geschützt sind (Art der Vorlage, Bauordnung, Naturschutz, Fällgenehmigung, Verbindung zu einer Eingabe).
- Die Live-Prüfung meldet einen Fehler, wenn die Quellen länger als zwei Tage nicht abrufbar waren (Nr. 11).

Prüfung: Unit-Tests Python und JavaScript; Browser-Tests gegen die Vorschau; im Browser nachgestellt: schnelle Bedienfolge (Abstände 0 bis 800 ms ohne Fehler, Hervorhebung bei 40 Einträgen wie zuvor), Ausfall von `index.json` (503, kaputt, einmalig), Anker-Links in sieben Formen, Gebietsdatei mit HTTP 500, wiederholtes Nachladen, Zeitleiste in Beuel-Mitte und ohne Gebiet, Zeitraum außerhalb des Bestands.
