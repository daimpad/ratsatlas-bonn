"""Seite rat-im-video/: Aufzeichnungen der Ratssitzungen (Entscheidungen des Auftraggebers 24.11.2026: eigene Seite
„Rat im Video“ mit Kachel im Menü „Wer entscheidet“, Link im Suchmenü und Zeile in „Aktuell in Bonn“).

Regeln wie transkripte/KONZEPT.md: nur Verweise auf Video (YouTube) und Suche in den Ratstranskripten (bonn.biz),
kein Text, keine Namen, nur auf Ebene der Sitzung; Hinweis „nicht amtlich“ sichtbar, Quelle und Lizenz im Akkordeon.

Je Sitzung des Rates seit 2021: Datum, Uhrzeit, Dauer, Video, Transkript durchsuchen, Tagesordnung der Stadt und die
öffentlichen Vorlagen, die dort beraten wurden (aus den Gebietsdateien: Beratungen mit derselben Aufzeichnung; Titel
maskiert wie überall), verlinkt auf die Seite je Vorgang oder auf die Karte. Sitzungen des Rates ohne Aufzeichnung
stehen mit „keine Aufzeichnung“ da, damit die Lücken sichtbar bleiben; der Hauptausschuss nur mit Aufzeichnung.
Je Jahr eine Unterseite rat-im-video/<jahr>/ mit den Vorlagen, damit die Übersicht klein bleibt (alle Jahre auf einer
Seite: rund 950 KB). Keine Erzeugungszeitpunkte (stabile Ausgabe)."""
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from html import escape

from . import aufzeichnungen
from .export import slug
from .gebietsseiten import _date
from .vorgangsseiten import _karte, _vorlagen

PFAD = "rat-im-video/"
ROOT = "../"
TITEL = "Rat im Video"
UNTERTITEL = "Aufzeichnungen und Transkripte der Ratssitzungen seit 2021"
GREMIEN = ("Rat", "Hauptausschuss")
NEU_TAGE = 30   # so lange heißt es „noch keine Aufzeichnung“: Videos erscheinen bei bonn.biz mit Verzug


def _top(nummer):
    """Sortierschlüssel für Tagesordnungspunkte wie „1.19“ oder „10“."""
    return [int(x) for x in re.findall(r"\d+", str(nummer or ""))] or [9999]


def daten(base, heute):
    """Sitzungen von Rat und Hauptausschuss seit Beginn der Aufzeichnungen bis heute, neueste zuerst, mit Vorlagen."""
    zeit = json.loads((base / "zeit.json").read_text(encoding="utf-8"))
    alle, gebiet, _ = _vorlagen(base)
    je_video = defaultdict(dict)
    for ref, p in alle.items():
        for s in p.get("steps") or []:
            if s.get("aufzeichnung") and ref not in je_video[s["aufzeichnung"]]:
                je_video[s["aufzeichnung"]][ref] = s.get("number")
    dauer = {e["video"]: e["dauer_min"] for e in aufzeichnungen.liste()}
    out = []
    for m in zeit.get("meetings") or []:
        if not (aufzeichnungen.SEIT <= m["date"] <= heute) or m.get("cancelled"):
            continue
        if m.get("gremium") not in GREMIEN or not aufzeichnungen.gremium_mit_aufzeichnung(m.get("name")):
            continue
        video = m.get("video") if str(m.get("video") or "").startswith("https://www.youtube.com/") else None
        if not video and m["gremium"] != "Rat":
            continue
        refs = sorted(je_video.get(video, {}).items(), key=lambda kv: (_top(kv[1]), kv[0])) if video else []
        jung = heute != "9999-12-31" and m["date"] >= (date.fromisoformat(heute) - timedelta(days=NEU_TAGE)).isoformat()
        out.append({"date": m["date"], "time": m.get("time"), "gremium": m["gremium"], "web": m.get("web"), "jung": jung,
                    "video": video, "dauer_min": dauer.get(video),
                    "vorlagen": [{"reference": r, "top": n, "name": alle[r]["name"], "seite": bool(alle[r].get("seite")),
                                  "gebiet": gebiet[r]} for r, n in refs]})
    return sorted(out, key=lambda x: (x["date"], x["time"] or ""), reverse=True)


def _dauer(minuten):
    if not minuten:
        return ""
    h, m = divmod(int(minuten), 60)
    return f"{h} Std. {m} Min." if h else f"{m} Min."


def _vorlage(v, root):
    ziel = f"{root}vorgang/{slug(v['reference'])}/" if v["seite"] else _karte(v["gebiet"], v["reference"]).replace("../../", root)
    top = f'<span class="riv-top">TOP {escape(str(v["top"]))}</span> ' if v.get("top") else ""
    return (f'<li>{top}<a href="{escape(ziel)}">{escape(v["name"] or v["reference"])}</a> '
            f'<span class="riv-ref">{escape(v["reference"])}</span></li>')


def _anker(s):
    return f"s{s['date']}-{slug(s['gremium'])}"


def _sitzung(s, mit_vorlagen, root):
    zeit = f" · {escape(s['time'])} Uhr" if s.get("time") else ""
    kopf = (f'<h3 class="riv-h" id="{_anker(s)}"><time datetime="{s["date"]}">{_date(s["date"])}</time>{zeit}'
            f' · {escape(s["gremium"])}</h3>')
    to = (f'<a href="{escape(s["web"])}" target="_blank" rel="noopener">Tagesordnung'
          f'<span class="visually-hidden"> (Ratsinformationssystem, neuer Tab)</span></a>') if s.get("web") else ""
    if not s["video"]:
        ohne = "Noch keine Aufzeichnung in der Quelle" if s.get("jung") else "Keine Aufzeichnung in der Quelle"
        return (f'<li class="riv-sitzung riv-ohne">{kopf}<p class="riv-meta">{ohne}'
                f'{" · " + to if to else ""}</p></li>')
    knoepfe = (f'<a class="aufz-knopf" href="{escape(s["video"])}" target="_blank" rel="noopener">Video der Sitzung'
               f'<span class="visually-hidden"> (YouTube, neuer Tab)</span></a> '
               f'<a class="aufz-knopf aufz-knopf-leise" href="{escape(aufzeichnungen.suchlink())}" target="_blank" '
               f'rel="noopener">Transkript durchsuchen<span class="visually-hidden"> (bonn.biz, neuer Tab)</span></a>')
    n = len(s["vorlagen"])
    if mit_vorlagen:
        vorl = (f'<details class="riv-vorlagen"><summary>Beratene Vorlagen ({n})</summary>'
                f'<ul>{"".join(_vorlage(v, root) for v in s["vorlagen"])}</ul></details>') if n else ""
        meta = " · ".join(x for x in (_dauer(s.get("dauer_min")), to) if x)
    else:
        vorl = ""
        liste = f'<a href="{s["date"][:4]}/#{_anker(s)}">{n} beratene Vorlagen</a>' if n else ""
        meta = " · ".join(x for x in (_dauer(s.get("dauer_min")), liste, to) if x)
    return (f'<li class="riv-sitzung">{kopf}<p class="riv-meta">{meta}</p>'
            f'<p class="aufz-links">{knoepfe}</p>{vorl}</li>')


GRENZEN = """    <h2 id="grenzen">Grenzen</h2>
    <ul>
      <li>Aufzeichnungen gibt es nur für den Rat; vom Hauptausschuss, den Fachausschüssen und den Bezirksvertretungen gibt es in der Quelle keine.</li>
      <li>In den Jahren 2023 und 2024 fehlen viele Aufzeichnungen in der Quelle.</li>
      <li>Die Transkripte sind automatisch erkannt und nicht amtlich. Maßgeblich sind Video und Niederschrift.</li>
      <li>Der Ratsatlas zeigt keinen Text aus den Transkripten und keine Namen; er verlinkt nur.</li>
      <li>„Beratene Vorlagen“ sind die öffentlichen Vorlagen, deren Beratung laut Ratsinformationssystem in dieser Sitzung lag. Nichtöffentliche Punkte fehlen.</li>
    </ul>"""


def _quellen(stand, root):
    return (f'    <details class="hh-mehr meta-acc"><summary>Quellen</summary><p>Sitzungen und Beratungen: '
            f'OParl-Schnittstelle der Stadt Bonn (CC0) und OParl-Lite Bonn (CC BY 4.0). Videos: YouTube-Kanal der Stadt '
            f'Bonn. Ratstranskripte: bonn.biz, Mika Baumeister (CC BY-NC 4.0), nur verlinkt.'
            f'{f" Aufzeichnungen geprüft am {_date(stand)}." if stand else ""}</p></details>\n'
            f'    <p><a href="{root}">Zur Karte</a> · <a href="{root}begriffe/">Begriffe</a></p>')


def _such_karte():
    return aufzeichnungen.karte(links=(
        f'<a class="aufz-knopf" href="{escape(aufzeichnungen.suchlink())}" target="_blank" rel="noopener">In allen '
        f'Ratstranskripten suchen<span class="visually-hidden"> (bonn.biz, neuer Tab)</span></a>'),
        ueberschrift="Ratstranskripte durchsuchen", zusatz="")


def _jahre(sitzungen):
    jahre = defaultdict(list)
    for s in sitzungen:
        jahre[s["date"][:4]].append(s)
    return jahre


def body(sitzungen, stand):
    jahre = _jahre(sitzungen)
    mit = sum(1 for s in sitzungen if s["video"])
    rat = [s for s in sitzungen if s["gremium"] == "Rat"]
    sprung = " · ".join(f'<a href="#j{j}">{j}</a>' for j in jahre)
    teile = []
    for j, liste in jahre.items():
        n = sum(1 for s in liste if s["video"])
        teile.append(f'    <h2 id="j{j}">{j} <span class="riv-zahl">{n} mit Aufzeichnung</span></h2>\n'
                     f'    <ol class="riv-liste">{"".join(_sitzung(s, False, ROOT) for s in liste)}</ol>\n'
                     f'    <p><a href="{j}/">Alle Sitzungen {j} mit den beratenen Vorlagen</a></p>\n')
    return f"""    <h1>{TITEL}</h1>
    <p class="lead">{UNTERTITEL}. {mit} Sitzungen mit Video und automatisch erkanntem Transkript, {sum(1 for s in rat if s["video"])} von {len(rat)} Sitzungen des Rates.</p>
{_such_karte()}
    <nav class="thema-sprung" aria-labelledby="sprung-h"><h2 id="sprung-h">Auf dieser Seite</h2><p>{sprung} · <a href="#grenzen">Grenzen</a></p></nav>
{"".join(teile)}{GRENZEN}
{_quellen(stand, ROOT)}"""


def body_jahr(jahr, liste, stand):
    root = "../../"
    n = sum(1 for s in liste if s["video"])
    return f"""    <h1>{TITEL}: {jahr}</h1>
    <p class="lead">Sitzungen des Rates {jahr}: {n} mit Video und automatisch erkanntem Transkript. Je Sitzung die öffentlichen Vorlagen, die dort beraten wurden.</p>
    <p><a href="../">Alle Jahre</a></p>
{_such_karte()}
    <ol class="riv-liste">{"".join(_sitzung(s, True, root) for s in liste)}</ol>
{GRENZEN}
{_quellen(stand, root)}"""


def write(site, site_url, page):
    """Schreibt rat-im-video/index.html; gibt den Pfad für die Sitemap zurück (leer ohne Exportdaten)."""
    base = site / "data" / "export" / "bonn"
    if not (base / "zeit.json").exists() or not (base / "index.json").exists():
        return []
    index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    heute = (index.get("aktuell") or {}).get("heute") or "9999-12-31"
    sitzungen = daten(base, heute)
    stand = aufzeichnungen.stand()
    out = site / PFAD / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(site_url, PFAD, f"{TITEL}: Aufzeichnungen der Ratssitzungen – Ratsatlas Bonn",
                        f"{UNTERTITEL}: Video und Suche im Transkript je Sitzung des Rates der Stadt Bonn.",
                        body(sitzungen, stand), ROOT), encoding="utf-8")
    pfade = [PFAD]
    for jahr, liste in _jahre(sitzungen).items():
        pfad = f"{PFAD}{jahr}/"
        datei = site / pfad / "index.html"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(page(site_url, pfad, f"{TITEL} {jahr}: Ratssitzungen und beratene Vorlagen – Ratsatlas Bonn",
                              f"Sitzungen des Rates der Stadt Bonn {jahr}: Video, Suche im Transkript und die "
                              "beratenen Vorlagen.", body_jahr(jahr, liste, stand), "../../"), encoding="utf-8")
        pfade.append(pfad)
    return pfade
