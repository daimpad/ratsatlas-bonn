"""Seite „Rat im Video“ (pipeline/ratimvideo.py): Auswahl der Sitzungen, Vorlagen je Aufzeichnung, Jahresseiten."""
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import gebietsseiten, ratimvideo

V1 = "https://www.youtube.com/watch?v=abc"


def _vorlage(ref, top, video, seite=True, name="Titel"):
    return {"reference": ref, "name": name, "seite": seite,
            "steps": [{"typ": "beratung", "label": "Rat", "number": top, "aufzeichnung": video}]}


class RatImVideo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        base = self.site / "data" / "export" / "bonn"
        (base / "ortsteile").mkdir(parents=True)
        (base / "ohne-ortsbezug").mkdir()
        (base / "index.json").write_text(json.dumps({
            "ortsteile": [{"name": "Endenich", "slug": "endenich", "count": 1}], "bezirke": [],
            "ohne_ortsbezug": [{"jahr": "2026"}], "aktuell": {"heute": "2026-11-24"}}))
        (base / "ortsteile" / "endenich.json").write_text(json.dumps({"papers": [_vorlage("262000", "10", V1)]}))
        (base / "ohne-ortsbezug" / "2026.json").write_text(json.dumps({"papers": [
            _vorlage("261000", "1.2", V1, seite=False, name="<b>Antrag</b>"), _vorlage("261001", "3", None)]}))
        meetings = [
            {"date": "2026-11-12", "time": "17:00", "gremium": "Rat", "name": "Sitzung des Rates", "cancelled": False,
             "web": "https://example.org/to", "video": V1},
            {"date": "2026-11-16", "time": "19:00", "gremium": "Rat", "name": "Sitzung des Rates", "cancelled": False},
            {"date": "2025-03-01", "time": None, "gremium": "Rat", "name": "Sitzung des Rates", "cancelled": False},
            {"date": "2026-10-01", "gremium": "Hauptausschuss", "name": "Sitzung des Hauptausschusses", "cancelled": False},
            {"date": "2026-10-02", "gremium": "Rat", "name": "Sitzung des Rates", "cancelled": True, "video": V1},
            {"date": "2026-12-10", "gremium": "Rat", "name": "Sitzung des Rates", "cancelled": False},
            {"date": "2026-10-05", "gremium": "Integrationsrat", "name": "Sitzung des Integrationsrates", "cancelled": False}]
        (base / "zeit.json").write_text(json.dumps({"meetings": meetings}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_auswahl_und_vorlagen(self):
        d = ratimvideo.daten(self.site / "data" / "export" / "bonn", "2026-11-24")
        self.assertEqual([s["date"] for s in d], ["2026-11-16", "2026-11-12", "2025-03-01"])
        mit = d[1]
        self.assertEqual([v["reference"] for v in mit["vorlagen"]], ["261000", "262000"])   # nach TOP
        self.assertTrue(d[0]["jung"])
        self.assertFalse(d[2]["jung"])

    def test_seiten(self):
        pfade = ratimvideo.write(self.site, "https://example.org/", gebietsseiten._page)
        self.assertEqual(pfade, ["rat-im-video/", "rat-im-video/2026/", "rat-im-video/2025/"])
        uebersicht = (self.site / "rat-im-video" / "index.html").read_text()
        self.assertIn("1 von 3 Sitzungen des Rates", uebersicht)
        self.assertIn("Noch keine Aufzeichnung in der Quelle", uebersicht)
        self.assertIn('href="2026/#s2026-11-12-rat"', uebersicht)
        self.assertIn("nicht amtlich", uebersicht)
        jahr = (self.site / "rat-im-video" / "2026" / "index.html").read_text()
        self.assertIn('href="../../vorgang/262000/"', jahr)
        self.assertIn('href="../../?gebiet=ohne:2026#261000"', jahr)   # ohne eigene Seite: Karte
        self.assertIn("&lt;b&gt;Antrag&lt;/b&gt;", jahr)               # Titel maskiert ausgegeben
        self.assertNotIn("<b>Antrag", jahr)


if __name__ == "__main__":
    unittest.main()
