# Ratstranskripte – Schritte 1 bis 3 (umgesetzt)

Stand 10.11.2026 · Entscheidungen des Auftraggebers vom 10.11.2026:
- Suche ohne Vorbefüllung;
- im Vorgang zwei kurze Zeilen, der Hinweis bleibt sichtbar;
- „setze alles um“.

## Daten (Schritt 1)

- `pipeline/aufzeichnungen.py`, Schritt `fetch-aufzeichnungen`: je Sitzung des Rates und des Hauptausschusses seit 2021 Video-Adresse, Dauer und Zahl der Abschnitte. Abgefragt wird über `meetingByIdRef` und `transcriptPassages`, mit einer Anfrage je Sekunde.
- **Zwischenspeicher:** `data/raw/aufzeichnungen.json` liegt im Repository und im Zwischenspeicher des Workflows. Abgefragt werden nur neue Sitzungen und solche ohne Aufzeichnung aus dem letzten Jahr; `--alle` fragt alles neu ab. Bei Fehlern bleibt der Stand, nach fünf Fehlern endet der Lauf.
- Übernommen werden nur YouTube-Adressen, kein Text der Transkripte.
- **Verknüpfung:**
  - Prozessschritte in Sitzungen mit Aufzeichnung tragen `aufzeichnung`, außer bei nichtöffentlichen Tagesordnungspunkten.
  - `zeit.json` nennt `video` je Sitzung.
  - `prozessarten.json` nennt je Gremium die Zahl der Aufzeichnungen und die jüngste.
- **Stand 10.11.2026:** 53 Sitzungen mit Aufzeichnung, 3.796 Beratungsschritte mit Link.

## Oberfläche (Schritt 2)

- **Vorgang auf der Karte:** unter jeder Beratung in einer Sitzung mit Aufzeichnung die Zeile „▶ Video der Sitzung · Transkript durchsuchen“ und darunter „automatisch erkannt, nicht amtlich“. Beide Links öffnen in einem neuen Tab, mit Text für Vorleseprogramme.
- **Seiten je Vorgang:** dieselben Links in der Beratungsfolge.
- **Reiter „Prozesse“, Gremium Rat:** „Aufzeichnungen: 53 Sitzungen seit 2021; jüngste vom …“ mit beiden Links.
- **Themenseiten:** Kasten „Im Rat gesagt“ mit zwei bis drei festen Suchwörtern je Thema (`Thema.transkript_begriffe`). Jedes Wort hatte am 10.11.2026 mindestens 12 Treffer. Ausgelassen wurden Wörter mit zu wenigen Treffern und „Sicherheit“ mit 1.311 Treffern, weil es zu allgemein ist.
- **Quellen, Begriffe und „Was ist neu?“:**
  - Quelle mit der Nennung „Datenquelle: OParl Bonn | Mika Baumeister“ und der Lizenz;
  - Begriff „Ratstranskript“ im Glossar;
  - Eintrag in „Was ist neu?“;
  - Quelle auf der Seite „So funktioniert der Ratsatlas“.

## Ratsassistent (Schritt 3)

- Neues Werkzeug `suche_aufzeichnungen`: Sitzungen mit Video und ein Link zur Suche, mit einem Stichwort nur im Link. `liste_sitzungen` und `hole_prozesslinie` nennen die `aufzeichnung`.
- Systemprompt v0.8: keine Aussagen über Inhalte von Redebeiträgen, keine Namen von Redenden, keine Zuordnung zu einer Stelle.

## Prüfung

- Tests: `tests/test_aufzeichnungen.py` mit nachgebildeter Schnittstelle. Geprüft werden Auswahl der Sitzungen, Zwischenspeicher, Fehler und Verweise. In `tests/js/tools.test.mjs` sind fremde Adressen ausgeschlossen und der Suchlink kodiert. Die Referenz der Kulturseite ist neu erzeugt; geändert sind nur der Kasten und der Sprunglink.
- Browser bei 1440 und 390 px (Vorgang 252458, Vorgangsseite, Gremium Rat, Themenseite Verkehr): Links vorhanden, axe ohne Verstöße, kein waagrechter Bildlauf, keine Skriptfehler.

## Nachtrag 10.11.2026: Stichwort im Vorgang, Kasten mit Symbol, Metaangaben eingeklappt

Entscheidungen des Auftraggebers 10.11.2026: Suche vorbefüllt nur, wenn geprüft; kleiner Kasten mit Symbol; „nicht amtlich“ bleibt sichtbar, der Hinweis mit Quelle und Lizenz steht im Akkordeon „Mehr über die Ratstranskripte erfahren“; Metaangaben aller statischen Seiten eingeklappt (Karte folgt in Schritt 2).

- Stichprobe `phase0/stichwort.py` → `phase0/stichwort.tsv` (30 Vorlagen ohne Einwohnerschaft): längstes Wort des Titels 21 von 30 mit Treffer in derselben Sitzung, Ortsname 3 von 4, beide 22 von 30. Bei etwa 6 Treffern ist das Wort allgemein (Einschätzung, Treffer nicht gelesen); diese Wörter stehen seither in der Liste der Verfahrenswörter (an der Stichprobe angepasst).
- Schritt `transkript-stichworte` (nach `build`, höchstens 8 Minuten je Lauf): je Beratung im Rat mit Aufzeichnung das Wort aus `aufzeichnungen.wort`; je Wort eine Suche (bis 400 Treffer), gespeichert nur Wort, Gesamtzahl und Sitzungen mit Treffer in `data/raw/aufzeichnungen_stichworte.json`. Ohne Treffer in derselben Sitzung bleibt die Suche leer. Vorlagen der Einwohnerschaft und ihre Folgevorlagen erhalten kein Stichwort.
- Prozessschritte tragen `transkript_q`; Vorgang auf der Karte und Seite je Vorgang zeigen „Im Transkript suchen: „…““.
- Kasten `aufz-karte` (Symbol Kamera, Schaltflächen) in `pipeline/aufzeichnungen.karte` und `site/app.js`; Themenseiten mit den festen Suchwörtern als Schaltflächen.
- Metaangaben in Akkordeons (`pipeline/akkordeon.py`): Themenseiten (Regel je Strang „Wie zugeordnet?“, Zuordnung, Quelle von Haushalt und Ausschuss, Bildbeschreibung, Grenzen, „Quellen und Methode“), Übersicht `thema/`, Seiten je Vorgang, Gebietsseiten, Haushalt (je Einwohner, Veränderung, Investitionen, Fundstellen der Ebenen), Begriffe, Einfache Sprache („Für Fachleute“), RSS (Quelle und Lizenz). Sichtbar bleiben kurze Markierungen „abgeleitet“ an einzelnen Werten.
- Schritt 2 (Karte): Metaangaben im Vorgang, bei Plänen und Baustellen, im Reiter „Prozesse“, in „Mitmachen“, bei Wegen und Terminen eingeklappt (`metaAcc` in `site/app.js`, Klasse `acc-meta`). Sichtbar bleiben die Rechtsgrundlage je Schritt (kurze Fundstelle am Schritt), der Hinweis vor der Suche im Text der Dokumente (Datenschutz) und die KI-Hinweise bei Kurzfassung und Assistent.

## Offen

- Lücken bei bonn.biz: Rat 2023 und 2024 nur zum Teil. Der tägliche Lauf fragt Sitzungen des letzten Jahres erneut ab; ältere nur mit `--alle`.
- Bezirksvertretungen, sobald bonn.biz sie aufnimmt: Erweiterung in `gremium_mit_aufzeichnung`.
