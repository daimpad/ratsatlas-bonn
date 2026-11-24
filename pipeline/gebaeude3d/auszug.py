"""Gebäude für die Seite 3d/ („Bonn in 3D“, Entscheidungen des Auftraggebers 24.11.2026, dreid/phase0/BERICHT.md).

Aufruf: python -I pipeline/gebaeude3d/auszug.py <ortsteile.geojson> <ausgabeordner>

Lädt das 3D-Gebäudemodell LoD1 von Geobasis NRW (CityGML, 1-km-Kacheln, dl-de/zero-2.0) für die Kacheln, die Bonn
berühren, und legt je Ortsteil eine Datei <slug>.json ab: Grundriss (WGS84, 5 Nachkommastellen, um etwa 0,5 m
vereinfacht) und Höhe (oberste minus unterste Kante, auf 0,5 m gerundet). Übernommen werden nur Gebäude mit dem
Gemeindeschlüssel Bonn; keine Gebäudefunktion, keine Adressen. Jede Kachel wird nach dem Lesen gelöscht.
stand.json nennt Quelle, Lizenz, Kacheln, Gebäude und den jüngsten Zeitstempel der Kacheln (keinen Erzeugungszeitpunkt).
"""
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Polygon, box, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

URL = "https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod1_gml/lod1_gml/"
BLDG = "{http://www.opengis.net/citygml/building/1.0}"
GEN = "{http://www.opengis.net/citygml/generics/1.0}"
GML = "{http://www.opengis.net/gml}"
BONN = "05314000"


def slug(name):
    name = name.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


def curl(url, ziel=None):
    cmd = ["curl", "-sfL", "--retry", "4", "--retry-delay", "5", "--max-time", "600", url]
    if ziel:
        subprocess.run(cmd + ["-o", str(ziel)], check=True)
        return None
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def kacheln(stadt_utm):
    index = json.loads(curl(URL + "index.json"))
    out = []
    for f in index["datasets"][0]["files"]:
        teile = f["name"].split("_")
        e, n = int(teile[2]), int(teile[3])
        if box(e * 1000, n * 1000, e * 1000 + 1000, n * 1000 + 1000).intersects(stadt_utm):
            out.append(f)
    return out


def gebaeude(pfad):
    """(Höhe, Bodenring in UTM) je Gebäude oder Gebäudeteil mit Gemeindeschlüssel Bonn."""
    for _, el in ET.iterparse(pfad, events=("end",)):
        if el.tag not in (BLDG + "Building", BLDG + "BuildingPart"):
            continue
        gs = next((a.findtext(GEN + "value") for a in el.findall(GEN + "stringAttribute")
                   if a.get("name") == "Gemeindeschluessel"), None)
        solid = el.find(BLDG + "lod1Solid")
        if solid is not None and gs == BONN:
            polys = []
            for pl in solid.iter(GML + "posList"):
                v = list(map(float, pl.text.split()))
                polys.append([(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)])
            zs = [p[2] for poly in polys for p in poly]
            zmin, zmax = min(zs), max(zs)
            boden = next((poly for poly in polys if all(abs(p[2] - zmin) < 0.01 for p in poly)), None)
            if boden and zmax - zmin >= 1:
                yield round((zmax - zmin) * 2) / 2, [(x, y) for x, y, _ in boden]
        if el.tag == BLDG + "Building":
            el.clear()


def main(ortsteile_pfad, ausgabe):
    ausgabe = Path(ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)
    nach_utm = Transformer.from_crs(4326, 25832, always_xy=True).transform
    nach_wgs = Transformer.from_crs(25832, 4326, always_xy=True).transform
    ots = [(f["properties"]["ortsteil_bez"], transform(nach_utm, shape(f["geometry"])))
           for f in json.loads(Path(ortsteile_pfad).read_text(encoding="utf-8"))["features"]]
    baum = STRtree([g for _, g in ots])
    stadt = unary_union([g for _, g in ots])
    liste = kacheln(stadt)
    je_ot, gesehen, stand = defaultdict(list), set(), ""
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(liste, 1):
            pfad = Path(tmp) / f["name"]
            curl(URL + f["name"], pfad)
            stand = max(stand, f.get("timestamp", ""))
            for h, ring in gebaeude(pfad):
                poly = Polygon(ring)
                if not poly.is_valid or poly.area < 4:
                    continue
                schluessel = (round(ring[0][0], 1), round(ring[0][1], 1), h)
                if schluessel in gesehen:   # Gebäude an Kachelgrenzen stehen in beiden Kacheln
                    continue
                gesehen.add(schluessel)
                punkt = poly.representative_point()
                treffer = [j for j in baum.query(punkt) if ots[j][1].contains(punkt)]
                if not treffer:
                    continue
                g = transform(nach_wgs, poly.simplify(0.5, preserve_topology=True))
                je_ot[ots[treffer[0]][0]].append([h, [[round(x, 5), round(y, 5)] for x, y in g.exterior.coords]])
            pfad.unlink()
            print(f"{i}/{len(liste)} {f['name']}", flush=True)
    summe = 0
    for name, _ in ots:
        geb = sorted(je_ot.get(name, []), key=lambda g: (g[1][0][0], g[1][0][1]))
        summe += len(geb)
        (ausgabe / f"{slug(name)}.json").write_text(json.dumps({"ortsteil": name, "gebaeude": geb},
                                                               ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (ausgabe / "stand.json").write_text(json.dumps({
        "quelle": "Geobasis NRW, 3D-Gebäudemodell LoD1 (CityGML)", "url": URL, "lizenz": "dl-de/zero-2.0",
        "kacheln": len(liste), "gebaeude": summe, "stand_kacheln": stand}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"{summe} Gebäude in {len(ots)} Ortsteilen → {ausgabe}")
    if summe < 100000:
        raise SystemExit(f"nur {summe} Gebäude, erwartet über 100.000")


if __name__ == "__main__":
    main(*sys.argv[1:3])
