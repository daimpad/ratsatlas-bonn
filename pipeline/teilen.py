"""Bilder zum Teilen und für die Pressearbeit (Seite teilen/; Entscheidungen des Auftraggebers 10.11.2026).

Mischung aus Grafiken aus den Daten und gestalteten Bildschirmfotos der Seite, wenig Text, je Motiv eine eigene
Farbwelt; Formate für soziale Medien, Präsentation, Web und Druck, Grafiken zusätzlich als SVG. Einmalig erzeugt und
im Repository abgelegt (site/teilen/bilder/), auf Knopfdruck neu: `python -m pipeline teilen-bilder` (braucht eine
laufende Vorschau der Seite unter TEILEN_SITE, Standard http://localhost:8765/, Node mit Playwright und Pillow).
Lizenz der Bilder CC BY 4.0 (Ratsatlas Bonn); Motive mit Karte oder Orten zusätzlich © OpenStreetMap-Mitwirkende.
"""
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from html import escape
from pathlib import Path

from . import config, topics

ZIEL = Path(__file__).resolve().parents[1] / "site" / "teilen" / "bilder"
MANIFEST = ZIEL.parent / "bilder.json"
SITE = os.environ.get("TEILEN_SITE", "http://localhost:8765/")
URL = "bonn.ratsatlas.de"
SCHRIFT = "Inter, 'Helvetica Neue', Arial, sans-serif"

# Format: (Breite, Höhe, Bezeichnung, Verwendung); Druck: Breite 3000 px
FORMATE = {
    "vorschau": (1200, 630, "Link-Vorschau", "Vorschaubild beim Teilen eines Links"),
    "quadrat": (1080, 1080, "Quadrat", "Beiträge in sozialen Medien"),
    "hoch": (1080, 1350, "Hochformat 4:5", "Beiträge in sozialen Medien"),
    "story": (1080, 1920, "Story 9:16", "Stories und Kurzvideos"),
    "breit": (1920, 1080, "Breitbild 16:9", "Präsentationen und Bildschirme"),
    "banner": (1500, 500, "Banner 3:1", "Kopfbild für Profile und Websites"),
}
DRUCK = ("breit", "quadrat", "hoch")       # zusätzlich 3000 px breit als JPG
DRUCK_BREITE = 3000

# Motive: Schlüssel, Titel, Zeile im Bild (kurz), Beschreibung für die Seite, Art, OSM-Nennung
MOTIVE = [
    ("marke", "Wortmarke", "Was Rat und Bezirksvertretungen beraten", "Logo und Name auf violettem Grund.", "svg", False),
    ("punkte", "Bonn in Punkten", "Wo beraten wird",
     "Jeder Punkt ist ein Ort, auf den sich eine Vorlage bezieht; dazu die vier Stadtbezirke.", "svg", True),
    ("themen", "Themen in Farbe", "Worum es geht",
     "Dieselben Orte, gefärbt nach dem Thema des federführenden Amtes.", "svg", True),
    ("flaechen", "Ortsteile", "Was im Viertel passiert",
     "Die 51 Ortsteile, je dunkler, desto mehr Vorlagen mit Ortsbezug seit 2019.", "svg", False),
    ("haushalt", "Haushalt", "Wofür das Geld da ist",
     "Die 17 Produktbereiche des städtischen Haushalts nach ihren geplanten Aufwendungen 2026.", "svg", False),
    ("prozess", "Prozesslinie", "Wie entschieden wird",
     "Der Weg einer Vorlage durch die Gremien, Station für Station.", "svg", False),
    ("karte", "Karte auf dem Telefon", "Bonn auf einen Blick",
     "Bildschirmfoto der Karte in einem Telefonrahmen.", "foto", True),
    ("themenseite", "Themenseite", "Themen im Überblick",
     "Bildschirmfoto der Themenseite „Verkehr und Mobilität“ in einem Browserrahmen.", "foto", True),
]

FARBEN = {  # Hintergrund 1, Hintergrund 2, Schrift, Akzent
    "marke": ("#7c3aed", "#a855f7", "#ffffff", "#ddd6fe"),
    "punkte": ("#0b1026", "#1e1347", "#ffffff", "#c4b5fd"),
    "themen": ("#fbf7f0", "#f3ece0", "#1f1a14", "#7c3aed"),
    "flaechen": ("#ecfdf5", "#d1fae5", "#06302b", "#0f766e"),
    "haushalt": ("#2a0f1f", "#4a1230", "#fff7ed", "#fdba74"),
    "prozess": ("#052e2b", "#064e3b", "#ecfdf5", "#34d399"),
    "karte": ("#ffe0f0", "#d4e4ff", "#0f0f14", "#7c3aed"),
    "themenseite": ("#1d4ed8", "#0891b2", "#ffffff", "#bae6fd"),
}
THEMENFARBEN = {"verkehr": "#2563eb", "bauen": "#d97706", "umwelt": "#16a34a", "bildung": "#db2777",
                "kinder": "#f43f5e", "soziales": "#9333ea", "kultur": "#0891b2", "wirtschaft": "#ca8a04",
                "sicherheit": "#475569", "beteiligung": "#7c3aed"}


# --- Daten ----------------------------------------------------------------------------------------------------------

def _lade_flaechen(name):
    return json.loads((config.ROOT / "data" / "geo" / name).read_text(encoding="utf-8"))["features"]


def _ringe(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [p[0] for p in geom["coordinates"]]


class Projektion:
    """Flächentreue genügt nicht; einfache Abbildung mit cos(Breite), eingepasst in ein Rechteck."""

    def __init__(self, bezirke, x, y, b, h):
        pts = [pt for f in bezirke for r in _ringe(f["geometry"]) for pt in r]
        self.lon0, self.lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
        self.lat0, self.lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
        k = math.cos(math.radians((self.lat0 + self.lat1) / 2))
        bw, bh = (self.lon1 - self.lon0) * k, self.lat1 - self.lat0
        s = min(b / bw, h / bh)
        self.k, self.s = k, s
        self.ox, self.oy = x + (b - bw * s) / 2, y + (h - bh * s) / 2

    def __call__(self, lon, lat):
        return self.ox + (lon - self.lon0) * self.k * self.s, self.oy + (self.lat1 - lat) * self.s


def _pfad(ringe, proj):
    teile = []
    for r in ringe:
        pts, letzter = [], None
        for lon, lat in r:
            p = tuple(round(v) for v in proj(lon, lat))
            if p != letzter:
                pts.append(p)
                letzter = p
        if len(pts) > 2:
            teile.append("M" + "L".join(f"{a},{b}" for a, b in pts) + "Z")
    return "".join(teile)


def daten():
    geo = json.loads((config.EXPORT / "bonn" / "vorlagen.geojson").read_text(encoding="utf-8"))["features"]
    punkte = []
    for f in geo:
        lon, lat = f["geometry"]["coordinates"]
        amt = (f["properties"].get("amt") or "")[:2]
        punkte.append((lon, lat, topics.AMT.get(amt), f["properties"].get("ortsteil")))
    haushalt = {}
    with open(config.ROOT / "data" / "haushalt" / "produktbereiche.tsv", encoding="utf-8") as fh:
        next(fh)
        for zeile in fh:
            a = zeile.rstrip("\n").split("\t")
            if a[0] == "2025/2026" and a[3] == "17" and a[5] == "2026" and a[6] == "Ansatz":
                haushalt[a[1]] = (a[2], abs(float(a[7])))
    vorgang = None
    for f in sorted((config.EXPORT / "bonn").glob("*/*.json")):
        if f.parent.name not in ("bezirke", "ortsteile", "ohne-ortsbezug") or vorgang:
            continue
        for p in json.loads(f.read_text(encoding="utf-8")).get("papers") or []:
            if p.get("reference") == "252458":
                vorgang = p
    return {"punkte": punkte, "bezirke": _lade_flaechen("stadtbezirke_bonn.geojson"),
            "ortsteile": _lade_flaechen("ortsteile_bonn.geojson"), "haushalt": haushalt,
            "schritte": [s for s in (vorgang or {}).get("steps") or [] if s.get("typ") != "soll"]}


# --- Bausteine ------------------------------------------------------------------------------------------------------

def _logo(x, y, s, hell=False):
    inhalt = (config.ROOT / "site" / "favicon.svg").read_text(encoding="utf-8")
    inhalt = re.sub(r"<!--.*?-->", "", inhalt, flags=re.S)
    inhalt = re.sub(r"^<svg[^>]*>", "", inhalt.strip()).replace("</svg>", "").replace('id="ra-bg"', 'id="ra-bg-t"') \
        .replace("url(#ra-bg)", "url(#ra-bg-t)")
    grund = (f'<rect x="{x - s * 0.08:.0f}" y="{y - s * 0.08:.0f}" width="{s * 1.16:.0f}" height="{s * 1.16:.0f}" '
             f'rx="{s * 0.3:.0f}" fill="#ffffff" opacity="0.92"/>') if hell else ""
    return grund + f'<svg x="{x:.0f}" y="{y:.0f}" width="{s:.0f}" height="{s:.0f}" viewBox="0 0 100 100">{inhalt}</svg>'


def _marke(x, y, s, farbe, ort_farbe, url=True, ausrichtung="start", hell=False):
    """Logo, „Ratsatlas Bonn“ und Adresse; s = Schriftgröße des Namens."""
    lg = s * 1.5
    anker = "start" if ausrichtung == "start" else "middle"
    if ausrichtung == "start":
        teile = [_logo(x, y - lg * 0.78, lg, hell),
                 f'<text x="{x + lg * 1.25:.0f}" y="{y:.0f}" font-size="{s:.0f}" font-weight="800" fill="{farbe}" '
                 f'letter-spacing="-0.02em">Ratsatlas <tspan font-weight="600" fill="{ort_farbe}">Bonn</tspan></text>']
        if url:
            teile.append(f'<text x="{x:.0f}" y="{y + s * 1.6:.0f}" font-size="{s * 0.55:.0f}" font-weight="500" '
                         f'fill="{ort_farbe}" opacity="0.85">{URL}</text>')
    else:
        teile = [_logo(x - lg / 2, y - lg * 2.1, lg, hell),
                 f'<text x="{x:.0f}" y="{y:.0f}" font-size="{s:.0f}" font-weight="800" fill="{farbe}" '
                 f'text-anchor="{anker}" letter-spacing="-0.02em">Ratsatlas <tspan font-weight="600" '
                 f'fill="{ort_farbe}">Bonn</tspan></text>']
        if url:
            teile.append(f'<text x="{x:.0f}" y="{y + s * 1.6:.0f}" font-size="{s * 0.55:.0f}" font-weight="500" '
                         f'fill="{ort_farbe}" text-anchor="middle" opacity="0.85">{URL}</text>')
    return "".join(teile)


def _zeile(x, y, s, text, farbe, anker="start"):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{s:.0f}" font-weight="700" fill="{farbe}" '
            f'text-anchor="{anker}" letter-spacing="-0.02em">{escape(text)}</text>')


def _rahmen(w, h, key, inhalt):
    a, b, _, _ = FARBEN[key]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{SCHRIFT}"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
            f'<rect width="{w}" height="{h}" fill="url(#bg)"/>{inhalt}</svg>')


def _flaeche_und_text(w, h):
    """Bildfläche (x, y, b, h) und Ort des Textes je nach Seitenverhältnis."""
    r = w / h
    rand = min(w, h) * 0.07
    if r >= 2.5:      # Banner: Grafik rechts, Text links
        return (w * 0.42, rand * 0.6, w * 0.58 - rand * 0.6, h - rand * 1.2), ("links", rand, h / 2)
    if r >= 1.3:      # quer
        return (w * 0.40, rand, w * 0.60 - rand, h - 2 * rand), ("links", rand, h / 2)
    return (rand, rand, w - 2 * rand, h * 0.70 - rand), ("unten", rand, h * 0.70)


def _text_block(w, h, key, zeile, pos):
    _, _, schrift, akzent = FARBEN[key]
    art, x, y = pos
    s = min(w, h) * (0.058 if w / h >= 2.5 else 0.05)
    if art == "links":
        groesse = min(s * 1.25, (w * 0.36) / max(len(zeile), 8) * 1.9)
        return (_zeile(x, y - s * 0.6, groesse, zeile, schrift)
                + _marke(x, y + s * 1.6, s * 0.75, schrift, akzent))
    groesse = min(s * 1.5, (w * 0.86) / max(len(zeile), 8) * 1.9)
    return (_zeile(x, y + s * 1.6, groesse, zeile, schrift)
            + _marke(x, h - s * 2.2, s * 0.8, schrift, akzent))


def _osm(w, h, farbe):
    return (f'<text x="{w - 14}" y="{h - 12}" font-size="{max(11, min(w, h) * 0.014):.0f}" fill="{farbe}" '
            f'opacity="0.7" text-anchor="end">Daten: Stadt Bonn · © OpenStreetMap-Mitwirkende</text>')


# --- Motive aus Daten -----------------------------------------------------------------------------------------------

def motiv_marke(w, h, d):
    _, _, schrift, akzent = FARBEN["marke"]
    s = min(w, h) * (0.13 if w / h < 2.5 else 0.16)
    kreise = "".join(f'<circle cx="{w * cx:.0f}" cy="{h * cy:.0f}" r="{min(w, h) * r:.0f}" fill="#ffffff" '
                     f'opacity="{o}"/>' for cx, cy, r, o in ((0.9, 0.1, 0.35, 0.08), (0.08, 0.95, 0.28, 0.07),
                                                              (0.75, 0.85, 0.12, 0.1)))
    if w / h >= 1.3:
        x, y = w * 0.1, h * 0.52
        return _rahmen(w, h, "marke", kreise + _marke(x, y, s * 0.62, schrift, akzent, hell=True)
                       + f'<text x="{x:.0f}" y="{y + s * 0.62 * 2.6:.0f}" font-size="{s * 0.24:.0f}" '
                         f'fill="{akzent}">Was Rat und Bezirksvertretungen beraten</text>')
    return _rahmen(w, h, "marke", kreise + _marke(w / 2, h * 0.55, s * 0.62, schrift, akzent, ausrichtung="mitte", hell=True)
                   + f'<text x="{w / 2:.0f}" y="{h * 0.55 + s * 0.62 * 2.8:.0f}" font-size="{s * 0.26:.0f}" '
                     f'fill="{akzent}" text-anchor="middle">Was Rat und Bezirksvertretungen beraten</text>')


def _karte(w, h, d, key, faerben, linien="#4c4a7a", flaechen_fill="none"):
    (fx, fy, fb, fh), pos = _flaeche_und_text(w, h)
    proj = Projektion(d["bezirke"], fx, fy, fb, fh)
    grenzen = "".join(f'<path d="{_pfad(_ringe(f["geometry"]), proj)}" fill="{flaechen_fill}" stroke="{linien}" '
                      f'stroke-width="{max(1, fb / 600):.1f}" stroke-linejoin="round"/>' for f in d["bezirke"])
    r = max(1.2, fb / 520)
    punkte = faerben(proj, r)
    return pos, grenzen + punkte


def motiv_punkte(w, h, d):
    def faerben(proj, r):
        gesehen, out = set(), []
        for lon, lat, _, _ in d["punkte"]:
            x, y = proj(lon, lat)
            k = (round(x), round(y))
            if k in gesehen:
                continue
            gesehen.add(k)
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}"/>')
        return f'<g fill="#c4b5fd" opacity="0.75">{"".join(out)}</g>'
    pos, karte = _karte(w, h, d, "punkte", faerben)
    glanz = f'<radialGradient id="gl"><stop offset="0" stop-color="#7c3aed" stop-opacity="0.35"/><stop offset="1" stop-color="#7c3aed" stop-opacity="0"/></radialGradient>'
    (fx, fy, fb, fh), _ = _flaeche_und_text(w, h)
    return _rahmen(w, h, "punkte", f'<defs>{glanz}</defs><ellipse cx="{fx + fb / 2:.0f}" cy="{fy + fh / 2:.0f}" '
                                   f'rx="{fb * 0.55:.0f}" ry="{fh * 0.55:.0f}" fill="url(#gl)"/>' + karte
                   + _text_block(w, h, "punkte", "Wo beraten wird", pos) + _osm(w, h, "#c4b5fd"))


def motiv_themen(w, h, d):
    def faerben(proj, r):
        gruppen, gesehen = {}, set()
        for lon, lat, thema, _ in d["punkte"]:
            if not thema:
                continue
            x, y = proj(lon, lat)
            k = (round(x / 2), round(y / 2))
            if k in gesehen:
                continue
            gesehen.add(k)
            gruppen.setdefault(thema, []).append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r * 1.15:.1f}"/>')
        return "".join(f'<g fill="{THEMENFARBEN[t]}" opacity="0.85">{"".join(c)}</g>' for t, c in sorted(gruppen.items()))
    pos, karte = _karte(w, h, d, "themen", faerben, linien="#d6cbb8")
    return _rahmen(w, h, "themen", karte + _text_block(w, h, "themen", "Worum es geht", pos) + _osm(w, h, "#6b6255"))


def motiv_flaechen(w, h, d):
    (fx, fy, fb, fh), pos = _flaeche_und_text(w, h)
    proj = Projektion(d["bezirke"], fx, fy, fb, fh)
    zahl = Counter(o for *_, o in d["punkte"] if o)
    hoch = max(zahl.values()) if zahl else 1
    stufen = ["#ccfbf1", "#99f6e4", "#5eead4", "#2dd4bf", "#14b8a6", "#0d9488", "#0f766e"]
    teile = []
    for f in d["ortsteile"]:
        n = zahl.get(f["properties"].get("ortsteil_bez") or f["properties"].get("ortsteil"), 0)
        stufe = stufen[min(len(stufen) - 1, int(math.sqrt(n / hoch) * len(stufen)))]
        teile.append(f'<path d="{_pfad(_ringe(f["geometry"]), proj)}" fill="{stufe}" stroke="#ffffff" '
                     f'stroke-width="{max(1.2, fb / 450):.1f}" stroke-linejoin="round"/>')
    return _rahmen(w, h, "flaechen", "".join(teile) + _text_block(w, h, "flaechen", "Was im Viertel passiert", pos))


def _squarify(werte, x, y, b, h):
    """Treemap (Bruls, Huizing, van Wijk 2000): Rechtecke in Reihen mit möglichst quadratischen Seiten."""
    werte = sorted(werte, key=lambda kv: -kv[1])
    summe = sum(v for _, v in werte) or 1
    flaeche = [(k, v / summe * b * h) for k, v in werte]
    out = []

    def worst(reihe, seite):
        s = sum(a for _, a in reihe)
        return max(max(seite * seite * a / (s * s), (s * s) / (seite * seite * a)) for _, a in reihe)

    while flaeche:
        seite = min(b, h)
        reihe = [flaeche.pop(0)]
        while flaeche and worst(reihe + [flaeche[0]], seite) <= worst(reihe, seite):
            reihe.append(flaeche.pop(0))
        s = sum(a for _, a in reihe)
        if b >= h:
            dicke, yy = s / h, y
            for k, a in reihe:
                out.append((k, x, yy, dicke, a / dicke))
                yy += a / dicke
            x, b = x + dicke, b - dicke
        else:
            dicke, xx = s / b, x
            for k, a in reihe:
                out.append((k, xx, y, a / dicke, dicke))
                xx += a / dicke
            y, h = y + dicke, h - dicke
    return out


def motiv_haushalt(w, h, d):
    (fx, fy, fb, fh), pos = _flaeche_und_text(w, h)
    farben = ["#fdba74", "#fb923c", "#f97316", "#fca5a5", "#f87171", "#fb7185", "#f43f5e", "#fda4af", "#fcd34d",
              "#fbbf24", "#f59e0b", "#fecaca", "#fed7aa", "#e11d48", "#ea580c", "#fde68a", "#fb7185"]
    rects = _squarify([(k, v[1]) for k, v in d["haushalt"].items()], fx, fy, fb, fh)
    spalt = max(2, fb / 300)
    teile = "".join(f'<rect x="{x + spalt / 2:.1f}" y="{y + spalt / 2:.1f}" width="{max(0, b - spalt):.1f}" '
                    f'height="{max(0, hh - spalt):.1f}" rx="{spalt * 1.5:.1f}" fill="{farben[i % len(farben)]}"/>'
                    for i, (k, x, y, b, hh) in enumerate(rects))
    return _rahmen(w, h, "haushalt", teile + _text_block(w, h, "haushalt", "Wofür das Geld da ist", pos))


def motiv_prozess(w, h, d):
    """Alle Stationen einer echten Prozesslinie (252458) als Wellenlinie: Entscheidungen groß und gefüllt,
    Beratungen als Ring, Folgevorlagen als Raute, Sitzungen mit Aufzeichnung mit hellem Kern."""
    (fx, fy, fb, fh), pos = _flaeche_und_text(w, h)
    schritte = d["schritte"] or [{"typ": "beratung"}] * 12
    n = len(schritte)
    quer = fb >= fh
    lang, kurz = (fb, fh) if quer else (fh, fb)
    r0 = min(lang / n * 0.42, kurz * 0.12)
    welle = kurz * 0.22

    def ort(i):
        t = (i + 0.5) / n
        v = math.sin(t * math.pi * 2.2) * welle
        return (fx + fb * t, fy + fh / 2 + v) if quer else (fx + fb / 2 + v, fy + fh * t)
    punkte = [ort(i) for i in range(n)]
    linie = "M" + "L".join(f"{x:.0f},{y:.0f}" for x, y in punkte)
    teile = [f'<path d="{linie}" fill="none" stroke="#34d399" stroke-width="{max(4, r0 * 0.3):.0f}" '
             f'stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>']
    for (x, y), s in zip(punkte, schritte):
        typ = s.get("typ")
        rand = f'stroke="#34d399" stroke-width="{max(3, r0 * 0.18):.0f}"'
        if typ == "entscheidung":
            teile.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r0 * 1.5:.0f}" fill="#34d399" {rand}/>')
        elif typ == "folgevorlage":
            q = r0 * 0.75
            teile.append(f'<rect x="{x - q:.0f}" y="{y - q:.0f}" width="{2 * q:.0f}" height="{2 * q:.0f}" '
                         f'transform="rotate(45 {x:.0f} {y:.0f})" fill="#a7f3d0" {rand}/>')
        elif typ in ("initiierung", "vorbereitung", "veroeffentlichung"):
            teile.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r0 * 0.6:.0f}" fill="#6ee7b7"/>')
        elif typ == "vollzug":
            teile.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r0 * 1.2:.0f}" fill="none" {rand} '
                         f'stroke-dasharray="{r0 * 0.5:.0f} {r0 * 0.35:.0f}"/>')
        else:
            teile.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r0:.0f}" fill="#052e2b" {rand}/>')
        if s.get("aufzeichnung"):
            teile.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r0 * 0.5:.0f}" fill="#ecfdf5"/>')
    return _rahmen(w, h, "prozess", "".join(teile) + _text_block(w, h, "prozess", "Wie entschieden wird", pos))


# --- Motive mit Bildschirmfotos -------------------------------------------------------------------------------------

def _foto_motiv(w, h, key, bild, art):
    """Telefon- oder Browserrahmen mit Bildschirmfoto; bild = Dateiname im Arbeitsordner."""
    (fx, fy, fb, fh), pos = _flaeche_und_text(w, h)
    teile = []
    if art == "telefon":
        ph = min(fh, fb * 2.05)
        pb = ph / 2.05
        x, y = fx + (fb - pb) / 2, fy + (fh - ph) / 2
        rad = pb * 0.12
        teile.append(f'<rect x="{x - pb * 0.04:.0f}" y="{y - pb * 0.04:.0f}" width="{pb * 1.08:.0f}" height="{ph + pb * 0.08:.0f}" '
                     f'rx="{rad * 1.15:.0f}" fill="#111118"/>')
        teile.append(f'<clipPath id="cl"><rect x="{x:.0f}" y="{y:.0f}" width="{pb:.0f}" height="{ph:.0f}" rx="{rad:.0f}"/></clipPath>')
        teile.append(f'<image href="{bild}" x="{x:.0f}" y="{y:.0f}" width="{pb:.0f}" height="{ph:.0f}" '
                     f'preserveAspectRatio="xMidYMin slice" clip-path="url(#cl)"/>')
    else:
        bb = fb
        bh = min(fh, bb * 0.66)
        x, y = fx, fy + (fh - bh) / 2
        leiste = max(18, bh * 0.06)
        teile.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bb:.0f}" height="{bh:.0f}" rx="{leiste * 0.6:.0f}" '
                     f'fill="#ffffff"/>')
        for i, c in enumerate(("#f87171", "#fbbf24", "#34d399")):
            teile.append(f'<circle cx="{x + leiste * (0.8 + i * 0.75):.0f}" cy="{y + leiste / 2:.0f}" '
                         f'r="{leiste * 0.18:.0f}" fill="{c}"/>')
        teile.append(f'<clipPath id="cl"><rect x="{x:.0f}" y="{y + leiste:.0f}" width="{bb:.0f}" height="{bh - leiste:.0f}" '
                     f'rx="{leiste * 0.4:.0f}"/></clipPath>')
        teile.append(f'<image href="{bild}" x="{x:.0f}" y="{y + leiste:.0f}" width="{bb:.0f}" height="{bh - leiste:.0f}" '
                     f'preserveAspectRatio="xMidYMin slice" clip-path="url(#cl)"/>')
    titel = dict((m[0], m[2]) for m in MOTIVE)[key]
    return _rahmen(w, h, key, "".join(teile) + _text_block(w, h, key, titel, pos)
                   + _osm(w, h, FARBEN[key][2]))


ERZEUGER = {"marke": motiv_marke, "punkte": motiv_punkte, "themen": motiv_themen, "flaechen": motiv_flaechen,
            "haushalt": motiv_haushalt, "prozess": motiv_prozess}
FOTOS = {"karte": ("telefon", "?gebiet=ortsteil:endenich", 390, 844),
         "themenseite": ("browser", "thema/verkehr-und-mobilitaet/", 1100, 760)}


# --- Erzeugen -------------------------------------------------------------------------------------------------------

def _html(svg):
    schrift = (config.ROOT / "site" / "fonts" / "inter-latin-wght-normal.woff2").as_uri()
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>@font-face{{font-family:Inter;'
            f'src:url("{schrift}") format("woff2");font-weight:100 900}}html,body{{margin:0;padding:0}}'
            f'svg{{display:block}}</style></head><body>{svg}</body></html>')


def bilder():
    """Alle Motive in allen Formaten erzeugen und site/teilen/bilder.json schreiben (auf Knopfdruck)."""
    from PIL import Image
    d = daten()
    arbeit = Path(tempfile.mkdtemp(prefix="teilen-"))
    auftraege = {"site": SITE, "fotos": [], "seiten": []}
    for key, (art, pfad, vb, vh) in FOTOS.items():
        auftraege["fotos"].append({"datei": str(arbeit / f"foto-{key}.png"), "url": SITE + pfad, "w": vb, "h": vh})
    for key, *_rest, art, _osm_ in MOTIVE:
        for fmt, (w, h, *_x) in FORMATE.items():
            svg = (ERZEUGER[key](w, h, d) if art == "svg"
                   else _foto_motiv(w, h, key, (arbeit / f"foto-{key}.png").as_uri(), FOTOS[key][0]))
            (arbeit / f"{key}-{fmt}.html").write_text(_html(svg), encoding="utf-8")
            if art == "svg":
                (arbeit / f"{key}-{fmt}.svg").write_text(svg, encoding="utf-8")
            auftraege["seiten"].append({"name": f"{key}-{fmt}", "html": str(arbeit / f"{key}-{fmt}.html"), "w": w, "h": h,
                                        "druck": DRUCK_BREITE / w if fmt in DRUCK else None})
    (arbeit / "auftraege.json").write_text(json.dumps(auftraege), encoding="utf-8")
    subprocess.run(["node", str(Path(__file__).with_name("teilen_render.mjs")), str(arbeit)], check=True)
    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    ZIEL.mkdir(parents=True)
    manifest = {"formate": {k: {"w": v[0], "h": v[1], "name": v[2], "zweck": v[3]} for k, v in FORMATE.items()},
                "druck_breite": DRUCK_BREITE, "stand": __import__("datetime").date.today().isoformat(), "motive": []}
    for key, titel, zeile, text, art, osm in MOTIVE:
        eintrag = {"key": key, "titel": titel, "zeile": zeile, "text": text, "osm": osm, "dateien": {}}
        for fmt in FORMATE:
            name = f"{key}-{fmt}"
            bild = Image.open(arbeit / f"{name}.png").convert("RGB")
            dateien = {}
            bild.save(ZIEL / f"{name}.jpg", "JPEG", quality=86, optimize=True, progressive=True)
            bild.save(ZIEL / f"{name}.webp", "WEBP", quality=82, method=6)
            dateien["jpg"], dateien["webp"] = f"{name}.jpg", f"{name}.webp"
            if key == "marke":
                shutil.copy(arbeit / f"{name}.png", ZIEL / f"{name}.png")
                dateien["png"] = f"{name}.png"
            if art == "svg":
                shutil.copy(arbeit / f"{name}.svg", ZIEL / f"{name}.svg")
                dateien["svg"] = f"{name}.svg"
            if fmt in DRUCK:
                Image.open(arbeit / f"{name}-druck.png").convert("RGB").save(
                    ZIEL / f"{name}-druck.jpg", "JPEG", quality=88, optimize=True, progressive=True)
                dateien["druck"] = f"{name}-druck.jpg"
            eintrag["dateien"][fmt] = {k: {"datei": v, "bytes": (ZIEL / v).stat().st_size} for k, v in dateien.items()}
        manifest["motive"].append(eintrag)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shutil.rmtree(arbeit, ignore_errors=True)
    gesamt = sum(f.stat().st_size for f in ZIEL.iterdir())
    print(f"Bilder zum Teilen: {len(MOTIVE)} Motive, {len(list(ZIEL.iterdir()))} Dateien, {gesamt / 1e6:.1f} MB → {ZIEL}")
