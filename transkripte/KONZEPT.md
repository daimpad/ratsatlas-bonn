# Ratstranskripte im Ratsatlas – UX-Konzept (Entwurf)

Stand 10.11.2026 · Entscheidungen des Auftraggebers vom 10.11.2026:
- nur Verweise, keine Texte;
- Orte: Vorgang, Sitzungen und Gremien, Themenseiten, Ratsassistent;
- nur auf Ebene der Sitzung;
- keine Namen sprechender Personen.

## 1. Ausgangslage

- **Quelle:** Ratstranskripte auf [bonn.biz](https://bonn.biz/ratstranskripte), erstellt von Mika Baumeister (CC BY-NC 4.0).
- **Entstehung:** automatische Spracherkennung (Whisper) aus den YouTube-Aufzeichnungen.
- **Umfang:** 162.550 Abschnitte, Rat und einzelne Sitzungen des Hauptausschusses, 2021 bis 2026; keine Bezirksvertretungen.
- **Verknüpfung:** Jede Aufnahme ist mit der Sitzung der Stadt verknüpft. Tagesordnungspunkte sind in einer Stichprobe von 500 Abschnitten nicht verknüpft.
- **Genauigkeit:** Fehlerquote geschätzt unter 2 %, Eigennamen am häufigsten verhört; maßgeblich sind Video und Niederschrift.

## 2. Grundsätze

1. **Verweisen, nicht übernehmen:** kein Transkripttext im Ratsatlas, im Datenpaket oder im Assistenten. Damit gibt es keine Mischung mit der NC-Lizenz und kein Zitat.
2. **Ebene der Sitzung:** „In dieser Sitzung beraten“, nie „an dieser Stelle gesagt“. Eine eigene Zuordnung zu Tagesordnungspunkten gibt es nicht.
3. **Keine Personen:** keine Namen, keine Zählungen nach Rednerinnen und Rednern, keine Auswertung von Redeanteilen.
4. **Kennzeichnung an jedem Verweis:** „automatisch erkannt, nicht amtlich“, Quelle bonn.biz (Mika Baumeister), maßgeblich Video und Niederschrift.
5. **Kein Einbetten:** Links öffnen in einem neuen Tab. Es gibt keinen YouTube-Player auf der Seite, daher keine Änderung der Datenschutzerklärung.

## 3. Daten (nur Angaben zur Aufzeichnung)

Datei `aufzeichnungen.json`, je Sitzung: Sitzung der Stadt (ID), Video-Adresse, Dauer, Abrufdatum. Erzeugt wird sie aus der GraphQL-Schnittstelle von OParl-Lite: die Sitzungsnummer der Stadt wird der Kennung in OParl-Lite zugeordnet, dann gibt es eine Abfrage je Sitzung. Das sind etwa 100 Sitzungen des Rates und des Hauptausschusses seit 2021. Abgerufen wird wöchentlich, gedrosselt. Fehlt die Datei, entfallen die Verweise ohne Fehler.

## 4. Elemente

| Ort | Element | Text (Vorschlag) |
|---|---|---|
| Vorgang, Prozesslinie | An Stationen in Sitzungen mit Aufzeichnung: Zeile unter der Station mit Symbol ▶ und Text | „Aufzeichnung dieser Sitzung: Video (YouTube) · Transkript durchsuchen (bonn.biz)“ |
| Vorgang | ~~Suchlink mit der Drucksachennummer~~ entfällt (Schritt 0: 0 von 20 Vorlagen mit Treffer); Vorbefüllung der Suche offen | – |
| Sitzungskalender, Reiter „Prozesse“ (Gremien) | vergangene Sitzungen mit Aufzeichnung: Symbol ▶ und „Aufzeichnung“ als Link | „Aufzeichnung (Video und Transkript)“ |
| Themenseiten | Kasten „Im Rat gesagt“ unter „Wer berät mit“: zwei bis drei feste Suchbegriffe je Strang (in der Themenbeschreibung festgelegt) | „Was im Rat zu ‚Nordbrücke‘ gesagt wurde – Suche in den Ratstranskripten“ |
| Ratsassistent | Werkzeug `suche_aufzeichnungen`: nennt Sitzungen mit Aufzeichnung und gibt Suchlinks; kein Inhalt. Neue Regel im Systemprompt: keine Aussagen über den Inhalt von Redebeiträgen | Antwortkarte „Aufzeichnung · Transkriptsuche“ |
| Quellen, „Über“, Begriffe | Quelle mit Lizenz; Begriff „Ratstranskript“ im Glossar | „Ratstranskripte: bonn.biz, Mika Baumeister (CC BY-NC 4.0); nur verlinkt“ |

## 5. Barrierefreiheit und Telefon

- Das Symbol steht nie allein; die Linktexte nennen Ziel und „neuer Tab“ (verborgen für Vorleseprogramme).
- Auf dem Telefon steht die Zeile unter der Station und bricht um; Tastatur und Fokus wie bei den übrigen Links des Vorgangs.

## 6. Grenzen (auf der Seite genannt)

- Nur Rat und Hauptausschuss; Bezirksvertretungen und Fachausschüsse fehlen in der Quelle.
- Aufzeichnungen gibt es für 50 von 66 Sitzungen des Rates seit 2021 (Lücken 2023 und 2024), im Hauptausschuss nur 2021 (Schritt 0, `phase0/BERICHT.md`).
- Die Transkripte sind automatisch erkannt; der Ratsatlas prüft sie nicht.

## 7. Schritte (je mit Freigabe)

0. **Prüfung:** Abdeckung messen (Sitzungen mit Aufzeichnung gegen Sitzungen des Rates und Hauptausschusses), Trefferquote der Suche nach Drucksachennummer an 20 Vorgängen, Hinweis an Mika Baumeister und bonn.biz.
1. **Daten:** `aufzeichnungen.json`, Audit, Tests.
2. **Oberfläche:** Vorgang, Sitzungen und Gremien, Themenseiten; Quellen und Glossar.
3. **Ratsassistent:** Werkzeug und Systemprompt.
