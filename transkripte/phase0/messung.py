"""Ratstranskripte, Schritt 0 (Prüfung, ohne Produktionscode): Abdeckung und Trefferquote.

1. Abdeckung: Sitzungen des Rates und des Hauptausschusses seit 2021 (Sitzungsliste der Stadt im Repository) gegen
   Aufzeichnungen in den Ratstranskripten (GraphQL von OParl-Lite: meetingByIdRef → transcriptPassages).
2. Trefferquote: 20 Vorlagen mit öffentlicher Beratung in einer Sitzung mit Aufzeichnung; Suche nach der
   Drucksachennummer (transcriptPassageSearch); Treffer in derselben Sitzung?

Es wird kein Text der Transkripte gespeichert, nur Zahlen, Sitzungs-IDs und Video-Adressen.
Aufruf: python transkripte/phase0/messung.py  (etwa eine Anfrage je Sekunde)
"""
import csv
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
G = "https://oparl.bonn.machdenstaat.de/graphql"
UA = "ratsatlas-bonn (https://github.com/daimpad/ratsatlas-bonn)"


def gql(query, variables=None):
    time.sleep(1)
    req = urllib.request.Request(G, data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                                 headers={"content-type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]


def sitzungen():
    heute = time.strftime("%Y-%m-%d")
    for m in json.load(open(ROOT / "data/raw/meetings.json", encoding="utf-8")):
        name, start = m.get("name") or "", (m.get("start") or "")[:10]
        if "2021-01-01" <= start <= heute and not m.get("cancelled") and ("Rat" in name or "Hauptausschuss" in name):
            yield m["id"].rsplit("/", 1)[1], name, start


def abdeckung():
    zeilen = []
    for idref, name, start in sorted(sitzungen(), key=lambda s: s[2]):
        lite = (gql("query($r:String!){ meetingByIdRef(idRef:$r){ id } }", {"r": idref})["meetingByIdRef"] or {}).get("id")
        n, video, dauer = 0, "", ""
        if lite:
            p = gql("query($m:ID!){ transcriptPassages(limit:1, filter:{meetingId:$m}){ totalCount items { revision { "
                    "recording { sourceUrl durationMs } } } } }", {"m": lite})["transcriptPassages"]
            n = p["totalCount"]
            if p["items"]:
                rec = p["items"][0]["revision"]["recording"]
                video, dauer = rec["sourceUrl"], round(int(rec["durationMs"]) / 60000)
        zeilen.append({"sitzung_id": idref, "name": name, "datum": start, "lite_id": lite or "",
                       "abschnitte": n, "video": video, "dauer_min": dauer})
        print(start, name[:40], n, file=sys.stderr)
    with open(OUT / "abdeckung.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(zeilen[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)
    return zeilen


def trefferquote(abd, n=20, seed=20261110):
    mit = {z["sitzung_id"] for z in abd if z["abschnitte"]}
    lite = {z["sitzung_id"]: z["lite_id"] for z in abd}
    kons = {}
    with open(ROOT / "data/raw/consultations_lite.jsonl", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            m, a = c.get("meeting") or {}, c.get("agendaItem") or {}
            if m and a.get("public") and m["uri"].rsplit("/", 1)[1] in mit:
                kons[c["uri"]] = m["uri"].rsplit("/", 1)[1]
    kandidaten = []
    with open(ROOT / "data/raw/papers.jsonl", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            for c in p.get("consultation") or []:
                if c.get("id") in kons:
                    kandidaten.append((p["reference"], p["name"], kons[c["id"]]))
                    break
    random.Random(seed).shuffle(kandidaten)
    zeilen = []
    for ref, titel, sid in kandidaten[:n]:
        hits = gql("query($q:String!){ transcriptPassageSearch(query:$q, limit:50){ totalCount items { passage { "
                   "revision { recording { meeting { id } } } } } } }", {"q": ref})["transcriptPassageSearch"]
        gleich = sum(1 for h in hits["items"]
                     if ((h["passage"]["revision"]["recording"] or {}).get("meeting") or {}).get("id") == lite[sid])
        zeilen.append({"drucksache": ref, "sitzung_id": sid, "treffer_gesamt": hits["totalCount"],
                       "treffer_in_sitzung": gleich, "titel": titel[:120]})
        print(ref, hits["totalCount"], gleich, file=sys.stderr)
    with open(OUT / "trefferquote.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(zeilen[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)
    return zeilen


if __name__ == "__main__":
    abd = abdeckung()
    tq = trefferquote(abd)
    mit = [z for z in abd if z["abschnitte"]]
    print(f"Abdeckung: {len(mit)} von {len(abd)} Sitzungen mit Aufzeichnung; "
          f"Trefferquote: {sum(1 for z in tq if z['treffer_in_sitzung'])} von {len(tq)} Vorlagen mit Treffer in der Sitzung")
