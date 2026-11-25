"""Seite 3d/ „Bonn in 3D“ (Entscheidungen des Auftraggebers 24.11.2026, dreid/phase0/BERICHT.md: LoD1, beide Ansichten).

Erzeugt im Schritt `seo` aus der zusammengestellten Seite (_site):
- 3d/index.html – Seite mit 3D-Karte (site/dreid.js, MapLibre GL aus site/vendor/maplibre), Tabelle aller Ortsteile als
  gleichwertige Alternative, Hinweis ohne WebGL, Grenzen und Quellen;
- 3d/orte.json – je Ortsteil: Mittelpunkt, Vorlagen der letzten 12 Monate (wie die Flächen der Hauptkarte, index.json
  „jahr“) und die Orte mit Vorlagen dieser 12 Monate auf Ebene Straße, Objekt oder Punkt (wie die Punkte der
  Hauptkarte, Titel maskiert wie dort), mit Thema des ersten Eintrags (abgeleitet).
Die Gebäude (3d/gebaeude/<slug>.json) kommen aus dem Branch `gebaeude` (Workflow gebaeude.yml,
pipeline/gebaeude3d/auszug.py). Keine Erzeugungszeitpunkte (stabile Ausgabe)."""
import json
from collections import defaultdict
from datetime import date, timedelta
from html import escape

from . import config
from .export import slug
from .topics import THEMES

PFAD = "3d/"
EBENEN = ("strasse", "objekt", "punkt")
FARBEN = {"verkehr": "#0072b2", "bauen": "#d55e00", "umwelt": "#009e73", "bildung": "#cc79a7", "kinder": "#e69f00",
          "soziales": "#882255", "kultur": "#56b4e9", "wirtschaft": "#8c6d1f", "sicherheit": "#332288",
          "beteiligung": "#44aa99"}   # wie THEME_COLOR in site/app.js
OHNE_THEMA = "#8a8a96"


def orte(base, ortsteile_geo):
    """Daten für 3d/orte.json aus index.json und den Gebietsdateien der Ortsteile."""
    from shapely.geometry import Point, shape
    index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    bis = (index.get("zahlen") or {}).get("bis") or (index.get("aktuell") or {}).get("heute")
    # wie gebietszahlen.recent (Flächen der Hauptkarte): Vorlagen nach dem Stichtag, angezeigt ab dem Tag danach
    grenze = (date.fromisoformat(bis) - timedelta(days=365)).isoformat() if bis else "0000"
    seit = (date.fromisoformat(grenze) + timedelta(days=1)).isoformat() if bis else "0000"
    flaechen = {f["properties"]["ortsteil_bez"]: shape(f["geometry"]) for f in ortsteile_geo["features"]}
    out = []
    for o in index["ortsteile"]:
        fl = flaechen.get(o["name"])
        if fl is None:
            continue
        c = fl.representative_point()
        punkte = defaultdict(list)
        datei = base / "ortsteile" / f"{o['slug']}.json"
        papers = json.loads(datei.read_text(encoding="utf-8"))["papers"] if datei.exists() else []
        for p in papers:
            if (p.get("date") or "") <= grenze:
                continue
            for loc in p.get("locations") or []:
                if loc.get("level") in EBENEN and loc.get("lon") and fl.contains(Point(loc["lon"], loc["lat"])):
                    punkte[(round(loc["lon"], 5), round(loc["lat"], 5))].append(p)
                    break
        liste = []
        for (lon, lat), ps in sorted(punkte.items()):
            ps = sorted(ps, key=lambda p: (p.get("date") or "", p["reference"]), reverse=True)
            thema = ((ps[0].get("themes") or [{}])[0]).get("theme")
            liste.append([lon, lat, thema, [[p["reference"], p["name"] or "", p.get("date") or ""] for p in ps]])
        out.append({"name": o["name"], "slug": o["slug"], "stadtbezirk": o.get("stadtbezirk"),
                    "lon": round(c.x, 5), "lat": round(c.y, 5), "n12": o.get("jahr") or 0, "orte": liste})
    return {"seit": seit, "bis": bis, "themen": [{"id": k, "label": v, "farbe": FARBEN[k]} for k, v in THEMES],
            "ohne_thema": OHNE_THEMA, "ortsteile": out}


def body(d, gebaeude_stand):
    zeilen = "".join(
        f'<tr><th scope="row"><a href="?ortsteil={escape(o["slug"])}">{escape(o["name"])}</a></th>'
        f'<td>{escape(o["stadtbezirk"] or "")}</td><td>{o["n12"]}</td><td>{sum(len(x[3]) for x in o["orte"])}</td>'
        f'<td><a href="../?gebiet=ortsteil:{escape(o["slug"])}">Karte</a></td></tr>'
        for o in sorted(d["ortsteile"], key=lambda o: o["name"]))
    legende = "".join(f'<li><span style="background:{t["farbe"]}"></span>{escape(t["label"])}</li>' for t in d["themen"])
    legende += f'<li><span style="background:{OHNE_THEMA}"></span>ohne Thema</li>'
    geb = (f'{gebaeude_stand["gebaeude"]:,} Gebäude'.replace(",", ".") if gebaeude_stand else "Gebäude")
    stand = f" (Stand der Kacheln {gebaeude_stand['stand_kacheln'][:10]})" if gebaeude_stand and gebaeude_stand.get("stand_kacheln") else ""
    zeitraum = f"{d['seit'][8:10]}.{d['seit'][5:7]}.{d['seit'][:4]} bis {d['bis'][8:10]}.{d['bis'][5:7]}.{d['bis'][:4]}" if d.get("bis") else "letzte 12 Monate"
    return f"""    <h1>Bonn in 3D</h1>
    <p class="lead">Wo in Bonn wie viel beraten wird – die Vorlagen der letzten 12 Monate als Säulen zwischen den Gebäuden der Stadt.</p>
    <div class="d3-buehne" id="d3-buehne">
    <div class="d3-leiste" role="group" aria-label="Ansicht">
      <button type="button" class="d3-knopf" data-ansicht="vorort" aria-pressed="true">Vorlagen vor Ort</button>
      <button type="button" class="d3-knopf" data-ansicht="bonn" aria-pressed="false">Ganz Bonn</button>
      <label class="d3-wahl">Ortsteil <select id="d3-ortsteil"></select></label>
      <button type="button" class="d3-knopf d3-leise" id="d3-neigung" aria-pressed="false">Schräg ansehen</button>
      <button type="button" class="d3-knopf d3-leise" id="d3-zurueck">Ansicht zurücksetzen</button>
      <button type="button" class="d3-knopf d3-voll" id="d3-voll" hidden><svg class="d3-sym d3-sym-voll" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg><svg class="d3-sym d3-sym-ende" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg><span>Vollbild</span></button>
    </div>
    <div class="d3-rahmen">
      <div id="d3-karte" role="region" aria-label="3D-Karte. Dieselben Angaben stehen in der Liste unter der Karte und in der Tabelle aller Ortsteile."></div>
      <p class="d3-ohne" id="d3-ohne" hidden>Ihr Browser kann die 3D-Karte nicht zeigen (WebGL fehlt). Die Liste und die Tabelle unten enthalten dieselben Angaben; die <a href="../">Hauptkarte</a> zeigt alle Vorlagen.</p>
    </div>
    <p class="d3-hinweis" id="d3-status" aria-live="polite"></p>
    </div>
    <details class="hh-mehr" open><summary>So lesen Sie die Karte</summary>
      <p><strong>Vorlagen vor Ort:</strong> Jede Säule steht an einem Ort, den eine Vorlage nennt (Straße, Gebäude oder Angabe der Stadt), und ist umso höher, je mehr Vorlagen dort beraten wurden. Die Farbe zeigt das Thema der jüngsten Vorlage. Ein Klick auf eine Säule nennt die Vorlagen; der Titel führt zum Vorgang.</p>
      <p><strong>Vollbild:</strong> „Vollbild“ zeigt die Karte auf dem ganzen Bildschirm, die Bedienung bleibt oben. Zurück mit „Vollbild beenden“ oder der Taste Esc. Mit der Maus: ziehen verschiebt, rechte Taste oder Strg und ziehen dreht und neigt; auf dem Telefon mit zwei Fingern.</p>
      <p><strong>Ganz Bonn:</strong> Eine Säule je Ortsteil, so hoch wie die Zahl der Vorlagen mit Ortsbezug in den letzten 12 Monaten. Ein Klick wechselt zu diesem Ortsteil.</p>
      <p>Die Höhe einer Säule sagt nichts über die Bedeutung eines Vorhabens. Vorlagen ohne genauen Ort fehlen in der Ansicht „Vorlagen vor Ort“.</p>
      <ul class="d3-legende">{legende}</ul>
    </details>
    <h2 id="d3-liste-h">Vorlagen im gewählten Ortsteil</h2>
    <div id="d3-liste"><p class="hint">Wird geladen …</p></div>
    <h2 id="ortsteile">Alle Ortsteile</h2>
    <p>Vorlagen mit Ortsbezug im Zeitraum {zeitraum}. Der Name öffnet den Ortsteil in 3D, „Karte“ die Hauptkarte.</p>
    <div class="tab-scroll"><table class="wz-tab wz-zahlen d3-tab"><thead><tr><th scope="col">Ortsteil</th><th scope="col">Stadtbezirk</th><th scope="col">Vorlagen (12 Monate)</th><th scope="col">davon mit genauem Ort</th><th scope="col">Hauptkarte</th></tr></thead><tbody>{zeilen}</tbody></table></div>
    <h2 id="grenzen">Grenzen</h2>
    <ul>
      <li>Die Gebäude sind einfache Blöcke mit der gemessenen Höhe, ohne Dachformen und Gelände.</li>
      <li>Verortungen sind teils abgeleitet: Ein Name im Titel kann einen anderen Ort meinen. Maßgeblich ist das Original im Ratsinformationssystem.</li>
      <li>Die 3D-Karte braucht WebGL und ist für Vorleseprogramme nicht lesbar; Liste und Tabelle enthalten dieselben Angaben.</li>
    </ul>
    <details class="hh-mehr meta-acc"><summary>Quellen und Lizenzen</summary><p>{geb}: Geobasis NRW, 3D-Gebäudemodell LoD1, dl-de/zero-2.0{stand}; übernommen sind nur Grundriss und Höhe. Vorlagen und Orte: Ratsatlas Bonn aus der OParl-Schnittstelle der Stadt Bonn (CC0) und OParl-Lite Bonn (CC BY 4.0), Verortung teils abgeleitet. Hintergrund: © OpenStreetMap-Mitwirkende (ODbL), Protomaps. Darstellung mit MapLibre GL (BSD-3-Clause).</p></details>
    <p><a href="../">Zur Karte</a> · <a href="../zu-und-wegzuege/">Zu- und Wegzüge</a></p>"""


HEAD = ('\n  <link rel="stylesheet" href="../vendor/maplibre/maplibre-gl.css">'
        '\n  <script type="module" src="../dreid.js"></script>')


def write(site, site_url, page):
    """Schreibt 3d/index.html und 3d/orte.json; leer ohne Gebietsdaten."""
    base = site / "data" / "export" / "bonn"
    if not (base / "index.json").exists():
        return []
    d = orte(base, json.loads(config.ORTSTEILE.read_text(encoding="utf-8")))
    ziel = site / PFAD
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / "orte.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    stand_datei = ziel / "gebaeude" / "stand.json"
    stand = json.loads(stand_datei.read_text(encoding="utf-8")) if stand_datei.exists() else None
    (ziel / "index.html").write_text(page(site_url, PFAD, "Bonn in 3D – Ratsatlas Bonn",
                                          "Die Vorlagen der letzten 12 Monate als Säulen zwischen den Gebäuden Bonns, "
                                          "je Ortsteil und für ganz Bonn, mit Tabelle.", body(d, stand), "../", HEAD),
                                     encoding="utf-8")
    return [PFAD]
