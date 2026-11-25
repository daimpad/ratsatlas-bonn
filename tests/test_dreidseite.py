"""Seite „Bonn in 3D“ (pipeline/dreidseite.py): Orte der letzten 12 Monate je Ortsteil, Seite mit Tabelle."""
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import dreidseite, gebietsseiten

FLAECHE = {"type": "Polygon", "coordinates": [[[7.0, 50.7], [7.1, 50.7], [7.1, 50.8], [7.0, 50.8], [7.0, 50.7]]]}
GEO = {"features": [{"properties": {"ortsteil_bez": "Endenich"}, "geometry": FLAECHE}]}


def vorlage(ref, datum, lon, lat, level="strasse", thema="verkehr", name="Titel"):
    return {"reference": ref, "name": name, "date": datum, "themes": [{"theme": thema}],
            "locations": [{"level": level, "lon": lon, "lat": lat}]}


class Orte(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "data" / "export" / "bonn"
        (self.base / "ortsteile").mkdir(parents=True)
        (self.base / "index.json").write_text(json.dumps({"zahlen": {"bis": "2026-11-24"},
            "ortsteile": [{"name": "Endenich", "slug": "endenich", "stadtbezirk": "Bonn", "jahr": 5}], "bezirke": [], "ohne_ortsbezug": []}))
        (self.base / "ortsteile" / "endenich.json").write_text(json.dumps({"papers": [
            vorlage("262001", "2026-10-01", 7.05, 50.75, name="<b>A</b>"),
            vorlage("262002", "2026-11-01", 7.05, 50.75, thema="bauen"),
            vorlage("252003", "2025-01-01", 7.06, 50.76),                 # älter als 12 Monate
            vorlage("262004", "2026-09-01", 7.07, 50.76, level="ortsteil"),  # kein genauer Ort
            vorlage("262005", "2026-09-01", 8.0, 50.76),                  # außerhalb der Fläche
            vorlage("252006", "2025-11-24", 7.08, 50.77)]}))              # Stichtag selbst zählt nicht (wie die Karte)

    def tearDown(self):
        self.tmp.cleanup()

    def test_orte(self):
        d = dreidseite.orte(self.base, GEO)
        self.assertEqual(d["seit"], "2025-11-25")   # Tag nach dem Stichtag, wie gebietszahlen.recent
        o = d["ortsteile"][0]
        self.assertEqual((o["slug"], o["n12"]), ("endenich", 5))
        self.assertEqual(len(o["orte"]), 1)
        lon, lat, thema, liste = o["orte"][0]
        self.assertEqual(thema, "bauen")                               # Thema der jüngsten Vorlage
        self.assertEqual([x[0] for x in liste], ["262002", "262001"])

    def test_seite(self):
        site = Path(self.tmp.name)
        from unittest import mock
        with mock.patch.object(dreidseite.config, "ORTSTEILE", Path(self.tmp.name) / "geo.json"):
            (Path(self.tmp.name) / "geo.json").write_text(json.dumps(GEO))
            self.assertEqual(dreidseite.write(site, "https://example.org/", gebietsseiten._page), ["3d/"])
        html = (site / "3d" / "index.html").read_text()
        self.assertIn('src="../dreid.js"', html)
        self.assertIn('href="?ortsteil=endenich"', html)
        self.assertIn("WebGL fehlt", html)
        self.assertIn("dl-de/zero-2.0", html)
        self.assertIn('id="d3-buehne"', html)   # Vollbild: Leiste, Karte und Statuszeile in einer Bühne
        self.assertIn('id="d3-voll"', html)
        orte = json.loads((site / "3d" / "orte.json").read_text())
        self.assertEqual(orte["ortsteile"][0]["orte"][0][3][1][1], "<b>A</b>")   # Titel wie in den Gebietsdateien; escapt die Seite


if __name__ == "__main__":
    unittest.main()
