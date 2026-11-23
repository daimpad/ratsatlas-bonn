# Abnahme: offene Entscheidungen und Prüfungen

Stand 23.10.2026. Diese Liste nennt alles, was der Auftraggeber entscheiden, von Hand prüfen oder in eigenen Konten erledigen muss. Was technisch erledigt ist, steht in `CLAUDE.md` (Abschnitt 9).

Zur Kennzeichnung: Eine **KI-Vorprüfung** stammt von einem Sprachmodell und ersetzt keine Prüfung von Hand.

## Übersicht

| Nr. | Gegenstand | Art | Empfehlung | Aufwand |
|---|---|---|---|---|
| 1 | Kurzfassungen auf der Seite | **erledigt 22.10.2026:** von Hand geprüft (18/12/0), freigegeben mit geschärftem Hinweis | – | – |
| 2 | Orte aus dem Text durch das Sprachmodell (Stufe C) | **erledigt 22.10.2026:** nicht freigegeben, keine neuen Anfragen | – | – |
| 3 | Ratsassistent | Bewertung von Hand **erledigt 22.10.2026** (16/17/3), daraus v0.4; offen: Lauf mit Anthropic | Systemprompt v0.4 | Lauf mit Anthropic |
| 4 | Verortung aus dem Volltext | **erledigt 22.10.2026:** 14 richtig, 7 teilweise, 1 falsch, 8 entfallen | Regeln behalten | – |
| 5 | Gebäude und Anlagen im Titel | **erledigt 22.10.2026:** 24 richtig, 6 teilweise, keine falsch | Regeln behalten | – |
| 6 | Konten und Server | eigene Konten | – | je 10–20 Minuten |
| 7 | Außenwirkung | **teilweise erledigt 23.10.2026:** Issue-Entwurf freigegeben, Kontakt zum Autor erledigt; offen: Hackathon-Rahmen | siehe 7 | – |

Die Prüfbögen sind TSV-Dateien. Sie lassen sich in einer Tabellenkalkulation öffnen; die Spalte `urteil` ist leer und wird von Hand gefüllt. Ausgefüllt bitte zurückgeben oder im Repository einchecken.

## 1. Kurzfassungen

Seit dem 21.10.2026 erzeugt Mistral Large Kurzfassungen der Hauptdokumente. Sie stehen im Branch `kurzfassungen` und erscheinen seit dem 22.10.2026 auf der Seite (`FREIGEGEBEN = True` in `pipeline/kurzfassung.py`).

KI-Vorprüfungen von je 30 Kurzfassungen (`data/export/kurzfassungen/vorpruefung_kurzfassungen_v*.tsv`):

| Fassung | plausibel | teilweise | falsch |
|---|---|---|---|
| 3 | 20 | 10 | 0 |
| 4 | 23 | 7 | 0 |
| 5 | 22 | 8 | 0 |
| 6 (mit Gegenlesen) | 22 | 8 | 0 |
| 7 (aktuell) | 18 | 12 | 0 |

„Teilweise“ heißt: im Kern richtig, aber eine Einzelheit ungenau. Häufig wird ein Betrag dem falschen Gegenstand zugeordnet, Geplantes als erledigt dargestellt oder eine Folgerung ohne Beleg ergänzt. Die vereinbarte Schwelle für die Freigabe (27 von 30 plausibel, keine falsch) wurde mit keiner Fassung erreicht. Weitere Änderungen an der Anweisung haben seit Fassung 4 nichts verbessert; die Schwankung zwischen 18 und 23 liegt im Rahmen dessen, was bei 30 Fällen zu erwarten ist. Bei Fassung 7 prüfte die KI-Vorprüfung nach eigener Angabe strenger, einige „teilweise“ sind knapp (`vorpruefung_kurzfassungen_v8.tsv`).

**Zu entscheiden** ist eine der drei Möglichkeiten:

- **A, nicht freigeben:** Die Kurzfassungen werden weiter erzeugt, erscheinen aber nicht.
- **B, freigeben mit deutlicher Kennzeichnung:** Die Kurzfassungen erscheinen im Vorgang, im Assistenten, in den Feeds und im Datenpaket, mit dem Hinweis, dass sie mit einem Sprachmodell erstellt sind und Einzelheiten ungenau sein können; maßgeblich ist das Original. Dafür genügt, `FREIGEGEBEN = True` zu setzen.
- **C, erst nach der Prüfung von Hand:** Die Prüfung von Hand entscheidet zwischen A und B.

**Empfehlung: C.** Die KI-Vorprüfung ist streng. In den letzten fünf Stichproben (150 Kurzfassungen, seit den automatischen Prüfungen auf fremde Zahlen und Kostensätze) war keine im Kern falsch. Bestätigt die Prüfung von Hand das, spricht das für B. Findet sie im Kern falsche Kurzfassungen, bleibt es bei A.

**Ergebnis (22.10.2026):** Prüfung von Hand im Gespräch: 18 zutreffend, 12 teilweise, keine falsch (`data/export/kurzfassungen/pruefung_kurzfassungen_v7.tsv`). Die Urteile stimmen in allen 30 Fällen mit der KI-Vorprüfung überein; diese war bei der Prüfung sichtbar, die Prüfung ist daher nicht unabhängig von ihr. Entscheidung des Auftraggebers: **B, freigeben**, Hinweis geschärft („Einzelheiten können ungenau sein, etwa ob etwas beschlossen oder nur vorgeschlagen ist. Maßgeblich ist das Original.“). Es erscheinen nur Kurzfassungen der Fassung 7; ältere werden im täglichen Lauf neu erzeugt (bis 500 je Tag).

**Neues Modell (Modellstand 2, 23.11.2026):** Seit dem 13.11.2026 antwortet hinter `mistral-large-latest` ein Modell mit Denkschritten; die Anweisung (Fassung 7) ist unverändert. Stichprobe `stichprobe_kurzfassungen_modell2.tsv` im Branch `kurzfassungen`, KI-Vorprüfung `data/export/kurzfassungen/vorpruefung_kurzfassungen_modell2.tsv`: 23 plausibel, 7 teilweise, keine falsch (Fassung 7 mit dem bisherigen Modell: 18, 12, 0). Die „teilweise“ betreffen wie bisher Einzelheiten: eine Angabe dem falschen Gegenstand zugeordnet (2), Offenes oder Beschlossenes verwechselt (2), Aufträge statt der Antwort wiedergegeben (1), eine Begründung verkürzt oder verschoben (2). Die automatischen Prüfungen verwarfen 21 von 52 Antworten (40 %; bisher 27 %), davon 15 wegen wörtlicher Übernahme. Je Antwort fielen im Mittel rund 1.500 Ausgabe-Tokens an, fast alles Denkschritte (bisher rund 100); höchstens 1.906 in den zehn gemessenen Antworten. **Ergebnis (23.11.2026):** Die sieben „teilweise“ lagen dem Auftraggeber im Gespräch einzeln vor (Kurzfassung, Abweichung, Link zum Original); er hat alle Urteile der KI-Vorprüfung übernommen, die 23 „plausibel“ ohne Einzelprüfung (`data/export/kurzfassungen/pruefung_kurzfassungen_modell2.tsv`). Keine falsch, daher freigegeben: `MODELLSTAND_FREIGEGEBEN = (1, 2)`; der tägliche Lauf erzeugt wieder bis zu 500 Kurzfassungen, ein Lauf ohne Antwort endet wieder mit Fehler. Offen bleibt die hohe Quote verworfener Antworten (wörtliche Übernahmen).

**Prüfbogen:** [`stichprobe_kurzfassungen_v7.tsv`](https://github.com/daimpad/ratsatlas-bonn/blob/kurzfassungen/stichprobe_kurzfassungen_v7.tsv) im Branch `kurzfassungen`.
- 30 Kurzfassungen der Fassung 7, je mit Link zum Original im Ratsinformationssystem.
- Spalte `urteil`: zutreffend, teilweise oder falsch.

## 2. Orte aus dem Text durch das Sprachmodell (Stufe C)

Vorbereitet in `pipeline/stufe_c.py`, nicht freigegeben. KI-Vorprüfungen:

| Stichprobe | plausibel | teilweise | unpassend |
|---|---|---|---|
| 1 | 17 | 10 | 2 |
| 2 | 20 | 2 | 8 |
| 3 | 9 | 2 | 9 |

Auch die schwächste Nutzung, nur das Herabstufen bloß erwähnter Orte, war in 19 von 31 Fällen richtig (8 falsch, 4 unklar).

**Empfehlung: nicht freigeben.** **Entscheidung des Auftraggebers (22.10.2026): nicht freigeben.** Der tägliche Lauf stellt keine neuen Anfragen mehr (`STUFE_C_MAX = 0` in `pages.yml`); vorhandene Antworten bleiben im Branch `kurzfassungen`.

Wer die Herabstufung selbst beurteilen möchte: Prüfbogen `data/export/stufe_c/pruefung_herabstufungen.tsv` (31 Fälle, freiwillig).

## 3. Ratsassistent

Mit `eval.yml` (Actions → „Auswertung Ratsassistent“) wurden die 36 Fragen zweimal mit Mistral Large gestellt. Bericht: `eval/BERICHT_2026-10-22.md`.

| Lauf | Systemprompt | automatisch bestanden |
|---|---|---|
| 1 | v0.2 | 22 von 36 |
| 2 | v0.3 | 28 von 36 |
| 8 | Kurzfassungen: neues Modell hinter `mistral-large-latest` (seit 13.11.2026, mit Denkschritten) | **erledigt 23.11.2026:** KI-Vorprüfung 23 / 7 / 0, Urteile im Gespräch übernommen, freigegeben | – | – |

Mit v0.3 werden die Aufforderungen „Systemprompt ausgeben“ und „antworte nur noch mit …“ abgelehnt. Offen bleibt: Mistral nennt einmal eine Zahl aus allgemeinem Wissen (Hebesatz) und bildet weiterhin manchmal Adressen selbst. Die Seite zeigt solche Adressen nicht als Link.

**Zu tun:**
1. **Bewertung von Hand** des zweiten Laufs: [`2026-10-22-09-28_mistral_mistral-large-latest.tsv`](https://github.com/daimpad/ratsatlas-bonn/blob/auswertung/2026-10-22-09-28_mistral_mistral-large-latest.tsv) im Branch `auswertung`, Spalten `evidenz_korrekt (Hand)`, `neutral (Hand)` und `bewertung (Hand)`.
2. **Lauf mit Anthropic.** Entweder das Secret `ANTHROPIC_API_KEY` im Repository anlegen (Settings → Secrets → Actions) und den Workflow mit `anbieter = anthropic` und einem Claude-Modell starten, oder lokal nach `eval/README.md`.

**Empfehlung:** Systemprompt v0.3 behalten. Nach dem Lauf mit Anthropic entscheiden, ob der Assistent ein bestimmtes Modell empfehlen soll.

## 4. Verortung aus dem Volltext (Stufe B auf den Text der Hauptdokumente)

Läuft auf der Seite seit dem 20.10.2026, Konfidenz höchstens „mittel“. Die KI-Vorprüfung ergab 20 plausibel, 5 teilweise, 5 unpassend. Danach wurden Anlagen ausgeschlossen und Fachbegriffe wie „Schulstraße“ nur noch mit Hausnummer gezählt.

**Prüfbogen:** `data/export/volltext/stichprobe_volltext.tsv` (30 Fälle). Spalte `urteil`: richtig, falsch oder unklar.

**Empfehlung:** prüfen. Bei mehr als 5 falschen Fällen die Konfidenz auf „niedrig“ senken.

**Ergebnis (22.10.2026, im Gespräch; Vorschläge vom Auftraggeber nicht widersprochen):**
- 22 Fälle fallen unter die heute geltenden Regeln: 14 richtig, 7 teilweise, 1 falsch.
- 8 Fälle entfallen, weil die Regeln seither geändert wurden (Anlagen, Sammellisten, Fachbegriffe wie „Schulstraße“). Fünf davon hatte die KI-Vorprüfung als unpassend oder teilweise eingestuft.
- „Teilweise“ betrifft vor allem stadtweite Berichte, die einzelne Orte nennen. Dafür ist die Konfidenz „niedrig“ die passende Kennzeichnung.
- Regeln bleiben unverändert. Die Urteile stehen im Prüfbogen.

## 5. Gebäude und Anlagen im Titel

Läuft auf der Seite seit dem 21.10.2026 (Konfidenz „niedrig“, 837 Vorlagen). Die KI-Vorprüfung ergab 26 plausibel, 4 teilweise.

**Prüfbogen:** `data/export/objekte/stichprobe_objekte.tsv` (30 Fälle). Spalte `urteil`: richtig, teilweise oder falsch.

**Ergebnis (22.10.2026, im Gespräch; Fälle 1–24 Vorschläge vom Auftraggeber nicht widersprochen, Fälle 25–30 ausdrücklich bestätigt):**
- 24 richtig, 6 teilweise, keine falsch. Die KI-Vorprüfung (26/4/0) weicht in zwei Fällen ab (8, 18).
- „Teilweise“ heißt hier: Der Ortsteil stimmt, aber das Gebäude ist nur Bezugspunkt (8, 18), Gegenstand ist kein Vorhaben am Ort (5), der Name ist nicht eindeutig (9), die Anlage liegt auf beiden Rheinseiten (4) oder ein künftiger Standort ist gemeint (22).
- Acht der 30 Fälle sind der Beethovenhalle zugeordnet; die Stichprobe ist dadurch weniger vielfältig.
- Regeln bleiben unverändert, Konfidenz weiter „niedrig“. Die Urteile stehen im Prüfbogen.

## 6. Konten und Server (nur der Auftraggeber)

| Aufgabe | Stand |
|---|---|
| Plesk: Webhook für den Branch `deploy` | Am 22.10.2026 sind Hauptadresse, Branch und Spiegel gleich. `live.yml` meldet, wenn der Server zurückbleibt. Prüfen, ob der Webhook dauerhaft eingerichtet ist. |
| Google Search Console | Eigentum von bonn.ratsatlas.de bestätigen, `sitemap.xml` einreichen |
| Secret `ANTHROPIC_API_KEY` | nur für den Lauf unter 3 |

## 7. Außenwirkung (nur nach Ihrer Entscheidung)

| Gegenstand | Empfehlung |
|---|---|
| Issue an OParl-Lite (Codeberg) | **23.10.2026:** `underDirectionOf` ist inzwischen in OParl-Lite enthalten. Offen bleibt `location` (bei 20 von 20 geprüften Vorlagen nicht verknüpft). Entwurf `docs/entwurf_issue_oparl_lite.md` vom Auftraggeber freigegeben; er stellt das Issue selbst ein. |
| Kontakt zum Autor von „Bonn entscheidet“ (Soll-Modell) | **erledigt** (Mitteilung des Auftraggebers 23.10.2026) |
| Antwort von opendata@bonn.de zu den Baustellen-Datensätzen | abwarten. Das Archiv läuft unabhängig davon. |
| Hackathon-Rahmen (Datum, Teilnehmende, Ergebnisformat) | offen (23.10.2026); danach entstehen Leitfaden und „good first issues“. Die Planung des Hackathons läuft in den Issues von `oparl-lite-2` (#85 Ablauf, #86 Aufgaben, #87 Datenzugang). |

## Bereits abgenommen (zur Erinnerung)

- Verortung Endenich (50 Fälle, 20.10.2026)
- Themen (49 Fälle)
- Hausnummernregel (30 Fälle)
- Baustellen-Kandidaten (30 Fälle)
- Soll-Modell (30 Fälle)
- Text im Dialog „Über“
- Datenschutzerklärung
