"""Zu- und Wegzüge für ganz Bonn (Entscheidungen des Auftraggebers 24.11.2026, Bericht wanderung/phase0/BERICHT.md):
eigene Seite zu-und-wegzuege/ mit öffentlichen Daten; kleinräumige Zahlen erst mit der Lieferung der Statistikstelle.

Schritt `wanderung` (auf Knopfdruck, einmal im Jahr) legt unter data/wanderung/ ab:
- partner_2025.tsv – Zu- und Fortzüge Bonns mit jedem Kreis in Deutschland 2025 (Kreiswanderungsmatrix der Statistischen
  Ämter des Bundes und der Länder, dl-de/by-2.0; Bonn = Kreis 05314; unverändert übernommen, leer = geheim gehalten)
- alter_2025.tsv – Summe über alle Kreise je Altersgruppe (abgeleitet: Summe der veröffentlichten Zellen)
- zeitreihe.tsv – Zuzüge, Fortzüge, Saldo, Bildungs- und Familienwanderung je 1.000 Einwohner, gleitendes Mittel über
  vier Jahre (Wegweiser Kommune, Bertelsmann Stiftung, CC0)
- kreise_region.geojson – Kreise in NRW und Rheinland-Pfalz, vereinfacht (VG2500, © BKG, dl-de/by-2.0)
- STAND.json – Abrufzeitpunkte und Adressen
Die Matrix für ganz Deutschland wird nicht abgelegt. Die Seite entsteht im Schritt `seo` aus diesen Dateien; Grafiken
als SVG mit Tabelle als Alternative. Melderegister der Stadt und amtliche Statistik werden nicht gemischt.
Keine Erzeugungszeitpunkte auf der Seite (stabile Ausgabe)."""
import csv
import io
import json
import math
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from . import config

PFAD = "zu-und-wegzuege/"
ORDNER = config.ROOT / "data" / "wanderung"
BONN = "5314"
KWM = "https://www.statistikportal.de/sites/default/files/2026-10/KWM_GES_NAT_ALT_2025.zip"
KWM_SEITE = "https://www.statistikportal.de/de/veroeffentlichungen/kreiswanderungsmatrix"
VG = "https://daten.gdz.bkg.bund.de/produkte/vg/vg2500/aktuell/vg2500_12-31.utm32s.shape.zip"
WW = "https://www.wegweiser-kommune.de/data-api/rest/statistics/data/{fu}+bonn+2006-2023"
WW_INDIKATOREN = {"zuzuege": "Zuzüge", "fortzuege": "Fortzüge", "wanderungssaldo": "Saldo",
                  "bildungswanderung": "Bildungswanderung (18 bis unter 25 Jahre)",
                  "familienwanderung": "Familienwanderung (unter 18 und 30 bis unter 50 Jahre)"}
STADT_BERICHT = ("https://www.bonn.de/themen-entdecken/wirtschaft-wissenschaft/jahreswirtschaftsbericht-2026/"
                 "standortentwicklung/demographische-entwicklung.php")
ALTER = ["unter 18 Jahre", "18 bis unter 25 Jahre", "25 bis unter 30 Jahre", "30 bis unter 50 Jahre",
         "50 bis unter 65 Jahre", "65 Jahre und älter"]
LAENDER = ("05", "07")   # Regionalkarte: NRW und Rheinland-Pfalz
TOP = 15
ZUZUG, FORTZUG = "#0f766e", "#6d28d9"   # Farben wie „Aktuell in Bonn“; Kontrast ≥ 4,5:1 auf Weiß


# --- Daten -----------------------------------------------------------------------------------------------------

def _zahl(x):
    return int(x) if str(x or "").strip() not in ("", "-") else None


def auszug_matrix(zeilen, kreis=BONN):
    """Aus den Zeilen der Kreiswanderungsmatrix (dicts) die Partner von `kreis` (Altersgruppe insgesamt) und die
    Summen je Altersgruppe. zuzug/fortzug beziehen sich auf den Zielkreis; Bonn steht als Zielkreis."""
    partner, alter = [], {a: [0, 0] for a in ALTER}
    for r in zeilen:
        if r["zielkreis_ags"].lstrip("0") != kreis:
            continue
        z, f = _zahl(r["zuzug_ins_i"]), _zahl(r["fortzug_ins_i"])
        if r["alter"] == "insgesamt":
            partner.append({"ags": r["herkunftskreis_ags"].zfill(5), "kreis": r["herkunftskreis"],
                            "land": r["herkunftsland"], "zuzuege": z, "fortzuege": f, "saldo": _zahl(r["saldo_ins_i"])})
        elif r["alter"] in alter:
            alter[r["alter"]][0] += z or 0
            alter[r["alter"]][1] += f or 0
    partner.sort(key=lambda p: (-((p["zuzuege"] or 0) + (p["fortzuege"] or 0)), p["ags"]))
    return partner, [{"alter": a, "zuzuege": z, "fortzuege": f, "saldo": z - f} for a, (z, f) in alter.items()]


def zeitreihe_aus_wegweiser(antwort):
    """[(jahr, wert)] aus einer Antwort von statistics/data (eine Kommune, ein Indikator)."""
    d = antwort["data"]["indicators"][0]
    jahre = antwort["years"]
    return [(j, w) for j, w in zip(jahre, d["regionYearValues"][0]) if w is not None]


def _hole(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _tsv(pfad, felder, zeilen):
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, felder, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for z in zeilen:
            w.writerow({k: "" if z.get(k) is None else z[k] for k in felder})


def kreise_region(shp_zip):
    """Kreise in NRW und Rheinland-Pfalz aus VG2500 (UTM32), in WGS84 und vereinfacht, als GeoJSON-dict."""
    import shapefile
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
    t = Transformer.from_crs(25832, 4326, always_xy=True).transform
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(io.BytesIO(shp_zip)).extractall(tmp)
        shp = next(Path(tmp).rglob("VG2500_KRS.shp"))
        r = shapefile.Reader(str(shp))
        felder = [f[0] for f in r.fields[1:]]
        out = []
        for s in r.iterShapeRecords():
            rec = dict(zip(felder, s.record))
            if rec["SN_L"] not in LAENDER:
                continue
            g = transform(t, shape(s.shape.__geo_interface__)).simplify(0.004, preserve_topology=True)
            geo = json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), 4))
            out.append({"type": "Feature", "properties": {"ags": rec["AGS"], "name": rec["GEN"], "art": rec["BEZ"]},
                        "geometry": geo})
    out.sort(key=lambda f: f["properties"]["ags"])
    return {"type": "FeatureCollection", "features": out}


def ausschnitt(ordner=ORDNER, hole=_hole):
    """Schritt `wanderung`: Quellen laden und die Auszüge für Bonn ablegen."""
    ordner.mkdir(parents=True, exist_ok=True)
    zeit = datetime.now(timezone.utc).isoformat(timespec="seconds")
    z = zipfile.ZipFile(io.BytesIO(hole(KWM)))
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    zeilen = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"), delimiter=";")
    partner, alter = auszug_matrix(zeilen)
    if len(partner) < 300:
        raise SystemExit(f"Kreiswanderungsmatrix: nur {len(partner)} Partnerkreise für Bonn, erwartet rund 380")
    _tsv(ordner / "partner_2025.tsv", ["ags", "kreis", "land", "zuzuege", "fortzuege", "saldo"], partner)
    _tsv(ordner / "alter_2025.tsv", ["alter", "zuzuege", "fortzuege", "saldo"], alter)
    reihe = []
    for fu, label in WW_INDIKATOREN.items():
        for jahr, wert in zeitreihe_aus_wegweiser(json.loads(hole(WW.format(fu=fu)))):
            reihe.append({"indikator": fu, "bezeichnung": label, "jahr": jahr, "wert": wert})
    _tsv(ordner / "zeitreihe.tsv", ["indikator", "bezeichnung", "jahr", "wert"], reihe)
    (ordner / "kreise_region.geojson").write_text(json.dumps(kreise_region(hole(VG)), ensure_ascii=False,
                                                             separators=(",", ":")), encoding="utf-8")
    (ordner / "STAND.json").write_text(json.dumps({
        "abruf": zeit, "kreiswanderungsmatrix": {"url": KWM, "seite": KWM_SEITE, "berichtsjahr": 2025, "datei": name},
        "wegweiser": {"url": WW.format(fu="…"), "jahre": "2006–2023"}, "vg2500": {"url": VG}},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wanderung: {len(partner)} Partnerkreise, {len(reihe)} Werte der Zeitreihe → {ordner}")


def lesen(ordner=ORDNER):
    """Auszüge für die Seite oder None, solange der Schritt `wanderung` nicht gelaufen ist."""
    if not (ordner / "partner_2025.tsv").exists():
        return None
    def tsv(n):
        with open(ordner / n, encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    partner = [{**p, **{k: _zahl(p[k]) for k in ("zuzuege", "fortzuege", "saldo")}} for p in tsv("partner_2025.tsv")]
    alter = [{**a, **{k: int(a[k]) for k in ("zuzuege", "fortzuege", "saldo")}} for a in tsv("alter_2025.tsv")]
    reihe = {}
    for r in tsv("zeitreihe.tsv"):
        reihe.setdefault(r["indikator"], []).append((int(r["jahr"]), float(r["wert"])))
    return {"partner": partner, "alter": alter, "reihe": reihe,
            "kreise": json.loads((ordner / "kreise_region.geojson").read_text(encoding="utf-8")),
            "stand": json.loads((ordner / "STAND.json").read_text(encoding="utf-8"))}


# --- Seite -----------------------------------------------------------------------------------------------------

def _n(x):
    return "–" if x is None else f"{x:,}".replace(",", ".")


def _s(x):
    if x is None:
        return "–"
    return ("+" if x > 0 else "−" if x < 0 else "±") + _n(abs(x))


def _kurz(name):
    return name.replace(", Kreisfreie Stadt", "").replace(", Landkreis", " (Landkreis)")


def _summen(d):
    z = sum(p["zuzuege"] or 0 for p in d["partner"])
    f = sum(p["fortzuege"] or 0 for p in d["partner"])
    return z, f, z - f


def _beide(fn, *args):
    """Grafik breit (ab 600 px) und schmal (Telefon), damit die Schrift lesbar bleibt; je eine ist ausgeblendet."""
    return (f'<div class="wz-breit">{fn(*args, b=720, sfx="b")}</div>'
            f'<div class="wz-schmal">{fn(*args, b=360, sfx="s")}</div>')


def balken_partner(partner, b=720, sfx="b"):
    """Zuzüge und Fortzüge der größten Partnerkreise als waagerechte Balkenpaare (SVG)."""
    top = partner[:TOP]
    m = max(max(p["zuzuege"] or 0, p["fortzuege"] or 0) for p in top)
    l, zh = (190 if b > 500 else 168), 34
    w = b - l - (120 if b > 500 else 88)
    zeilen = []
    for i, p in enumerate(top):
        y = 30 + i * zh
        wz, wf = (p["zuzuege"] or 0) / m * w, (p["fortzuege"] or 0) / m * w
        zeilen.append(
            f'<g><title>{escape(_kurz(p["kreis"]))}: {_n(p["zuzuege"])} Zuzüge nach Bonn, {_n(p["fortzuege"])} Fortzüge aus Bonn, Saldo {_s(p["saldo"])}</title>'
            f'<text x="{l - 8}" y="{y + 15}" text-anchor="end" class="wz-l">{escape(_kurz(p["kreis"]))}</text>'
            f'<rect x="{l}" y="{y + 2}" width="{wz:.1f}" height="11" rx="2" fill="{ZUZUG}"/>'
            f'<text x="{l + wz + 5:.1f}" y="{y + 12}" class="wz-z">{_n(p["zuzuege"])}</text>'
            f'<rect x="{l}" y="{y + 16}" width="{wf:.1f}" height="11" rx="2" fill="{FORTZUG}"/>'
            f'<text x="{l + wf + 5:.1f}" y="{y + 26}" class="wz-z">{_n(p["fortzuege"])}</text>'
            f'<text x="{b - 4}" y="{y + 20}" text-anchor="end" class="wz-s">{_s(p["saldo"])}</text></g>')
    h = 30 + TOP * zh + 6
    x0 = l if b > 500 else 6
    kopf = (f'<rect x="{x0}" y="8" width="12" height="10" rx="2" fill="{ZUZUG}"/><text x="{x0 + 17}" y="17" class="wz-k">Zuzüge nach Bonn</text>'
            f'<rect x="{x0 + 135}" y="8" width="12" height="10" rx="2" fill="{FORTZUG}"/><text x="{x0 + 152}" y="17" class="wz-k">Fortzüge aus Bonn</text>'
            f'<text x="{b - 4}" y="17" text-anchor="end" class="wz-k">Saldo</text>')
    return (f'<svg class="wz-svg" viewBox="0 0 {b} {h}" role="img" aria-labelledby="wz-partner-t{sfx}">'
            f'<title id="wz-partner-t{sfx}">Zu- und Fortzüge zwischen Bonn und den {TOP} Kreisen mit dem größten Austausch, 2025</title>'
            f'{kopf}{"".join(zeilen)}</svg>')


def _klasse(saldo):
    if saldo is None:
        return "#fafafa", "kein Austausch oder geheim"
    for grenze, farbe, text in ((-500, "#5b21b6", "−500 und weniger"), (-100, "#a78bfa", "−499 bis −100"),
                                (-20, "#ddd6fe", "−99 bis −20"), (20, "#d4d4d8", "−19 bis +19"),
                                (100, "#99f6e4", "+20 bis +99"), (500, "#2dd4bf", "+100 bis +499")):
        if saldo <= grenze if grenze < 0 else saldo < grenze:
            return farbe, text
    return "#0f766e", "+500 und mehr"


STUFEN = ["−500 und weniger", "−499 bis −100", "−99 bis −20", "−19 bis +19", "+20 bis +99", "+100 bis +499", "+500 und mehr"]


def karte_region(kreise, partner):
    """Kreise in NRW und Rheinland-Pfalz, gefärbt nach dem Saldo mit Bonn (Sicht Bonns: + mehr Zuzüge nach Bonn)."""
    saldo = {p["ags"]: p for p in partner}
    xs = [c[0] for f in kreise["features"] for c in _ringe(f["geometry"])]
    ys = [c[1] for f in kreise["features"] for c in _ringe(f["geometry"])]
    lat0 = (min(ys) + max(ys)) / 2
    k = 520 / ((max(xs) - min(xs)) * math.cos(math.radians(lat0)))
    pt = lambda c: ((c[0] - min(xs)) * math.cos(math.radians(lat0)) * k + 10, (max(ys) - c[1]) * k + 10)
    breite, hoehe = 540, (max(ys) - min(ys)) * k + 20
    pfade, bonn = [], None
    for f in kreise["features"]:
        ags = f["properties"]["ags"]
        p = saldo.get(ags)
        farbe, _ = ("#3f3f46", "") if ags == "05314" else _klasse(p["saldo"] if p else None)
        d = " ".join("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in map(pt, ring)) + " Z" for ring in _ringe_einzeln(f["geometry"]))
        name = f["properties"]["name"]
        titel = (f"Bonn" if ags == "05314" else
                 f"{name}: {_n(p['zuzuege'])} Zuzüge nach Bonn, {_n(p['fortzuege'])} Fortzüge aus Bonn, Saldo {_s(p['saldo'])}"
                 if p else f"{name}: kein Austausch oder geheim gehalten")
        pfade.append(f'<path d="{d}" fill="{farbe}" stroke="#a1a1aa" stroke-width="0.4"><title>{escape(titel)}</title></path>')
        if ags == "05314":
            from shapely.geometry import shape
            c = shape(f["geometry"]).representative_point()
            bonn = pt((c.x, c.y))
    marke = (f'<text x="{bonn[0] + 9:.1f}" y="{bonn[1] + 4:.1f}" class="wz-bonn">Bonn</text>' if bonn else "")
    return (f'<svg class="wz-svg wz-karte" viewBox="0 0 {breite} {hoehe:.0f}" role="img" aria-labelledby="wz-karte-t">'
            f'<title id="wz-karte-t">Saldo der Zu- und Fortzüge zwischen Bonn und den Kreisen in Nordrhein-Westfalen und '
            f'Rheinland-Pfalz, 2025</title>{"".join(pfade)}{marke}</svg>')


def _ringe_einzeln(g):
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    return [p[0] for p in g["coordinates"]]


def _ringe(g):
    return [c for r in _ringe_einzeln(g) for c in r]


def legende_karte():
    eintraege = [(_klasse(s)[0], t) for s, t in zip((-600, -200, -50, 0, 50, 200, 600), STUFEN)]
    eintraege.append(("#fafafa", "kein Austausch oder geheim"))
    return ('<ul class="wz-legende">' + "".join(f'<li><span style="background:{f}"></span>{escape(t)}</li>' for f, t in eintraege)
            + '<li><span style="background:#3f3f46"></span>Bonn</li></ul>')


def balken_alter(alter, b=720, sfx="b"):
    l, zh = (190 if b > 500 else 148), 30
    m = max(abs(a["saldo"]) for a in alter)
    halb = (b - l - (140 if b > 500 else 96)) / 2   # Platz für die Zahl links und rechts der Balken
    mitte = l + (70 if b > 500 else 50) + halb
    zeilen = []
    for i, a in enumerate(alter):
        y = 14 + i * zh
        w = abs(a["saldo"]) / m * halb
        x = mitte if a["saldo"] >= 0 else mitte - w
        farbe = ZUZUG if a["saldo"] >= 0 else FORTZUG
        tx = (mitte + w + 5, "start") if a["saldo"] >= 0 else (mitte - w - 5, "end")
        zeilen.append(f'<g><title>{escape(a["alter"])}: {_n(a["zuzuege"])} Zuzüge, {_n(a["fortzuege"])} Fortzüge, Saldo {_s(a["saldo"])}</title>'
                      f'<text x="{l - 8}" y="{y + 14}" text-anchor="end" class="wz-l">{escape(a["alter"])}</text>'
                      f'<rect x="{x:.1f}" y="{y + 3}" width="{w:.1f}" height="16" rx="2" fill="{farbe}"/>'
                      f'<text x="{tx[0]:.1f}" y="{y + 15}" text-anchor="{tx[1]}" class="wz-z">{_s(a["saldo"])}</text></g>')
    h = 14 + len(alter) * zh + 8
    return (f'<svg class="wz-svg" viewBox="0 0 {b} {h}" role="img" aria-labelledby="wz-alter-t{sfx}">'
            f'<title id="wz-alter-t{sfx}">Saldo der Zu- und Fortzüge Bonns innerhalb Deutschlands nach Altersgruppe, 2025</title>'
            f'<line x1="{mitte:.1f}" y1="8" x2="{mitte:.1f}" y2="{h - 4}" stroke="#a1a1aa" stroke-width="1"/>{"".join(zeilen)}</svg>')


def linie_reihe(reihe, b=720, sfx="b"):
    z, f = reihe.get("zuzuege", []), reihe.get("fortzuege", [])
    if not z or not f:
        return ""
    jahre = [j for j, _ in z]
    werte = [w for _, w in z + f]
    lo, hi = math.floor(min(werte) / 10) * 10 - 5, math.ceil(max(werte) / 10) * 10
    h, l, r, o, u = (280 if b > 500 else 250), 40, 12, 36, 30
    px = lambda j: l + (j - jahre[0]) / (jahre[-1] - jahre[0]) * (b - l - r)
    py = lambda w: o + (hi - w) / (hi - lo) * (h - o - u)
    gitter = "".join(f'<line x1="{l}" x2="{b - r}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="#ececf1"/>'
                     f'<text x="{l - 6}" y="{py(v) + 4:.1f}" text-anchor="end" class="wz-k">{v}</text>'
                     for v in range(int(lo) + 5 - (int(lo) + 5) % 10, int(hi) + 1, 10))
    achse = "".join(f'<text x="{px(j):.1f}" y="{h - 10}" text-anchor="middle" class="wz-k">{j}</text>' for j in jahre if j % (3 if b > 500 else 5) == 0)
    linie = lambda s, farbe: (f'<polyline fill="none" stroke="{farbe}" stroke-width="2.5" points="'
                              + " ".join(f"{px(j):.1f},{py(w):.1f}" for j, w in s) + '"/>')
    kopf = (f'<rect x="{l}" y="6" width="14" height="4" rx="2" fill="{ZUZUG}"/><text x="{l + 19}" y="12" class="wz-k">Zuzüge</text>'
            f'<rect x="{l + 80}" y="6" width="14" height="4" rx="2" fill="{FORTZUG}"/><text x="{l + 99}" y="12" class="wz-k">Fortzüge</text>')
    return (f'<svg class="wz-svg" viewBox="0 0 {b} {h}" role="img" aria-labelledby="wz-reihe-t{sfx}">'
            f'<title id="wz-reihe-t{sfx}">Zuzüge und Fortzüge Bonns je 1.000 Einwohner, gleitendes Mittel über vier Jahre, {jahre[0]}–{jahre[-1]}</title>'
            f'{kopf}{gitter}{achse}{linie(z, ZUZUG)}{linie(f, FORTZUG)}</svg>')


def _tabelle(kopf, zeilen, klasse=""):
    th = "".join(f'<th scope="col">{escape(k)}</th>' for k in kopf)
    tr = "".join("<tr>" + "".join(f"<td>{z}</td>" for z in zeile) + "</tr>" for zeile in zeilen)
    return f'<div class="tab-scroll"><table class="wz-tab {klasse}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def body(d, root):
    z, f, s = _summen(d)
    p = d["partner"]
    nrw = [x for x in p if x["land"] == "Nordrhein-Westfalen"]
    nz, nf = sum(x["zuzuege"] or 0 for x in nrw), sum(x["fortzuege"] or 0 for x in nrw)
    reihe = d["reihe"]
    letzt = lambda k: reihe[k][-1] if reihe.get(k) else (None, None)
    jz, wz = letzt("zuzuege")
    _, wf = letzt("fortzuege")
    _, ws = letzt("wanderungssaldo")
    tab_partner = _tabelle(["Kreis", "Land", "Zuzüge nach Bonn", "Fortzüge aus Bonn", "Saldo"],
                           [[escape(_kurz(x["kreis"])), escape(x["land"]), _n(x["zuzuege"]), _n(x["fortzuege"]), _s(x["saldo"])]
                            for x in p if max(x["zuzuege"] or 0, x["fortzuege"] or 0) >= 100], "wz-zahlen")
    tab_alter = _tabelle(["Altersgruppe", "Zuzüge", "Fortzüge", "Saldo"],
                         [[escape(a["alter"]), _n(a["zuzuege"]), _n(a["fortzuege"]), _s(a["saldo"])] for a in d["alter"]], "wz-zahlen")
    jahre = sorted({j for v in reihe.values() for j, _ in v})
    ww = {k: dict(v) for k, v in reihe.items()}
    zahl = lambda x: "–" if x is None else f"{x:.1f}".replace(".", ",")
    tab_reihe = _tabelle(["Jahr", "Zuzüge", "Fortzüge", "Saldo", "Bildungswanderung", "Familienwanderung"],
                         [[str(j)] + [zahl(ww.get(k, {}).get(j)) for k in ("zuzuege", "fortzuege", "wanderungssaldo",
                                                                           "bildungswanderung", "familienwanderung")]
                          for j in jahre], "wz-zahlen")
    abruf = d["stand"].get("abruf", "")[:10]
    return f"""    <h1>Zu- und Wegzüge</h1>
    <p class="lead">Wer nach Bonn zieht, wer Bonn verlässt und wohin: Zahlen für ganz Bonn aus der amtlichen Statistik.</p>
    <div class="wz-kacheln">
      <p class="wz-kachel"><span class="wz-wert" style="color:{ZUZUG}">{_n(z)}</span><span>Zuzüge nach Bonn aus anderen Kreisen Deutschlands, 2025</span></p>
      <p class="wz-kachel"><span class="wz-wert" style="color:{FORTZUG}">{_n(f)}</span><span>Fortzüge aus Bonn in andere Kreise Deutschlands, 2025</span></p>
      <p class="wz-kachel"><span class="wz-wert">{_s(s)}</span><span>Saldo innerhalb Deutschlands, 2025</span></p>
    </div>
    <p class="wz-hinweis"><strong>Ohne Ausland:</strong> Zuzüge aus dem Ausland und Fortzüge ins Ausland fehlen in dieser Quelle. Die Stadt Bonn nennt nach ihrem Melderegister für 2025 insgesamt 23.805 Zuzüge und 23.135 Fortzüge (<a href="{STADT_BERICHT}">Jahreswirtschaftsbericht 2026</a>). Beide Zählungen folgen unterschiedlichen Regeln und lassen sich nicht verrechnen.</p>
    <nav class="thema-sprung" aria-labelledby="sprung-h"><h2 id="sprung-h">Auf dieser Seite</h2><p><a href="#woher">Woher und wohin</a> · <a href="#region">Karte der Region</a> · <a href="#alter">Wer zieht</a> · <a href="#entwicklung">Entwicklung seit 2006</a> · <a href="#grenzen">Grenzen</a></p></nav>

    <h2 id="woher">Woher und wohin</h2>
    <p>Bonn tauscht Einwohnerinnen und Einwohner mit {len(p)} Kreisen. Am meisten mit dem Umland: {_n(nz)} Zuzüge aus und {_n(nf)} Fortzüge nach Nordrhein-Westfalen. Die {TOP} Kreise mit dem größten Austausch:</p>
{_beide(balken_partner, p)}
    <details class="hh-mehr"><summary>Alle Kreise mit mindestens 100 Zu- oder Fortzügen als Tabelle</summary>{tab_partner}</details>

    <h2 id="region">Karte der Region</h2>
    <p>Saldo mit Bonn je Kreis in Nordrhein-Westfalen und Rheinland-Pfalz. Violett: Mehr Menschen ziehen aus Bonn dorthin als umgekehrt. Türkis: Mehr Menschen ziehen von dort nach Bonn.</p>
{karte_region(d["kreise"], p)}
    {legende_karte()}

    <h2 id="alter">Wer zieht</h2>
    <p>Saldo nach Altersgruppe innerhalb Deutschlands: Junge Erwachsene von 18 bis 24 Jahren ziehen nach Bonn, oft zum Studium. Kinder und Erwachsene von 30 bis 49 Jahren, also häufig Familien, ziehen aus Bonn fort.</p>
{_beide(balken_alter, d["alter"])}
    <details class="hh-mehr"><summary>Zahlen je Altersgruppe als Tabelle</summary>{tab_alter}</details>

    <h2 id="entwicklung">Entwicklung seit 2006</h2>
    <p>Zuzüge und Fortzüge je 1.000 Einwohnerinnen und Einwohner, einschließlich Ausland. Jeder Wert ist der Durchschnitt aus vier Jahren; so wirken einzelne Jahre geglättet. {f"Zuletzt ({jz}): {zahl(wz)} Zuzüge und {zahl(wf)} Fortzüge je 1.000, Saldo {zahl(ws)}." if jz else ""}</p>
{_beide(linie_reihe, reihe)}
    <details class="hh-mehr"><summary>Werte als Tabelle, mit Bildungs- und Familienwanderung</summary>{tab_reihe}<p class="hint">Bildungswanderung: Saldo der 18- bis unter 25-Jährigen; Familienwanderung: Saldo der unter 18- und der 30- bis unter 50-Jährigen; je 1.000 Einwohner der jeweiligen Altersgruppe laut Wegweiser Kommune.</p></details>

    <h2 id="grenzen">Grenzen</h2>
    <ul>
      <li>Zahlen je Stadtbezirk oder Ortsteil gibt es öffentlich nicht. Sie folgen, sobald die Statistikstelle der Stadt sie liefert; dann auch auf der Karte.</li>
      <li>Umzüge innerhalb Bonns sind nicht enthalten.</li>
      <li>Die Ströme zwischen Kreisen stammen aus einem einzigen Jahr (2025). Für 2022 bis 2024 gibt es nur Salden, frühere Jahre nur auf Anfrage.</li>
      <li>Die Statistik schützt kleine Zahlen mit einem Zufallsverfahren: Einzelne Werte können leicht abweichen, sehr kleine bleiben leer. Summen auf dieser Seite sind aus den veröffentlichten Werten gebildet.</li>
      <li>Die Entwicklung seit 2006 zeigt Werte je 1.000 Einwohner im Durchschnitt über vier Jahre, keine Personenzahlen.</li>
    </ul>
    <details class="hh-mehr meta-acc"><summary>Quellen und Lizenzen</summary><p>Ströme zwischen Kreisen: Statistische Ämter des Bundes und der Länder, <a href="{KWM_SEITE}">Kreiswanderungsmatrix</a>, Berichtsjahr 2025, Datenlizenz Deutschland – Namensnennung 2.0 (dl-de/by-2-0); Summen und Altersgruppen für Bonn abgeleitet. Entwicklung: Bertelsmann Stiftung, <a href="https://www.wegweiser-kommune.de/">wegweiser-kommune.de</a> (CC0). Kreisgrenzen: © <a href="https://www.bkg.bund.de">BKG</a> (2025) <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>, Verwaltungsgebiete 1:2 500 000, vereinfacht; Datenquellen: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf. Melderegister: Stadt Bonn, Jahreswirtschaftsbericht 2026. Abgerufen am {abruf}.</p></details>
    <p><a href="{root}">Zur Karte</a> · <a href="{root}haushalt/">Haushalt auf einen Blick</a></p>"""


def write(site, site_url, page, ordner=ORDNER):
    """Schreibt zu-und-wegzuege/index.html; leer, solange der Schritt `wanderung` nicht gelaufen ist."""
    d = lesen(ordner)
    if not d:
        return []
    out = site / PFAD / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(site_url, PFAD, "Zu- und Wegzüge – Ratsatlas Bonn",
                        "Wer nach Bonn zieht und wer Bonn verlässt: Zu- und Fortzüge mit den Kreisen in Deutschland, "
                        "nach Alter und seit 2006, aus der amtlichen Statistik.", body(d, "../"), "../"), encoding="utf-8")
    return [PFAD]
