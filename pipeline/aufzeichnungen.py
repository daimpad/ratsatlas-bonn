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
