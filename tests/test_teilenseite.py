"""Seite teilen/ (pipeline/teilenseite.py) und Bilder (pipeline/teilen.py): alle Dateien des Verzeichnisses vorhanden,
Formate vollständig, Lizenz genannt; Grafiken ohne Netz erzeugbar."""
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import gebietsseiten, teilen, teilenseite


class Teilen(unittest.TestCase):
    def test_bilder_und_seite(self):
        m = json.loads(teilenseite.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(set(m["formate"]), set(teilen.FORMATE))
        self.assertEqual([x["key"] for x in m["motive"]], [x[0] for x in teilen.MOTIVE])
        for motiv in m["motive"]:
            for fmt, dateien in motiv["dateien"].items():
                self.assertIn("jpg", dateien)
                self.assertIn("webp", dateien)
                self.assertEqual("druck" in dateien, fmt in teilen.DRUCK)
                for d in dateien.values():
                    self.assertTrue((teilen.ZIEL / d["datei"]).exists(), d["datei"])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(teilenseite.write(Path(tmp), "https://example.org/", gebietsseiten._page), ["teilen/"])
            html = (Path(tmp) / "teilen" / "index.html").read_text(encoding="utf-8")
        self.assertIn("CC BY 4.0", html)
        self.assertIn("© OpenStreetMap-Mitwirkende", html)
        self.assertEqual(html.count('class="tl-motiv"'), len(teilen.MOTIVE))
        self.assertIn('href="../teilen/bilder/punkte-breit-druck.jpg" download', html)

    def test_grafik_ohne_netz(self):
        d = {"punkte": [(7.1, 50.73, "verkehr", "Endenich")], "haushalt": {"01": ("Innere Verwaltung", 5.0)},
             "bezirke": [{"geometry": {"type": "Polygon", "coordinates": [[[7.0, 50.6], [7.2, 50.6], [7.2, 50.8], [7.0, 50.6]]]}}],
             "ortsteile": [], "schritte": [{"typ": "entscheidung", "aufzeichnung": "x"}]}
        for key, erzeuge in teilen.ERZEUGER.items():
            svg = erzeuge(1200, 630, d)
            self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"), key)
        self.assertEqual(len(teilen._squarify([("a", 3), ("b", 1)], 0, 0, 4, 1)), 2)


if __name__ == "__main__":
    unittest.main()
