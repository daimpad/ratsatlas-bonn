"""Ratstranskripte, Nachmessung zu Schritt 0: Suche mit einem Stichwort aus dem Titel statt der Drucksachennummer.

Stichprobe: 30 Vorlagen (ohne Vorlagen der Einwohnerschaft und ihre Folgevorlagen) mit öffentlicher Beratung im Rat
in einer Sitzung mit Aufzeichnung. Drei Regeln für das Stichwort:
  ort   – Name eines Ortes aus dem Titel (Verortung Stufe A/B aus dem Titel: Straße, Platz, Gebäude, Ortsteil)
  wort  – das längste Wort des Titels (mindestens 6 Buchstaben, großgeschrieben, ohne Ziffern, ohne Verfahrenswörter)
  beide – ort, sonst wort
Gemessen wird, ob die Suche bei den Ratstranskripten (transcriptPassageSearch) einen Treffer in derselben Sitzung hat
und wie viele Treffer es insgesamt gibt (ein Wort mit sehr vielen Treffern hilft wenig). Es wird kein Text der
Transkripte gespeichert, nur Zahlen. Aufruf: .venv/bin/python transkripte/phase0/stichwort.py (etwa eine Anfrage je Sekunde)
"""
import csv
import json
import random
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUT = Path(__file__).resolve().parent / "stichwort.tsv"
G = "https://oparl.bonn.machdenstaat.de/graphql"
UA = "ratsatlas-bonn (https://github.com/daimpad/ratsatlas-bonn)"
SEITEN = 4            # höchstens 4 × 100 Treffer je Suchwort durchsehen
STOPP = {
    "antrag", "anträge", "anfrage", "anfragen", "vorlage", "beschluss", "beschlüsse", "stellungnahme", "verwaltung",
    "mitteilung", "ergänzung", "änderung", "änderungsantrag", "sachstand", "bericht", "beratung", "fraktion",
    "fraktionen", "dringlichkeitsantrag", "bundesstadt", "stadtverwaltung", "umsetzung", "einrichtung", "durchführung",
    "erweiterung", "anpassung", "fortschreibung", "aufstellung", "satzung", "beschlussvorlage", "ergänzungsantrag",
    "verwaltungsvorlage", "haushaltsjahr", "haushaltsjahre", "tischvorlage", "informationen", "information",
    "beteiligung", "einwohnerinnen", "einwohner", "bürgerinnen", "bürger", "zusammenhang", "grundsatzbeschluss",
    "bürgerantrag", "ratsbeschluss", "ratsbeschlusses", "beschlusses", "vertagungsbitte", "kenntnisnahme",
}


def gql(query, variables):
    time.sleep(1)
    req = urllib.request.Request(G, data=json.dumps({"query": query, "variables": variables}).encode(),
                                 headers={"content-type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]


def wort(titel):
    kandidaten = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*", titel)
                  if len(w) >= 6 and w[0].isupper() and not re.search(r"\d", w) and w.lower().strip("-") not in STOPP]
    return max(kandidaten, key=len).strip("-") if kandidaten else ""


def ort(c, pid, titel):
    for (name,) in c.execute(
            "select coalesce(l.street, l.description) from paper_location pl join location l on l.id = pl.location_id "
            "where pl.paper_id = ? and pl.method not like 'volltext%' and pl.method not like '%vererb%' "
            "order by pl.confidence = 'hoch' desc", (pid,)):
        name = re.sub(r",.*", "", name or "").strip()
        if name and name.lower() in titel.lower():
            return name
    return ""


def treffer(stichwort, lite):
    gesamt = gleich = 0
    for seite in range(SEITEN):
        d = gql("query($q:String!,$o:Int){ transcriptPassageSearch(query:$q, limit:100, offset:$o){ totalCount items "
                "{ passage { revision { recording { meeting { id } } } } } } }",
                {"q": stichwort, "o": seite * 100})["transcriptPassageSearch"]
        gesamt = d["totalCount"]
        gleich += sum(1 for h in d["items"]
                      if ((h["passage"]["revision"]["recording"] or {}).get("meeting") or {}).get("id") == lite)
        if gleich or (seite + 1) * 100 >= gesamt:
            break
    return gesamt, gleich


def main(n=30, seed=20261110):
    aufz = json.loads((ROOT / "data/raw/aufzeichnungen.json").read_text(encoding="utf-8"))
    mit = {k: v["lite_id"] for k, v in aufz.items() if v.get("video")}
    privat = set(json.loads((ROOT / "data/export/bonn/chat/einwohner.json").read_text(encoding="utf-8"))["drucksachen"])
    c = sqlite3.connect(ROOT / "data/build/allris.sqlite")
    kandidaten = {}
    for pid, ref, name, mid in c.execute(
            "select p.id, p.reference, p.name, co.meeting_id from paper p join consultation co on co.paper_id = p.id "
            "join agenda_item a on a.id = co.agenda_item_id where a.public = 1 and co.meeting_id is not null"):
        sid = (mid or "").rsplit("/", 1)[-1]
        if sid in mit and ref not in privat:
            kandidaten.setdefault(pid, (ref, name, sid))
    liste = sorted(kandidaten.items())
    random.Random(seed).shuffle(liste)
    zeilen = []
    for pid, (ref, titel, sid) in liste[:n]:
        o, w = ort(c, pid, titel), wort(titel)
        z = {"drucksache": ref, "sitzung_id": sid, "titel": titel[:140], "ort": o, "wort": w}
        cache = {}
        for regel, kw in (("ort", o), ("wort", w)):
            if kw and kw not in cache:
                cache[kw] = treffer(kw, mit[sid])
            z[f"{regel}_gesamt"], z[f"{regel}_in_sitzung"] = cache.get(kw, ("", ""))
        zeilen.append(z)
        print(ref, o, z["ort_in_sitzung"], w, z["wort_in_sitzung"], file=sys.stderr)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(zeilen[0]), delimiter="\t", lineterminator="\n")
        wr.writeheader()
        wr.writerows(zeilen)

    o_n = [z for z in zeilen if z["ort"]]
    w_n = [z for z in zeilen if z["wort"]]
    b_hit = sum(1 for z in zeilen if (z["ort_in_sitzung"] if z["ort"] else z["wort_in_sitzung"]))
    print(f"ort: {len(o_n)} mit Stichwort, {sum(1 for z in o_n if z['ort_in_sitzung'])} mit Treffer in der Sitzung")
    print(f"wort: {len(w_n)} mit Stichwort, {sum(1 for z in w_n if z['wort_in_sitzung'])} mit Treffer in der Sitzung")
    print(f"beide: {b_hit} von {len(zeilen)} mit Treffer in der Sitzung")


if __name__ == "__main__":
    main()
