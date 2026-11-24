"""Phase 0 3D: LoD1-Kacheln für Bonn laden, je Gebäude Grundriss (WGS84) und Höhe ableiten, Kachel danach löschen."""
import json, sys, os, subprocess, time
import xml.etree.ElementTree as ET
from pathlib import Path
from pyproj import Transformer
D = Path(sys.argv[1]); out = D / "gebaeude"; out.mkdir(exist_ok=True)
NS = {"bldg": "http://www.opengis.net/citygml/building/1.0", "gml": "http://www.opengis.net/gml"}
T = Transformer.from_crs(25832, 4326, always_xy=True)
URL = "https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod1_gml/lod1_gml/"
tiles = json.load(open(D / "bonn_tiles.json"))
t0 = time.time(); stat = {"kacheln": 0, "gebaeude": 0, "fremd": 0}
for f in tiles:
    ziel = out / (f["name"] + ".json")
    if ziel.exists():
        continue
    tmp = D / "gml" / f["name"]
    subprocess.run(["curl", "-sf", "--retry", "3", "-o", str(tmp), URL + f["name"]], check=True)
    feats = []
    for ev, el in ET.iterparse(tmp, events=("end",)):
        if el.tag not in ("{%s}Building" % NS["bldg"], "{%s}BuildingPart" % NS["bldg"]):
            continue
        solid = el.find("bldg:lod1Solid", NS)
        gs = None
        for a in el.findall("{http://www.opengis.net/citygml/generics/1.0}stringAttribute"):
            if a.get("name") == "Gemeindeschluessel":
                gs = a.findtext("{http://www.opengis.net/citygml/generics/1.0}value")
        if solid is not None:
            polys = []
            for pl in solid.iter("{%s}posList" % NS["gml"]):
                v = list(map(float, pl.text.split()))
                polys.append([(v[i], v[i+1], v[i+2]) for i in range(0, len(v), 3)])
            zs = [p[2] for poly in polys for p in poly]
            zmin, zmax = min(zs), max(zs)
            boden = min((poly for poly in polys if all(abs(p[2] - zmin) < 0.01 for p in poly)), key=len, default=None)
            if boden and gs == "05314000":
                ring = [[round(c, 6) for c in T.transform(x, y)] for x, y, _ in boden]
                feats.append({"type": "Feature", "properties": {"h": round(zmax - zmin, 1)},
                              "geometry": {"type": "Polygon", "coordinates": [ring]}})
            elif boden:
                stat["fremd"] += 1
        if el.tag == "{%s}Building" % NS["bldg"]:
            el.clear()
    json.dump(feats, open(ziel, "w"), separators=(",", ":"))
    tmp.unlink()
    stat["kacheln"] += 1; stat["gebaeude"] += len(feats)
    print(stat["kacheln"], f["name"], len(feats), round(time.time() - t0), flush=True)
print(stat)
