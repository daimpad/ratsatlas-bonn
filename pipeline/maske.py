"""Hausnummern in Titeln von Vorlagen aus der Einwohnerschaft ausblenden (Datenschutz, CLAUDE.md 5.2).

Gilt für Bürgeranträge, Anregungen und Beschwerden, Einwohnerfragen und Bürgerbriefe sowie alle Vorlagen, die mit
ihnen über- oder untergeordnet verbunden sind (chat.einwohner). Dieselbe Regel wie `masker()` in
site/chat/tools.js: eine Hausnummer hinter einem bekannten Straßennamen oder einer Straßen-Endung wird durch
OHNE_NR ersetzt. Entscheidung des Auftraggebers 24.10.2026: auf Seite, in Feeds, Suche und offenen Daten wie im
Assistenten; das Original bleibt über den Link ins Ratsinformationssystem erreichbar.
Verortung und Audit der Geokodierung arbeiten weiter mit dem vollen Titel aus der Datenbank (die Hausnummer
bestimmt den Ortsteil, angezeigt wird nur die Straße).
Erweitert am 26.10.2026 (Entscheidung des Auftraggebers): auch Vorlagen, die das Bauordnungsamt (63) oder eine Untere
Naturschutzbehörde (56-3, 67-6) federführend betreut (Bauanträge und Fällgenehmigungen auf Grundstücken), und ihre
verbundenen Vorlagen.
Ergänzt am 01.11.2026 (Lücke aus der Phase 0 „Verständlichkeit“: 27 Titel aus 15 Vorgängen): auch eine Nummer hinter
„Hausnummer(n)“, „Hausnr.“, „Haus-Nr.“ oder „Haus Nr.“ (ersetzt samt dem Wort) und hinter „Straße Nr.“.
Ergänzt nach der Prüfung vom November 2026 (pruefung/BERICHT_2026-11.md, Nr. 2, 4–6, 28; Freigabe des Auftraggebers
21.11.2026, Umsetzung wie empfohlen): Aufzählungen mit „oder“, „sowie“, „+“ und „&“, „Häuser(n) (Nr.) N“, „Str“ ohne
Punkt; Flurstücksnummern (FLUR); Fällgenehmigungen für private Bäume auch bei anderer Federführung (PRIVAT_TITEL);
dieselbe Regel für Fundstellen (evidence) und für alle TSV-Dateien unter data/export (bestand: auch einmalig gezogene
Prüfbögen)."""
import json
import re

from . import chat, config

OHNE_NR = "[Hausnummer ausgelassen]"
# Bauordnungsamt und Untere Naturschutzbehörden: Titel nennen oft private Baugrundstücke mit Hausnummer
AMT_PRIVAT = re.compile(r"^(?:63(?:\s|-)|56-3\b|67-6\b)")
# Fällgenehmigungen für private Bäume führt teils eine Bezirksverwaltungsstelle (z. B. 190302, 190305, 190306)
PRIVAT_TITEL = re.compile(r"fällgenehmigung", re.I)
_L = r"[^\W\d_]"   # Buchstabe (wie \p{L})
# wie NR und SUFFIX in site/chat/tools.js
NR = (rf"\d{{1,3}}(?:\s?[a-zA-Z](?!{_L}))?(?:\s*(?:-|–|bis|und|u\.|oder|sowie|/|,|\+|&)\s*\d{{1,3}}"
      rf"(?:\s?[a-zA-Z](?!{_L}))?)*(?!\d)")
SUFFIX = (rf"(?:{_L}|[.-])*(?:straße|strasse|str\.?|weg|platz|gasse|allee|ring|ufer|damm|pfad|chaussee|hof|markt|"
          rf"graben|berg|feld)(?!{_L})")


# „Hausnummer 82“, „Haus-Nr. 264“, „Haus Nr. 5“, „Hausnummern 36 bis 40“, „(neben Haus-Nr.) 68“ (wie WORT in
# site/chat/tools.js); eine schließende Klammer bleibt stehen
# „vor den Häusern Nr. 73 - 89“, „Häuser 12 und 14“ (240963)
WORT = re.compile(rf"\b(?:hausnummern?|hausnr\.?|haus-nr\.?|haus\s+nr\.?|häusern?(?:\s+nr\.?)?)\s*(\))?\s*{NR}", re.I)
# Rest einer Aufzählung hinter einer Auslassung („[Hausnummer ausgelassen] oder 12-14“): entsteht, wenn ein Titel
# nach älteren Regeln schon ausgeblendet war (eingecheckte Audits und Prüfbögen)
REST = re.compile(rf"({re.escape(OHNE_NR)})\s*(?:-|–|bis|und|u\.|oder|sowie|/|,|\+|&)\s*{NR}", re.I)
# Flurstücke bestimmen ein Grundstück wie eine Hausnummer: „Flur 12, Flurstück 345/6“, „Flurstücke 12 und 13“
OHNE_FLUR = "[Flurstück ausgelassen]"
_FS = r"\d{1,5}(?:\s*/\s*\d{1,4})?"
FLUR = re.compile(rf"\b(?:flur\s+\d{{1,3}}\s*,?\s*(?:und\s+)?)?flurstücke?n?s?\s*(?:nr\.?\s*)?{_FS}"
                  rf"(?:\s*(?:,|und|u\.|sowie|-|–|bis)\s*{_FS})*", re.I)


def _muster(strassen):
    names = sorted({s for s in strassen if s}, key=len, reverse=True)
    return re.compile(rf"((?:{'|'.join([*map(re.escape, names), SUFFIX])})\s+)(?:nr\.?\s*)?{NR}", re.I)


def privat(p):
    """Federführend Bauordnungsamt oder Untere Naturschutzbehörde (Name der Organisationseinheit oder Amtsbezeichnung;
    Datenbank: amt_name, Export: responsibility)."""
    namen = [p.get("amt_name"), p.get("amt")] + [r.get("name") for r in p.get("responsibility") or []
                                                 if r.get("kind") == "federfuehrend"]
    return any(AMT_PRIVAT.match(n or "") for n in namen) or bool(PRIVAT_TITEL.search(p.get("name") or ""))


class Maske:
    """maske(titel, drucksache) → Titel ohne Hausnummer, wenn die Drucksache zur Einwohnerschaft gehört."""

    def __init__(self, refs, strassen=None):
        self.refs = set(refs)
        if strassen is None:
            strassen = json.loads(config.STRASSEN.read_text())["streets"] if config.STRASSEN.exists() else []
        self.rx = _muster(strassen)
        self._offen = {}   # Text → Befund: Titel wiederholen sich über Gebietsdateien, Audits und Folgevorlagen

    def _betroffen(self, titel, ref):
        # ohne Ziffer keine Hausnummer: spart die teure Regex bei den meisten Titeln (gleiche Ergebnisse)
        return bool(titel) and ref in self.refs and any(c.isdigit() for c in titel)

    def __call__(self, titel, ref):
        if not self._betroffen(titel, ref):
            return titel
        titel = WORT.sub(lambda m: OHNE_NR + (m.group(1) or ""), self.rx.sub(lambda m: m.group(1) + OHNE_NR, titel))
        return FLUR.sub(OHNE_FLUR, REST.sub(r"\1", titel))

    def offen(self, titel, ref):
        """Bleibt nach dem Ausblenden eine Hausnummer oder ein Flurstück stehen? (Prüfung in check.py)"""
        if not self._betroffen(titel, ref):
            return False
        if titel not in self._offen:
            self._offen[titel] = bool(self.rx.search(titel) or WORT.search(titel) or REST.search(titel)
                                      or FLUR.search(titel))
        return self._offen[titel]

    def moeglich(self, titel, ref):
        """Gröbere, von den Regeln unabhängige Gegenprobe (Warnliste in check.py): steht in einem ausgeblendeten Titel
        kurz hinter einem Straßenwort oder einer Auslassung noch eine ein- bis dreistellige Zahl, getrennt nur durch
        Bindewörter und Satzzeichen (GROB)? Die Regeln selbst können ihre Lücken nicht finden (Prüfung November 2026,
        Nr. 5)."""
        return self._betroffen(titel, ref) and bool(GROB.search(titel))


class _Alle:
    """Jede Drucksache gilt als geschützt."""

    def __contains__(self, ref):
        return True


def fuer_alle(strassen=None):
    """Maske für Prüfbögen, bei denen die geschützten Drucksachen nicht bekannt sind (Branch `kurzfassungen`, ohne
    Datenbank): Sie blendet Hausnummern und Flurstücke in jedem Titel aus. Ein Prüfbogen braucht die Nummer nicht,
    der Link führt zum Original."""
    m = Maske((), strassen)
    m.refs = _Alle()
    return m


# Gegenprobe: Zahl kurz hinter einem Straßenwort oder einer Auslassung, dazwischen nur Bindewörter und Satzzeichen
# („… oder 12“, „in Höhe 7“, „vor den Häusern 3“); Ordnungszahlen, Dezimalzahlen und Zahlen mit Einheit zählen nicht
_BINDE = r"(?:und|oder|sowie|bis|u\.|nr\.?|no\.?|vor|neben|gegenüber|höhe|haus|häusern?|den|der|dem|in|von|ab|zwischen)"
GROB = re.compile(
    rf"(?:{SUFFIX}|\[Hausnummer ausgelassen\])[\s,;/+&()–-]*(?:{_BINDE}\b[\s,;/+&().–-]*){{0,4}}"
    r"(?<![\d§])\d{1,3}\s?[a-z]?\b(?![\d/.]|,\d|\s?(?:%|Prozent|Euro|€|EUR|Uhr|m\b|qm|m²|km|cm|Jahre))",
    re.I)


def _text(zelle):
    """Zellen, in denen eine Hausnummer stehen kann: keine Adressen, Daten oder Kennungen (spart die teure Regex)."""
    return len(zelle) > 7 and not zelle.startswith(("http://", "https://"))


def tsv_offen(path, m):
    """Drucksachen in einer TSV-Datei, in deren Zeile noch eine Hausnummer oder ein Flurstück steht."""
    offen = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            zellen = line.rstrip("\n").split("\t")
            ref = next((c for c in zellen if c in m.refs), None)
            if ref and any(m.offen(c, ref) for c in zellen if _text(c)):
                offen.add(ref)
    return sorted(offen)


def tsv_nachziehen(path, m):
    """Hausnummern und Flurstücke in den Zeilen geschützter Drucksachen einer TSV-Datei ausblenden (Drucksache als
    eigene Zelle, gleich in welcher Spalte). Schreibt nur, wenn sich etwas ändert; liefert die Zahl geänderter Zeilen."""
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.readlines()
    n = 0
    for i, line in enumerate(lines):
        ende = line[len(line.rstrip("\r\n")):]
        zellen = line[:len(line) - len(ende)].split("\t")   # je Zelle: kein Treffer über Spaltengrenzen
        ref = next((c for c in zellen if c in m.refs), None)
        if ref and (neu := "\t".join(m(c, ref) if _text(c) else c for c in zellen) + ende) != line:
            lines[i] = neu
            n += 1
    if n:
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        tmp.replace(path)
    return n


def bestand(m, base=None, ohne=("bonn",)):
    """Alle TSV-Dateien unter data/export nachziehen (ohne den täglich erzeugten Ordner bonn/, den check.py prüft):
    auch einmalig gezogene Prüfbögen und Audits tragen so keine Hausnummer geschützter Drucksachen. Die Urteile und
    Anmerkungen der Prüfung von Hand bleiben unberührt, nur der Titel verliert die Nummer."""
    base = base or config.EXPORT
    geaendert = {}
    for path in sorted(base.rglob("*.tsv")):
        if path.relative_to(base).parts[0] in ohne:
            continue
        if n := tsv_nachziehen(path, m):
            geaendert[str(path.relative_to(base))] = n
    return geaendert


def vorlagen(db):
    """Alle Vorlagen der Datenbank mit Art, Titel (ungekürzt), federführender Stelle und Beziehungen, wie
    chat.einwohner sie erwartet."""
    spalten = {r[1] for r in db.execute("PRAGMA table_info(paper)")}
    amt = ("(SELECT name FROM organization o WHERE o.id = paper.under_direction_of)"
           if "under_direction_of" in spalten else "NULL")
    papers = {r[0]: {"reference": r[1], "paper_type": r[2], "name": r[3], "amt_name": r[4], "superordinated": [],
                     "subordinated": []}
              for r in db.execute(f"SELECT id, reference, paper_type, name, {amt} FROM paper")}
    has_rel = db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'paper_relation'").fetchone()
    for parent, child in db.execute("SELECT parent_id, child_id FROM paper_relation") if has_rel else ():
        if parent in papers and child in papers:
            papers[child]["superordinated"].append({"reference": papers[parent]["reference"]})
            papers[parent]["subordinated"].append({"reference": papers[child]["reference"]})
    return list(papers.values())


def aus_db(db, strassen=None):
    """Maske für alle Vorlagen der Datenbank (Einwohnerschaft, Bauordnung, Naturschutz und verbundene Vorlagen)."""
    return Maske(chat.einwohner(vorlagen(db), auch=privat), strassen)
