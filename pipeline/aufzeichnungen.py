"""Aufzeichnungen von Sitzungen (Ratstranskripte von Mika Baumeister, bonn.biz; über die GraphQL-Schnittstelle von
OParl-Lite). Konzept `transkripte/KONZEPT.md`, Schritt 0 `transkripte/phase0/BERICHT.md`.

Nur Angaben zur Aufzeichnung je Sitzung (Video-Adresse, Dauer, Zahl der Abschnitte), nie Text der Transkripte; der
Ratsatlas verweist auf das Video und auf die Suche bei bonn.biz (Entscheidungen des Auftraggebers 10.11.2026: nur
Verweise, Ebene der Sitzung, keine Namen). Zwischenspeicher `data/raw/aufzeichnungen.json` (im Repository und im
Zwischenspeicher des Workflows): neu abgefragt werden nur Sitzungen ohne Eintrag und Sitzungen des letzten Jahres
ohne Aufzeichnung; `python -m pipeline fetch-aufzeichnungen --alle` fragt alle erneut ab.
"""
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date, timedelta
from functools import lru_cache

from . import config
from .net import post_graphql

DATEI = config.RAW / "aufzeichnungen.json"
SUCHE = "https://bonn.biz/ratstranskripte"
SEIT = "2021-01-01"            # Beginn der Aufzeichnungen laut bonn.biz
NEU_PRUEFEN_TAGE = 365         # Sitzungen ohne Aufzeichnung so lange erneut abfragen
PAUSE = float(os.environ.get("AUFZEICHNUNGEN_PAUSE", "1"))   # Sekunden zwischen zwei Anfragen
QUELLE = {"name": "Ratstranskripte (Mika Baumeister, bonn.biz)", "url": SUCHE,
          "schnittstelle": config.LITE_GRAPHQL, "lizenz": "CC BY-NC 4.0 (Transkripte; im Ratsatlas nur verlinkt)",
          "hinweis": "automatisch erkannt, nicht amtlich; maßgeblich sind Video und Niederschrift"}

STICHWORTE = config.RAW / "aufzeichnungen_stichworte.json"
BUDGET = float(os.environ.get("AUFZEICHNUNGEN_BUDGET", "480"))   # Sekunden je Lauf für neue Stichwörter
SEITEN = 4            # je Stichwort höchstens 4 × 100 Treffer durchsehen; mehr Treffer: zu allgemein
# Wörter, die als Stichwort nichts über den Gegenstand sagen: Verfahrens- und Verwaltungswörter; die letzte Zeile
# aus der Stichprobe vom 10.11.2026 (transkripte/phase0/stichwort.tsv: Treffer meist zu anderen Punkten)
STOPP = {
    "antrag", "anträge", "anfrage", "anfragen", "vorlage", "beschluss", "beschlüsse", "stellungnahme", "verwaltung",
    "mitteilung", "ergänzung", "änderung", "änderungsantrag", "sachstand", "bericht", "beratung", "fraktion",
    "fraktionen", "dringlichkeitsantrag", "bundesstadt", "stadtverwaltung", "umsetzung", "einrichtung", "durchführung",
    "erweiterung", "anpassung", "fortschreibung", "aufstellung", "satzung", "beschlussvorlage", "ergänzungsantrag",
    "verwaltungsvorlage", "haushaltsjahr", "haushaltsjahre", "tischvorlage", "informationen", "information",
    "beteiligung", "einwohnerinnen", "einwohner", "bürgerinnen", "bürger", "zusammenhang", "grundsatzbeschluss",
    "bürgerantrag", "ratsbeschluss", "ratsbeschlusses", "beschlusses", "vertagungsbitte", "kenntnisnahme",
    "erarbeitung", "aufwendungen", "veranstaltungen", "vorhabenbezogener", "planungssicherheit", "ordnungsbehördlichen",
}
# Vorlagen der Einwohnerschaft (wie chat.einwohner): kein Stichwort aus ihrem Titel und dem ihrer Folgevorlagen
EINWOHNER_ARTEN = {"Bürgerantrag § 24 GO - Öffentlich", "Anregungen und Beschwerden", "Einwohnerfrage", "Bürgerbrief"}
EINWOHNER_TITEL = re.compile(r"bürgerantrag|einwohner|anregung|beschwerde", re.I)
Q_SUCHE = ("query($q:String!,$o:Int){ transcriptPassageSearch(query:$q, limit:100, offset:$o){ totalCount items "
           "{ passage { revision { recording { meeting { id } } } } } } }")

Q_SITZUNG = "query($r:String!){ meetingByIdRef(idRef:$r){ id } }"
Q_AUFZ = ("query($m:ID!){ transcriptPassages(limit:1, filter:{meetingId:$m}){ totalCount items { revision { "
          "recording { sourceUrl durationMs } } } } }")


def gremium_mit_aufzeichnung(name):
    """Rat und Hauptausschuss (Schritt 0: nur dort gibt es Aufzeichnungen)."""
    return bool(name) and ("Rat" in name or "Hauptausschuss" in name)


def _sitzungen(meetings, heute):
    for m in meetings:
        start = (m.get("start") or "")[:10]
        if SEIT <= start <= heute and not m.get("cancelled") and gremium_mit_aufzeichnung(m.get("name")):
            yield m["id"].rsplit("/", 1)[1], start


def _abfragen(idref, post=post_graphql):
    lite = (post(config.LITE_GRAPHQL, Q_SITZUNG, {"r": idref})["meetingByIdRef"] or {}).get("id")
    eintrag = {"lite_id": lite or "", "abschnitte": 0, "video": "", "dauer_min": 0}
    if lite:
        time.sleep(PAUSE)
        p = post(config.LITE_GRAPHQL, Q_AUFZ, {"m": lite})["transcriptPassages"]
        eintrag["abschnitte"] = p["totalCount"]
        if p["items"]:
            rec = p["items"][0]["revision"]["recording"] or {}
            url = rec.get("sourceUrl") or ""
            eintrag["video"] = url if url.startswith("https://www.youtube.com/") else ""
            eintrag["dauer_min"] = round(int(rec.get("durationMs") or 0) / 60000)
    return eintrag


def fetch(alle=None, post=post_graphql, heute=None, datei=None):
    """Zwischenspeicher ergänzen; bricht bei Fehlern nicht ab, der vorhandene Stand bleibt."""
    alle = ("--alle" in sys.argv) if alle is None else alle
    datei = datei or DATEI
    heute = heute or date.today().isoformat()
    grenze = (date.fromisoformat(heute) - timedelta(days=NEU_PRUEFEN_TAGE)).isoformat()
    bestand = json.loads(datei.read_text(encoding="utf-8")) if datei.exists() else {}
    meetings = json.loads((config.RAW / "meetings.json").read_text(encoding="utf-8"))
    neu = fehler = 0
    for idref, start in _sitzungen(meetings, heute):
        alt = bestand.get(idref)
        if alt and not alle and (alt["video"] or start < grenze):
            continue
        try:
            bestand[idref] = {**_abfragen(idref, post), "datum": start, "geprueft": heute}
            neu += 1
        except Exception as e:   # Schnittstelle nicht erreichbar: Stand behalten, nächster Lauf versucht es erneut
            fehler += 1
            print(f"Aufzeichnungen: Sitzung {idref} nicht abgefragt ({e})", file=sys.stderr)
            if fehler >= 5:
                break
        time.sleep(PAUSE)
    tmp = datei.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(bestand.items(), key=lambda kv: (kv[1]["datum"], kv[0]))),
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(datei)
    mit = sum(1 for v in bestand.values() if v["video"])
    print(f"Aufzeichnungen: {neu} Sitzungen abgefragt, {fehler} Fehler; {mit} von {len(bestand)} mit Aufzeichnung → {datei}")


def wort(titel):
    """Stichwort aus dem Titel: das längste großgeschriebene Wort mit mindestens 6 Buchstaben, ohne Ziffern und ohne
    Verfahrenswörter (Stichprobe 10.11.2026: 21 von 30 mit Treffer in derselben Sitzung)."""
    kandidaten = [w.strip("-") for w in re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*", titel or "")
                  if len(w) >= 6 and w[0].isupper() and not re.search(r"\d", w) and w.lower().strip("-") not in STOPP]
    return max(kandidaten, key=len) if kandidaten else ""


def _einwohner(c):
    nachbarn = {}
    for a, b in c.execute("select parent_id, child_id from paper_relation"):
        nachbarn.setdefault(a, set()).add(b)
        nachbarn.setdefault(b, set()).add(a)
    offen = [pid for pid, art, name in c.execute("select id, paper_type, name from paper")
             if art in EINWOHNER_ARTEN or EINWOHNER_TITEL.search(name or "")]
    gesehen = set(offen)
    while offen:
        for n in nachbarn.get(offen.pop(), ()):
            if n not in gesehen:
                gesehen.add(n)
                offen.append(n)
    return gesehen


def _paare(db):
    """(Drucksache, Sitzungsnummer, Titel) öffentlicher Beratungen in Sitzungen mit Aufzeichnung, ohne Einwohnerschaft."""
    mit = set(_video_je_sitzung())
    c = sqlite3.connect(db)
    privat = _einwohner(c)
    for pid, ref, name, mid in c.execute(
            "select p.id, p.reference, p.name, co.meeting_id from paper p join consultation co on co.paper_id = p.id "
            "join agenda_item a on a.id = co.agenda_item_id where a.public = 1 and co.meeting_id is not null "
            "order by p.reference"):
        sid = mid.rsplit("/", 1)[-1]
        if sid in mit and pid not in privat:
            yield ref, sid, name


def _sitzungen_mit_treffer(w, post):
    """Gesamtzahl der Treffer und OParl-Lite-IDs der Sitzungen unter den ersten SEITEN × 100 Treffern."""
    gesamt, ids = 0, set()
    for seite in range(SEITEN):
        d = post(config.LITE_GRAPHQL, Q_SUCHE, {"q": w, "o": seite * 100})["transcriptPassageSearch"]
        gesamt = d["totalCount"]
        ids |= {((h["passage"]["revision"]["recording"] or {}).get("meeting") or {}).get("id") for h in d["items"]}
        if (seite + 1) * 100 >= gesamt:
            break
        time.sleep(PAUSE)
    ids.discard(None)
    return gesamt, ids


def fetch_stichworte(db=None, post=post_graphql, heute=None, datei=None, budget=None):
    """Stichwort je Vorlage und Sitzung prüfen (Entscheidung des Auftraggebers 10.11.2026: vorbefüllt nur, wenn die
    Suche einen Treffer in derselben Sitzung hat). Je Stichwort eine Suche, im Zwischenspeicher; je Lauf höchstens
    BUDGET Sekunden, der Rest folgt im nächsten Lauf. Gespeichert werden nur Wort und Zahlen, kein Text."""
    db = db or config.DB
    datei = datei or STICHWORTE
    heute = heute or date.today().isoformat()
    budget = BUDGET if budget is None else budget
    bestand = json.loads(datei.read_text(encoding="utf-8")) if datei.exists() else {"woerter": {}, "paare": {}}
    lite = {k: v["lite_id"] for k, v in json.loads(DATEI.read_text(encoding="utf-8")).items()} if DATEI.exists() else {}
    start, neu, fehler = time.monotonic(), 0, 0
    for ref, sid, titel in _paare(db):
        schluessel = f"{ref}|{sid}"
        w = wort(titel)
        if not w or bestand["paare"].get(schluessel, {}).get("wort") == w:
            continue
        if w not in bestand["woerter"]:
            if time.monotonic() - start > budget or fehler >= 5:
                continue
            try:
                gesamt, ids = _sitzungen_mit_treffer(w, post)
            except Exception as e:   # Schnittstelle nicht erreichbar: nächster Lauf versucht es erneut
                fehler += 1
                print(f"Stichwort {w!r} nicht abgefragt ({e})", file=sys.stderr)
                continue
            bestand["woerter"][w] = {"gesamt": gesamt, "sitzungen": sorted(ids), "geprueft": heute}
            neu += 1
            time.sleep(PAUSE)
        bestand["paare"][schluessel] = {"wort": w, "treffer": lite.get(sid, "") in bestand["woerter"][w]["sitzungen"]}
    tmp = datei.with_suffix(".tmp")
    tmp.write_text(json.dumps({"woerter": dict(sorted(bestand["woerter"].items())),
                               "paare": dict(sorted(bestand["paare"].items()))}, ensure_ascii=False, indent=0) + "\n",
                   encoding="utf-8")
    tmp.replace(datei)
    mit = sum(1 for v in bestand["paare"].values() if v["treffer"])
    print(f"Stichwörter: {neu} neu abgefragt, {fehler} Fehler; {mit} von {len(bestand['paare'])} Beratungen mit "
          f"Treffer in derselben Sitzung → {datei}")


@lru_cache(maxsize=1)
def _stichwort_je_paar():
    if not STICHWORTE.exists():
        return {}
    return {k: v["wort"] for k, v in json.loads(STICHWORTE.read_text(encoding="utf-8"))["paare"].items() if v["treffer"]}


def stichwort(reference, meeting_id):
    """Geprüftes Stichwort für die Suche in den Ratstranskripten oder None."""
    if not reference or not meeting_id:
        return None
    return _stichwort_je_paar().get(f"{reference}|{str(meeting_id).rsplit('/', 1)[-1]}")


def suchlink(w=None):
    """Adresse der Suche bei bonn.biz, mit geprüftem Stichwort vorbefüllt."""
    from urllib.parse import quote
    return f"{SUCHE}?q={quote(w)}" if w else SUCHE


# Hinweis im Akkordeon „Mehr über die Ratstranskripte erfahren“ (Wortlaut des Auftraggebers 10.11.2026)
HINWEIS = ("Automatisch erkannt aus den Videoaufzeichnungen, nicht amtlich; maßgeblich sind Video und Niederschrift. "
           "Quelle: verlinkte Ratstranskriptionen von Mika Baumeister auf bonn.biz von Christoph Görn | CC BY-NC 4.0.")
HINWEIS_THEMA = ""
HINWEIS_VORGANG = ("Das Suchwort stammt aus dem Titel der Vorlage; es ist nur gesetzt, wenn die Suche damit einen Treffer "
                   "in dieser Sitzung findet. Die Treffer stammen aus allen Sitzungen seit 2021.")
# Video-Symbol (Linien, viewBox 0 0 24 24), gleich in site/app.js
SYMBOL = ('<svg class="aufz-symbol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
          'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
          '<rect x="2.5" y="5.5" width="13" height="13" rx="2.5"/><path d="M15.5 10.5 21 7.5v9l-5.5-3"/></svg>')


def karte(video=None, w=None, links=None, ueberschrift="Aufzeichnung dieser Sitzung", zusatz=HINWEIS_VORGANG):
    """Kasten für statische Seiten: Symbol, Überschrift mit „nicht amtlich“, Schaltflächen zu Video und Suche,
    Akkordeon mit Quelle und Lizenz. links: eigene Suchlinks (Themenseiten) statt Video und Suche."""
    from html import escape
    if links is None:
        if not str(video or "").startswith("https://www.youtube.com/"):
            return ""
        such = f"Im Transkript suchen: „{escape(w)}“" if w else "Im Transkript suchen"
        links = (f'<a class="aufz-knopf" href="{escape(video)}" target="_blank" rel="noopener">Video der Sitzung'
                 f'<span class="visually-hidden"> (YouTube, neuer Tab)</span></a> '
                 f'<a class="aufz-knopf aufz-knopf-leise" href="{escape(suchlink(w))}" target="_blank" rel="noopener">'
                 f'{such}<span class="visually-hidden"> (bonn.biz, neuer Tab)</span></a>')
    return (f'<div class="aufz-karte">{SYMBOL}<div class="aufz-inhalt">'
            f'<p class="aufz-titel">{ueberschrift} <span class="aufz-kurz">nicht amtlich</span></p>'
            f'<p class="aufz-links">{links}</p>'
            f'<details class="aufz-mehr"><summary>Mehr über die Ratstranskripte erfahren</summary>'
            f'<p>{escape(HINWEIS)}{" " + escape(zusatz) if zusatz else ""}</p></details></div></div>')


@lru_cache(maxsize=1)
def _video_je_sitzung():
    if not DATEI.exists():
        return {}
    return {k: v["video"] for k, v in json.loads(DATEI.read_text(encoding="utf-8")).items() if v.get("video")}


def video(meeting_id):
    """Video-Adresse der Sitzung (OParl-ID oder Nummer der Stadt) oder None."""
    if not meeting_id:
        return None
    return _video_je_sitzung().get(str(meeting_id).rsplit("/", 1)[-1])


def stand():
    """Jüngster Prüftag im Zwischenspeicher (Abrufzeitpunkt der Quelle)."""
    if not DATEI.exists():
        return None
    return max((v.get("geprueft", "") for v in json.loads(DATEI.read_text(encoding="utf-8")).values()), default=None)


def liste():
    """Sitzungen mit Aufzeichnung, neueste zuerst: [{sitzung_id, datum, video, dauer_min}] (für Assistent und Gremien)."""
    if not DATEI.exists():
        return []
    d = json.loads(DATEI.read_text(encoding="utf-8"))
    return [{"sitzung_id": k, "datum": v["datum"], "video": v["video"], "dauer_min": v["dauer_min"]}
            for k, v in sorted(d.items(), key=lambda kv: kv[1]["datum"], reverse=True) if v.get("video")]
