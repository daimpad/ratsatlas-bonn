"""Kurzfassungen der Vorlagen in einfacher Sprache (Sprachmodell Mistral, gekennzeichnet).

Rahmen laut Antwort der Stadt Bonn vom 19.10.2026: Verarbeitung der Texte zulässig, keine Zitate und keine Auszüge;
selbst formulierte, gekennzeichnete Kurzfassungen zulässig. Deshalb:
- Eingabe: Titel und bereinigter Hauptteil des Hauptdokuments (volltext.clean), gekürzt auf MAX_ZEICHEN.
- Prüfung jeder Kurzfassung: verworfen wird sie, wenn sie eine Folge von mehr als UEBERNAHME_WOERTER Wörtern wörtlich
  aus dem Text enthält (Auszug) oder eine Hausnummer nennt (Datenschutz).
- Ablage: kurzfassungen.jsonl im Branch `kurzfassungen` (Verzeichnis KURZFASSUNGEN), je Datei-Hash (`textSha256`)
  einmal erzeugt; der Workflow schreibt den Branch zurück. Auf der Seite erscheinen die Kurzfassungen erst, wenn
  FREIGEGEBEN gesetzt ist (nach Prüfung einer Stichprobe von Hand).
Schlüssel: Umgebungsvariable MISTRAL_API_KEY (Secret im Workflow); ohne Schlüssel wird nichts erzeugt.
"""
import csv
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import config, maske, sprachmodell, volltext

API = "https://api.mistral.ai/v1/chat/completions"
# Fassung 2 (21.10.2026): großes Modell und genauere Anweisung nach der KI-Vorprüfung der ersten Stichprobe
# (18 plausibel, 8 teilweise, 2 falsch, 2 unklar; Fehler: falscher Akteur, Vermutungen, falsche Orte, vertauschter
# Kostenträger; data/export/kurzfassungen/vorpruefung_kurzfassungen_v1.tsv)
MODELL = os.environ.get("KURZFASSUNG_MODELL", "mistral-large-latest")
FASSUNG = 7   # 7: Anweisung der Fassung 5 ohne Gegenlesen (Vorprüfung v7 der Fassung 6: 22/8/0, keine Verbesserung,
#               doppelte Kosten, mehr wörtliche Übernahmen); 6: zweiter Aufruf liest gegen (GEGENLESEN_AKTIV);
# 3: ohne Überschrift, Absender im ersten Satz, Kosten nur laut Text (Vorprüfung v2); 4: Fragen von
#               Anfragen nur wie gestellt, Gremium und Fraktion nur laut Text (Vorprüfung v4: 20/10/0); 5: Rolle im
#               Verfahren (Kenntnisnahme), keine erschlossenen Fragen oder Ursachen, Ebene einer Zahl (Vorprüfung v5: 23/7/0)
GEGENLESEN_AKTIV = False   # Fassung 6: kein messbarer Gewinn, daher abgeschaltet; die Funktion bleibt für Versuche
MAX_JE_LAUF = int(os.environ.get("KURZFASSUNG_MAX", "50"))   # zuerst klein, um Kosten und Güte zu messen
MAX_ZEICHEN = 12000
UEBERNAHME_WOERTER = 6
MAX_VERSUCHE = 3   # gescheiterte Anfragen werden in späteren Läufen wiederholt, dann übersprungen
# Fehler, die das Konto betreffen (Schlüssel, Zahlung, Rechte, Kontingent), und eine Serie gescheiterter Anfragen
# beenden den Lauf, ohne die Dokumente als gescheitert zu zählen (Code-Prüfung 24.10.2026: ein Ausfall von drei Tagen
# sperrte sonst die betroffenen Dokumente dauerhaft, und jede Anfrage wartete erst die Wiederholungen ab)
KONTO_FEHLER = (401, 402, 403, 429)
SERIE = 5
FREIGEGEBEN = True   # Prüfung von Hand der Stichprobe v7 (22.10.2026): 18 zutreffend, 12 teilweise, keine falsch;
#                       Freigabe durch den Auftraggeber mit geschärftem Hinweis
# Stand des Modells hinter dem Namen MODELL. 1: Mistral Large bis zum 12.11.2026; mit ihm ist die Stichprobe v7 von
# Hand geprüft, für ihn gilt die Freigabe. 2: seit dem 13.11.2026 antwortet hinter demselben Namen ein Modell mit
# Denkschritten (Antwort als Liste von Teilen; bei 220 Tokens kam nur der Denkteil). Entscheidung des Auftraggebers
# 22.11.2026: Anfrage anpassen, 30 Kurzfassungen als Stichprobe mit KI-Vorprüfung, auf die Seite erst nach seiner
# Prüfung. Bis dahin entstehen nur die Kurzfassungen der Stichprobe, und ein Lauf ohne Antwort endet mit einem Hinweis
# statt mit einem Fehler. Freigabe: den Stand in MODELLSTAND_FREIGEGEBEN aufnehmen.
MODELLSTAND = 2
# Stand 2 freigegeben am 23.11.2026: Stichprobe mit KI-Vorprüfung 23 plausibel, 7 teilweise, keine falsch; die sieben
# „teilweise“ lagen dem Auftraggeber einzeln vor, er hat alle Urteile übernommen (pruefung_kurzfassungen_modell2.tsv)
MODELLSTAND_FREIGEGEBEN = (1, 2)
STICHPROBE_MODELL = 30
# Denkschritte zählen zur Längengrenze der Antwort; die Kurzfassung selbst bleibt bei höchstens 60 Wörtern (Anweisung).
# Die Grenze ist eine Obergrenze, bezahlt werden die tatsächlich erzeugten Tokens; der Lauf nennt Mittel und Höchstwert
# je Antwort. 3.000 waren dem Auftraggeber zu knapp (22.11.2026), 16.000 lassen auch langen Denkschritten Raum. Der
# Aufwand für Denkschritte wird klein gehalten; nimmt der Anbieter die Angabe nicht an (HTTP 400 oder 422), wird ohne
# sie angefragt.
MAX_TOKENS = 16000
ZEITLIMIT = 300    # Sekunden je Anfrage; eine Anfrage, die so lange braucht, wird nicht wiederholt
DENKAUFWAND = "low"
MAX_WOERTER = 90   # ab Modellstand 2: die frühere Grenze von 220 Tokens begrenzte auch die Länge der Kurzfassung
_ohne_denkaufwand = False
# Ausweichweg (Entscheidungen des Auftraggebers 22.11.2026): Liefert ein Lauf mit Mistral keine einzige Antwort, erzeugt
# derselbe Lauf die Stichprobe mit Claude Sonnet 5.5 (Modellstand 3, Secret ANTHROPIC_API_KEY). Antwortet Mistral,
# bleibt Claude unbenutzt. Auch dieser Stand erscheint erst nach Prüfung der Stichprobe und Freigabe. Ein Ausweichmodell
# bei abgelehnten Anfragen ist bewusst nicht eingeschaltet: Die Freigabe gilt je Modell, eine Kurzfassung eines dritten
# Modells unter diesem Namen wäre nicht geprüft; eine abgelehnte Anfrage gilt als gescheitert.
AUSWEICHSTAND = 3
MODELL_CLAUDE = os.environ.get("KURZFASSUNG_MODELL_CLAUDE", "claude-sonnet-5-5")
AUFWAND_CLAUDE = "medium"   # Denkaufwand; bei Claude Sonnet 5.5 ausdrücklich zu setzen (Voreinstellung „high“)
_claude = None
VERZEICHNIS = Path(os.environ.get("KURZFASSUNGEN", config.ROOT / "_kurzfassungen"))
# Absender und Gremien, die in einer Kurzfassung nur stehen dürfen, wenn Titel oder Text sie nennen (KI-Vorprüfung v4:
# „Die Grünen beantragen“ und „dem Rat vorgelegt“ ohne Beleg)
PARTEIEN = {"CDU": r"\bCDU\b", "SPD": r"\bSPD\b", "Grüne": r"\bGrüne|\bGRÜNE|Bündnis 90", "FDP": r"\bFDP\b",
            "Linke": r"\bLinke|\bLINKE", "Volt": r"\bVolt\b", "BBB": r"\bBBB\b|Bürger Bund", "AfD": r"\bAfD\b"}
GREMIEN = {"Rat": r"\b(Rat|Rates|Rats\w*|Stadtrat\w*)\b", "Bezirksvertretung": r"Bezirksvertretung",
           "Ausschuss": r"[Aa]usschuss"}
# Hausnummer hinter einer Straßen-Endung („Hauptstraße 12a“, „Bornheimer Str 5“, „Am Burggraben 3“) oder hinter einem
# Straßennamen aus dem Verzeichnis („Markt 2“); Code-Prüfung 23.10.2026: Buchstabenzusätze und „Str“ ohne Punkt fehlten
_NR = r"\s+(?:Nr\.\s*)?\d{1,3}(?:\s?[a-zA-Z])?\b(?!\s?(?:%|Prozent|Euro|€|Jahre|Meter|m\b|km|[.,]\d))"
HAUSNUMMER = re.compile(r"(?:straße|strasse|str\.?|weg|platz|allee|gasse|ring|ufer|damm|pfad|graben|wall|chaussee|"
                        r"promenade)" + _NR, re.I)
NACH_NAME = re.compile(r"((?:\S+\s+){0,3}\S+?)" + _NR)
_STRASSEN = None


def strassen():
    """Namen der Straßen in Bonn (OpenStreetMap, ODbL), klein geschrieben."""
    global _STRASSEN
    if _STRASSEN is None:
        d = json.loads(config.STRASSEN.read_text()) if config.STRASSEN.exists() else {}
        _STRASSEN = {n.lower() for n in d.get("streets", {})}
    return _STRASSEN


def hausnummer(kurz):
    """True, wenn die Kurzfassung eine Hausnummer nennt (Datenschutz, CLAUDE.md 5.2). Auch „Hausnummer(n) N“,
    „vor den Häusern N“ und Flurstücke wie in maske.py (Prüfung November 2026, Nr. 1: 57 veröffentlichte Kurzfassungen
    mit „zwischen den Hausnummern N und M“ blieben unerkannt)."""
    if HAUSNUMMER.search(kurz or "") or maske.WORT.search(kurz or "") or maske.FLUR.search(kurz or ""):
        return True
    namen = strassen()
    for m in NACH_NAME.finditer(kurz or ""):
        teile = m.group(1).split()
        if teile[-1][-1:] in ",;:":   # „am Holzlarer Weg, 500 Euro …“: Aufzählung, keine Hausnummer
            continue
        if any(" ".join(teile[i:]).lower().strip(",;:()") in namen for i in range(len(teile))):
            return True
    return False

ANWEISUNG = """Du schreibst Kurzfassungen von Vorlagen des Rates der Stadt Bonn für Bürgerinnen und Bürger ohne
Verwaltungswissen. Schreibe zwei bis drei kurze Sätze in einfacher Sprache, höchstens 60 Wörter: worum es geht, was
beantragt, vorgeschlagen, beschlossen oder mitgeteilt wird und, wenn genannt, welcher Ort betroffen ist.
- Nenne den richtigen Absender und die Art der Vorlage: Ein Antrag einer Fraktion ist ein Vorschlag, kein Beschluss;
  eine Beschlussvorlage ist ein Vorschlag der Verwaltung; eine Stellungnahme gibt die Sicht der Verwaltung oder einer
  anderen Stelle wieder; eine Mitteilung informiert nur. Schreibe nicht „die Stadt plant“ oder „der Rat will“, wenn
  das nicht im Text steht.
- Gib Bedingungen wieder („nur wenn der Antrag angenommen wird“) und sage, wer Kosten trägt, nur so, wie es im Text steht.
- Nenne nur Orte, Zahlen und Daten, die im Text stehen; nenne keine Stadtbezirke oder Ortsteile, die der Text nicht nennt.
- Vermute nichts und ergänze nichts („vermutlich“, „oder“-Aufzählungen möglicher Inhalte). Steht wenig im Text, schreibe
  kurz, was dort steht.
- Wer Kosten trägt, schreibst du nur, wenn es im Text ausdrücklich steht.
- Bei einer Anfrage gibst du nur die Fragen wieder, die gestellt werden; füge keine eigenen Fragen hinzu.
- Nenne eine Fraktion oder ein Gremium (Rat, Ausschuss, Bezirksvertretung) nur, wenn Titel oder Text sie nennen.
  Steht dort „Koalition“, schreibe „die Koalition“ und zähle keine Parteien auf.
- Gib die Rolle im Verfahren genau wieder: Soll ein Gremium etwas nur zur Kenntnis nehmen, schreibe das; schreibe dann
  nicht, dass es etwas beschließen oder ablehnen soll. Was ein Antrag fordert, ist eine Forderung, keine Tatsache.
- Gib Fragen so wieder, wie sie gestellt sind; erschließe sie nicht aus der Antwort. Nenne keine Gründe oder
  Ursachen, die der Text nicht nennt.
- Gilt eine Zahl für eine bestimmte Ebene (ganze Stadt, Stadtbezirk, Verwaltung, Beschäftigte), nenne diese Ebene.
Beginne direkt mit dem ersten Satz und nenne den Absender darin („Die Verwaltung schlägt vor …“, „Die CDU-Fraktion
beantragt …“); schreibe keine Überschrift und keine Angaben wie „Absender:“ oder „Art der Vorlage:“.
Formuliere vollständig mit eigenen Worten; übernimm keine Sätze und keine längeren Wortfolgen aus dem Text. Nenne keine
Namen von Privatpersonen und keine Hausnummern. Antworte nur mit der Kurzfassung."""


GEGENLESEN = """Du prüfst eine Kurzfassung einer Vorlage des Rates der Stadt Bonn gegen den Text der Vorlage und
berichtigst sie. Prüfe Satz für Satz:
- Absender und Art der Vorlage (Antrag, Anfrage, Stellungnahme, Mitteilung, Beschlussvorlage) wie im Titel oder Text.
- Rolle im Verfahren: Was vorgeschlagen, beantragt, angekündigt oder nur zur Kenntnis gegeben wird, darf nicht als
  beschlossen, zugesagt oder bereits vorliegend erscheinen.
- Zahlen: Steht jede Zahl so im Text, und gilt sie für die genannte Ebene (Stadt, Bezirk, Verwaltung, Personen)?
- Fragen einer Anfrage: nur die gestellten Fragen, keine hinzugefügten.
- Nichts, was der Text nicht sagt: keine Gründe, Folgerungen, Gremien oder Fraktionen ohne Beleg.
Streiche oder berichtige, was nicht stimmt; ergänze nichts Neues. Behalte einfache Sprache, zwei bis drei kurze Sätze,
höchstens 60 Wörter, keine längeren Wortfolgen aus dem Text. Antworte nur mit der berichtigten Kurzfassung (oder der
unveränderten, wenn alles stimmt), ohne Kommentar."""


def _woerter(text):
    return re.findall(r"\w+", (text or "").lower())


def _folgen(woerter, n):
    return {tuple(woerter[i:i + n]) for i in range(len(woerter) - n + 1)}


_NAMEN = None


def namen():
    """Namen von Gremien und Ämtern (OParl, CC0): lange Eigennamen, kein Text der Dokumente."""
    global _NAMEN
    if _NAMEN is None:
        orgs = json.loads(config.ORGANIZATIONS.read_text()) if config.ORGANIZATIONS.exists() else []
        _NAMEN = [o.get("name") or "" for o in orgs]
    return _NAMEN


def uebernahme(kurz, text, n=UEBERNAHME_WOERTER + 1, erlaubt=()):
    """Erste übernommene Wortfolge mit mehr als UEBERNAHME_WOERTER Wörtern aus dem Text (sonst None). Wörter, mit denen
    die Kurzfassung eine Angabe aus `erlaubt` wiederholt (Titel der Vorlage, Namen von Gremien; ab drei Wörtern),
    zählen nicht: Sie sind öffentliche Angaben aus der OParl-API, kein Auszug aus dem Dokument. Gezählt wird über die
    ganze zusammenhängende Übernahme (Code-Prüfung 24.10.2026: bisher galt jedes Fenster, das eine erlaubte Angabe
    berührte, als frei, so dass sechs Wörter davor und danach unbemerkt blieben)."""
    folgen = _folgen(_woerter(text), n)
    k = _woerter(kurz)
    frei = set()
    for e in erlaubt:
        w = _woerter(e)
        if len(w) >= 3:
            frei |= {j for i in range(len(k) - len(w) + 1) if k[i:i + len(w)] == w for j in range(i, i + len(w))}
    gedeckt = [False] * len(k)   # Wörter, die in einer Folge aus n Wörtern des Textes liegen
    for i in range(len(k) - n + 1):
        if tuple(k[i:i + n]) in folgen:
            gedeckt[i:i + n] = [True] * n
    i = 0
    while i < len(k):
        if not gedeckt[i]:
            i += 1
            continue
        j = i
        while j < len(k) and gedeckt[j]:
            j += 1
        if sum(1 for x in range(i, j) if x not in frei) > UEBERNAHME_WOERTER:
            return " ".join(k[i:j])
        i = j
    return None


KOPFZEILE = re.compile(r"^(Absender|Art der Vorlage)\s*:|:\s*$|^[^.!?]{0,80}$")


def glaetten(kurz):
    """Markdown-Auszeichnungen (*kursiv*, **fett**, `Code`) und vorangestellte Überschriften („Stellungnahme der
    Verwaltung“, „Absender: …“) entfernen; Zeilen werden zu einem Absatz: die Seite zeigt reinen Text."""
    zeilen = [z.strip() for z in re.sub(r"(\*{1,2}|_{2}|`)(.+?)\1", r"\2", kurz or "").split("\n")]
    while len(zeilen) > 1 and (not zeilen[0] or KOPFZEILE.search(zeilen[0])):
        zeilen = zeilen[1:]
    return " ".join(z for z in zeilen if z).strip()


# Prüfungen nach der KI-Vorprüfung von Fassung 3 (21.10.2026): Sätze zum Kostenträger, die der Text nicht stützt,
# werden entfernt; Zahlen, die nicht im Text stehen (falsch errechnete Summen), führen zum Verwerfen
KOSTEN_SATZ = re.compile(r"\bKosten\b.*\b(trägt|tragen|übernimmt|übernehmen|zahlt|zahlen)\b|"
                         r"\b(trägt|tragen|übernimmt|übernehmen|zahlt|zahlen)\b.*\bKosten\b")
KOSTEN_IM_TEXT = re.compile(r"Kostenträger|Kostenübernahme|Übernahme der[^.]{0,60}Kosten|"
                            r"(trägt|tragen|übernimmt|übernehmen)[^.]{0,40}Kosten|Kosten[^.]{0,40}(trägt|tragen|übernimmt|übernehmen)")
ZAHL = re.compile(r"\d+(?:[.,]\d+)*")


def ohne_kostensatz(kurz, text):
    """Sätze zum Kostenträger entfernen, wenn der Text keinen Kostenträger nennt."""
    if KOSTEN_IM_TEXT.search(text or ""):
        return kurz
    saetze = re.split(r"(?<=[.!?])\s+", kurz or "")
    return " ".join(s for s in saetze if not KOSTEN_SATZ.search(s)).strip()


def fremde_zahl(kurz, text):
    """Erste Zahl (ab zwei Ziffern) der Kurzfassung, die so nicht im Text steht, sonst None."""
    tausender = lambda t: re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", t)
    quelle = set()
    for z in ZAHL.findall(text or ""):   # auch Teile von Datumsangaben („31.12.2024“ → „2024“)
        quelle |= {tausender(z), *re.split(r"[.,]", z)}
    for z in ZAHL.findall(kurz or ""):
        if len(re.sub(r"\D", "", z)) >= 2 and tausender(z) not in quelle:
            return z
    return None


def fremder_akteur(kurz, quelle):
    """Fraktion oder Gremium, das die Kurzfassung nennt, Titel und Text aber nicht (sonst None)."""
    for name, rx in {**PARTEIEN, **GREMIEN}.items():
        if re.search(rx, kurz or "") and not re.search(rx, quelle or ""):
            return name
    return None


def pruefe(kurz, text, titel=""):
    """Grund, aus dem eine Kurzfassung verworfen wird, oder None."""
    if not kurz:
        return "zu kurz"
    if uebernahme(kurz, text, erlaubt=[titel, *namen()]):
        return f"wörtliche Übernahme von mehr als {UEBERNAHME_WOERTER} Wörtern"
    if hausnummer(kurz):
        return "Hausnummer genannt"
    if len(_woerter(kurz)) < 8:
        return "zu kurz"
    z = fremde_zahl(kurz, f"{titel} {text}")   # Zahlen im Titel („Controllingbericht 2023“) zählen mit
    if z:
        return f"Zahl nicht im Text: {z}"
    a = fremder_akteur(kurz, f"{titel} {text}")
    if a:
        return f"nicht in Titel oder Text: {a}"
    return None


def _anfrage(titel, text, schluessel, tries=4, system=ANWEISUNG, zusatz=""):
    global _ohne_denkaufwand
    koerper = {"model": MODELL, "temperature": 0.2, "max_tokens": MAX_TOKENS, "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Titel: {titel}\n\nText der Vorlage:\n{text}{zusatz}"}]}
    for i in range(tries):
        body = koerper if _ohne_denkaufwand else {**koerper, "reasoning_effort": DENKAUFWAND}
        req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {schluessel}"})
        try:
            with urllib.request.urlopen(req, timeout=ZEITLIMIT) as r:
                d = json.load(r)
            return sprachmodell.antworttext(d), d.get("usage") or {}
        except (sprachmodell.AntwortFormat, TimeoutError):   # ohne Text oder zu langsam: Wiederholen hilft nicht
            raise
        except urllib.error.HTTPError as e:
            if e.code in (400, 422) and not _ohne_denkaufwand:   # Angabe zum Denkaufwand nicht angenommen
                _ohne_denkaufwand = True
                print(f"  Anbieter nimmt reasoning_effort nicht an (HTTP {e.code}); weiter ohne diese Angabe", flush=True)
                continue
            if e.code in KONTO_FEHLER[:3] or i == tries - 1:   # Schlüssel, Zahlung, Rechte: Wiederholen hilft nicht
                raise
            time.sleep(2 ** (i + 2))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** (i + 2))


def _anfrage_claude(titel, text, schluessel, system=ANWEISUNG):
    """Kurzfassung mit Claude über das SDK von Anthropic (Ausweichweg). Der Schlüssel kommt aus ANTHROPIC_API_KEY;
    das SDK wiederholt Netzfehler, 429 und 5xx selbst. Denkschritte gehören nicht zur Antwort: gelesen werden nur die
    Textteile. Eine abgelehnte, leere oder an der Längengrenze abgeschnittene Antwort gilt als gescheitert."""
    global _claude
    if _claude is None:
        import anthropic   # nur für diesen Weg nötig
        _claude = anthropic.Anthropic(timeout=float(ZEITLIMIT), max_retries=2)
    r = _claude.messages.create(
        model=MODELL_CLAUDE, max_tokens=MAX_TOKENS, system=system, output_config={"effort": AUFWAND_CLAUDE},
        messages=[{"role": "user", "content": f"Titel: {titel}\n\nText der Vorlage:\n{text}"}])
    kurz = "".join(b.text for b in r.content if b.type == "text").strip()
    if r.stop_reason != "end_turn" or not kurz:
        raise sprachmodell.AntwortFormat(f"Antwort ohne verwertbaren Text (Modell laut Antwort: {r.model}; "
                                         f"Ende: {r.stop_reason})")
    return kurz, {"prompt_tokens": r.usage.input_tokens, "completion_tokens": r.usage.output_tokens}


def _status(e):
    """HTTP-Status eines Fehlers der Anfrage (urllib oder SDK von Anthropic), sonst None."""
    return e.code if isinstance(e, urllib.error.HTTPError) else getattr(e, "status_code", None)


def _gegenlesen(titel, text, kurz, schluessel):
    return _anfrage(titel, text, schluessel, system=GEGENLESEN, zusatz=f"\n\nKurzfassung zum Prüfen:\n{kurz}")


def _ergebnis(kurz, grund):
    """Felder eines Ergebnisses. Ein verworfener Entwurf wird nicht mehr aufbewahrt, nur der Grund (Prüfung November
    2026, Nr. 25: der Branch `kurzfassungen` ist öffentlich, 2.861 Entwürfe mit unbelegten Angaben waren dort lesbar).
    Das Feld `entwurf` bleibt leer bestehen; vorhandene Entwürfe werden beim nächsten Lauf ein letztes Mal geprüft
    und dann entfernt. Ändern sich die Regeln, entsteht eine verworfene Kurzfassung erst mit einer neuen Fassung
    (FASSUNG) neu."""
    if not grund:
        return {"kurzfassung": kurz, "verworfen": None, "entwurf": None}
    return {"kurzfassung": None, "verworfen": grund, "entwurf": None}


def laden(verzeichnis=None):
    path = Path(verzeichnis or VERZEICHNIS) / "kurzfassungen.jsonl"
    if not path.exists():
        return {}
    return {r["sha"]: r for r in map(json.loads, open(path, encoding="utf-8"))}


def _schreiben(base, have):
    tmp = base / "kurzfassungen.jsonl.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for sha in sorted(have):
            f.write(json.dumps(have[sha], ensure_ascii=False) + "\n")
    tmp.replace(base / "kurzfassungen.jsonl")


def erzeugen(verzeichnis=None, anfrage=_anfrage, gegenlesen=None):
    """Neue Kurzfassungen für Hauptdokumente mit Text (höchstens MAX_JE_LAUF je Lauf); Stichprobe einmalig."""
    if gegenlesen is None and anfrage is _anfrage and GEGENLESEN_AKTIV:
        gegenlesen = _gegenlesen
    schluessel = os.environ.get("MISTRAL_API_KEY")
    if not schluessel:
        print("Kurzfassungen: MISTRAL_API_KEY fehlt – nichts erzeugt.")
        return
    base = Path(verzeichnis or VERZEICHNIS)
    base.mkdir(parents=True, exist_ok=True)
    _stichproben_nachziehen(base)
    have = laden(base)
    texts = {}
    if config.TEXTE.exists():
        texts = {r["uri"]: r for r in map(json.loads, open(config.TEXTE, encoding="utf-8"))}
    papers = {}
    for line in open(config.PAPERS, encoding="utf-8"):
        p = json.loads(line)
        uri = (p.get("mainFile") or {}).get("id")
        # Sammellisten nichtöffentlicher Punkte teilen meist nur mit, dass es keine gibt: keine Kurzfassung
        if uri in texts and volltext.allowed(p.get("paperType")) and not volltext.sammelliste(p.get("name")):
            papers.setdefault(uri, p)
    # vorhandene Kurzfassungen der aktuellen Fassung nach den jeweils geltenden Prüfungen neu bewerten; früher
    # aufbewahrte Entwürfe werden dabei ein letztes Mal geprüft und entfernt (_ergebnis)
    for r in have.values():
        kurz = r["kurzfassung"] or r.get("entwurf")
        if r.get("fassung", 1) == FASSUNG and kurz and r.get("datei") in texts and r["datei"] not in papers:
            r.update(kurzfassung=None, entwurf=None, verworfen="keine Kurzfassung für diese Art von Vorlage")
        elif r.get("fassung", 1) == FASSUNG and kurz and r.get("datei") in texts:
            main = re.sub(r"\s+", " ", volltext.clean(texts[r["datei"]]["text"])[0]).strip()[:MAX_ZEICHEN]
            kurz = ohne_kostensatz(glaetten(kurz), main)
            grund = pruefe(kurz, main, (papers.get(r["datei"]) or {}).get("name") or "")
            r.update(_ergebnis(kurz, grund))
    for r in have.values():   # Entwürfe ohne Text im Zwischenspeicher: ebenfalls nicht länger aufbewahren
        if r.get("entwurf"):
            r["entwurf"] = None
    # ältere Fassungen zuerst (so entsteht die neue Stichprobe aus denselben Vorlagen), danach neue Texte, zuletzt
    # gescheiterte Anfragen (höchstens MAX_VERSUCHE; Code-Prüfung 23.10.2026: eine stets scheiternde Anfrage hielt
    # sonst jeden Lauf an derselben Stelle an)
    alt = lambda uri: have[texts[uri]["sha"]].get("fassung", 1) < FASSUNG
    erneut = lambda uri: (have[texts[uri]["sha"]].get("fehler")
                          and have[texts[uri]["sha"]].get("versuche", 1) < MAX_VERSUCHE)
    def lauf_mit(stand, modell, key, anfrage):
        """Ein Durchgang mit einem Modellstand; gibt (Zähler des Laufs, Stichprobenphase?) zurück."""
        todo = ([(uri, p) for uri, p in sorted(papers.items()) if texts[uri]["sha"] in have and alt(uri)]
                + [(uri, p) for uri, p in sorted(papers.items()) if texts[uri]["sha"] not in have]
                + [(uri, p) for uri, p in sorted(papers.items())
                   if texts[uri]["sha"] in have and not alt(uri) and erneut(uri)])[:MAX_JE_LAUF]
        # Modellstand noch nicht freigegeben: nur die Stichprobe entsteht (etwas mehr Anfragen, weil ein Teil verworfen wird)
        probe = stand not in MODELLSTAND_FREIGEGEBEN
        neue = lambda: [r for r in have.values() if r.get("modellstand", 1) == stand and r["kurzfassung"]
                        and r.get("fassung", 1) == FASSUNG]
        if probe:
            rest = STICHPROBE_MODELL - len(neue())
            todo = todo[:min(MAX_JE_LAUF, -(-rest * 7 // 5))] if rest > 0 else []
            if rest <= 0:
                print(f"::notice::Kurzfassungen: Stichprobe zum Modellstand {stand} ({modell}) liegt vor ({len(neue())}); "
                      "keine weiteren Anfragen bis zur Prüfung durch den Auftraggeber")
        tokens = [0, 0]
        lauf = {"gesendet": 0, "beantwortet": 0, "gescheitert": 0, "abbruch": None, "max_aus": 0}
        try:
            _erzeugen_alle(todo, texts, have, base, key, anfrage, gegenlesen, tokens, lauf, stand, modell)
        finally:   # bricht der Lauf ab (Zeitgrenze, Fehler), bleibt das Erzeugte erhalten
            _schreiben(base, have)
        ok = [r for r in have.values() if r["kurzfassung"] and r.get("fassung", 1) == FASSUNG]
        # Protokoll: tatsächlich gesendete Anfragen; Fehler = gescheiterte Anfragen und verworfene Kurzfassungen (Prüfung
        # November 2026, Nr. 3: bisher stand dort die Zahl der geplanten Anfragen, auch wenn keine beantwortet wurde)
        verworfen = sum(1 for uri, p in todo if have.get(texts[uri]["sha"], {}).get("verworfen"))
        sprachmodell.protokoll(base, "kurzfassungen", modell, lauf["gesendet"], {"ein": tokens[0], "aus": tokens[1]},
                               lauf["gescheitert"] + verworfen)
        je = f"; je Antwort im Mittel {tokens[1] // lauf['beantwortet']}, höchstens {lauf['max_aus']} Ausgabe-Tokens " \
             f"bei einer Grenze von {MAX_TOKENS}" if lauf["beantwortet"] else ""
        print(f"Kurzfassungen ({modell}): {len(todo)} geplant, {lauf['gesendet']} gesendet, {lauf['beantwortet']} "
              f"beantwortet ({tokens[0]} Eingabe-, {tokens[1]} Ausgabe-Tokens{je}), "
              f"{len(ok)} vorhanden, {sum(1 for r in have.values() if r.get('verworfen'))} verworfen, "
              f"{sum(1 for r in have.values() if r.get('fehler'))} gescheitert → {base}")
        _stichprobe(base, ok, papers)
        if stand > 1:
            _stichprobe(base, neue(), papers, f"stichprobe_kurzfassungen_modell{stand}.tsv")
        return lauf, probe

    lauf, probe = lauf_mit(MODELLSTAND, MODELL, schluessel, anfrage)
    ohne = bool(lauf["abbruch"]) and not lauf["beantwortet"]
    if ohne and AUSWEICHSTAND and AUSWEICHSTAND != MODELLSTAND and AUSWEICHSTAND not in MODELLSTAND_FREIGEGEBEN:
        # Ausweichweg: die Stichprobe mit Claude entsteht, sobald ein Lauf mit Mistral ganz ohne Antwort bleibt, auch
        # im Regelbetrieb; der Ausfall selbst wird unten weiter gemeldet
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            print("::notice::Kurzfassungen: Ausweichweg über Claude nicht möglich – ANTHROPIC_API_KEY fehlt")
        else:
            print(f"Kurzfassungen: Ausweichweg mit {MODELL_CLAUDE} (Modellstand {AUSWEICHSTAND})")
            zweiter, _ = lauf_mit(AUSWEICHSTAND, MODELL_CLAUDE, key, _anfrage_claude)
            if zweiter["abbruch"] and not zweiter["beantwortet"]:
                print(f"::warning::Kurzfassungen: auch der Lauf mit {MODELL_CLAUDE} blieb ohne Ergebnis "
                      f"({zweiter['abbruch']})")
    if ohne and probe:
        # Entscheidung des Auftraggebers 22.11.2026: bis zur Freigabe eines Modellstands kein roter Lauf
        print(f"::warning::Kurzfassungen: Lauf mit {MODELL} ohne Ergebnis beendet ({lauf['abbruch']}); der Modellstand "
              f"{MODELLSTAND} ist noch nicht freigegeben, daher kein Fehler")
        return
    if ohne:
        # Kein einziges Ergebnis: der Schritt endet mit Fehler, damit der Ausfall auffällt (vom 13. bis 20.11.2026
        # blieb er acht Tage unbemerkt, weil der Lauf grün endete). Der Bestand ist gesichert.
        rat = ("der Anbieter antwortet ohne Text; Längengrenze (MAX_TOKENS) und Modell prüfen" if lauf.get("form")
               else "Konto und Schlüssel beim Anbieter prüfen")
        raise SystemExit(f"Kurzfassungen: Lauf ohne Ergebnis beendet ({lauf['abbruch']}); {rat}.")
    if lauf["abbruch"]:
        print(f"::warning::Kurzfassungen: Lauf vorzeitig beendet ({lauf['abbruch']}) nach "
              f"{lauf['beantwortet']} beantworteten Anfragen")


def _erzeugen_alle(todo, texts, have, base, schluessel, anfrage, gegenlesen, tokens, lauf=None, stand=None,
                   modell=None):
    stand, modell = stand or MODELLSTAND, modell or MODELL
    lauf = lauf if lauf is not None else {"gesendet": 0, "beantwortet": 0, "gescheitert": 0, "abbruch": None}
    serie = []   # (sha, Eintrag vorher) der zuletzt in Folge gescheiterten Anfragen
    for i, (uri, p) in enumerate(todo, 1):
        main, _ = volltext.clean(texts[uri]["text"])
        main = re.sub(r"\s+", " ", main).strip()[:MAX_ZEICHEN]
        titel = f"{p.get('name') or ''} (Art der Vorlage: {p.get('paperType') or 'unbekannt'})"
        sha = texts[uri]["sha"]
        lauf["gesendet"] += 1
        try:
            kurz, usage = anfrage(titel, main, schluessel)
            kurz = ohne_kostensatz(glaetten(kurz if isinstance(kurz, str) else ""), main)
        except Exception as e:   # ein Fehler beim Anbieter hält den Lauf nicht auf
            lauf["gescheitert"] += 1
            vorher = have.get(sha) or {}
            konto = _status(e) in KONTO_FEHLER
            form = isinstance(e, sprachmodell.AntwortFormat)   # Antwort ohne Text (etwa nur Denkschritte)
            if konto or len(serie) + 1 >= SERIE:
                for alt_sha, v in serie:   # die Serie zählt nicht als Fehler der einzelnen Dokumente
                    if v:
                        have[alt_sha] = v
                    else:
                        have.pop(alt_sha, None)
                grund = f"HTTP {_status(e)}" if konto else f"{SERIE} Anfragen in Folge gescheitert" + (f": {e}" if form else "")
                print(f"  Lauf beendet: {grund} ({type(e).__name__}); die Dokumente werden im nächsten Lauf angefragt", flush=True)
                lauf["abbruch"] = grund
                lauf["form"] = form
                return
            serie.append((sha, dict(vorher) if vorher else None))
            versuche = vorher.get("versuche", 0) + 1 if vorher.get("fassung", 1) == FASSUNG and vorher.get("fehler") else 1
            have[sha] = {**vorher, "sha": sha, "datei": uri, "drucksache": p["reference"], "kurzfassung": None,
                         "verworfen": None, "entwurf": None, "modell": modell, "fassung": FASSUNG,
                         "fehler": f"Anfrage gescheitert: {type(e).__name__}", "versuche": versuche,
                         "erzeugt": datetime.now(timezone.utc).date().isoformat()}
            print(f"  {p['reference']}: Anfrage gescheitert ({type(e).__name__}, Versuch {versuche})", flush=True)
            continue
        serie.clear()
        lauf["beantwortet"] += 1
        tokens[0] += usage.get("prompt_tokens", 0)
        tokens[1] += usage.get("completion_tokens", 0)
        lauf["max_aus"] = max(lauf.get("max_aus", 0), usage.get("completion_tokens", 0))
        geaendert = False
        if gegenlesen and kurz:
            try:
                neu, usage = gegenlesen(titel, main, kurz, schluessel)
                tokens[0] += usage.get("prompt_tokens", 0)
                tokens[1] += usage.get("completion_tokens", 0)
                neu = ohne_kostensatz(glaetten(neu), main)
                if len(_woerter(neu)) >= 8:   # leere oder abgebrochene Antwort: erste Fassung bleibt
                    geaendert, kurz = neu != kurz, neu
            except Exception:   # Gegenlesen gescheitert: erste Fassung wird wie bisher geprüft
                pass
        grund = pruefe(kurz, main, p.get("name") or "")
        if not grund and stand > 1 and len(_woerter(kurz)) > MAX_WOERTER:
            grund = f"zu lang (mehr als {MAX_WOERTER} Wörter)"
        have[sha] = {"sha": sha, "datei": uri, "drucksache": p["reference"],
                     **_ergebnis(kurz, grund), "modell": modell, "modellstand": stand, "fassung": FASSUNG,
                     "gegengelesen": bool(gegenlesen), "beim_gegenlesen_geaendert": geaendert,
                     "erzeugt": datetime.now(timezone.utc).date().isoformat()}
        time.sleep(0.5)
        if i % 25 == 0:   # Zwischenstand sichern: bricht der Lauf ab, bleibt das Erzeugte erhalten
            _schreiben(base, have)


def _stichproben_nachziehen(base):
    """Hausnummern und Flurstücke in den Titeln vorhandener Stichproben ausblenden (einmalig wirksam, danach ohne
    Änderung); Urteile und Anmerkungen bleiben."""
    m, n = maske.fuer_alle(), 0
    for path in sorted(Path(base).glob("stichprobe_*.tsv")):
        n += maske.tsv_nachziehen(path, m)
    if n:
        print(f"Stichproben: in {n} Zeilen Hausnummer oder Flurstück ausgeblendet")
    return n


def _stichprobe(base, ok, papers, name=None):
    sample = base / (name or f"stichprobe_kurzfassungen_v{FASSUNG}.tsv")   # Fassung 1: stichprobe_kurzfassungen.tsv
    if not sample.exists() and len(ok) >= 30:
        # Titel ohne Hausnummer und Flurstück: der Branch `kurzfassungen` ist öffentlich (23.11.2026: die Stichprobe zum
        # Modellstand 2 und sechs ältere trugen Titel privater Baugrundstücke mit Hausnummer)
        m = maske.fuer_alle()
        titel = {p["reference"]: (m(p.get("name"), p["reference"]), p.get("web")) for p in papers.values()}
        pick = sorted(random.Random(20261020).sample(ok, 30), key=lambda r: r["drucksache"])
        with open(sample, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["nr", "drucksache", "titel", "link", "kurzfassung (KI)", "urteil (zutreffend/teilweise/falsch)",
                        "anmerkung"])
            for i, r in enumerate(pick, 1):
                t, web = titel.get(r["drucksache"], ("", ""))
                w.writerow([i, r["drucksache"], t, web or "", r["kurzfassung"], "", ""])
        print(f"Stichprobe Kurzfassungen: 30 → {sample}")


def fuer_seite(verzeichnis=None):
    """Drucksache → Kurzfassung für den Export, nur wenn freigegeben (auch der Stand des Modells, mit dem sie entstand)."""
    if not FREIGEGEBEN:
        return {}
    # Hausnummern auch hier prüfen: die übrigen Prüfungen laufen nur beim Erzeugen (mit Schlüssel). Geprüft wird der
    # geglättete Text, der erscheint („Straße **12**“ wird erst durch das Glätten zu „Straße 12“).
    return {r["drucksache"]: {"text": glaetten(r["kurzfassung"]), "modell": r["modell"], "erzeugt": r["erzeugt"]}
            for r in laden(verzeichnis).values()
            if r["kurzfassung"] and r.get("fassung", 1) == FASSUNG and not hausnummer(glaetten(r["kurzfassung"]))
            and r.get("modellstand", 1) in MODELLSTAND_FREIGEGEBEN}
