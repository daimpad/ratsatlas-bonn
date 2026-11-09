"""Seite rss/ (pipeline/rssseite.py): Feed-Adresse, drei Zugänge, Liste der Feeds ohne leere, Feed-Erkennung im Kopf
und ein Python-Beispiel, das gegen einen Feed der Pipeline läuft."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import gebietsseiten, publish, rssseite, seo

PAPER = {"reference": "261856", "name": "Radweg Endenicher Straße", "paper_type": "Antrag", "date": "2026-05-04",
         "amt": "66 Tiefbauamt", "stand": "in Beratung", "web": "https://example.org/vo?x=1",
         "source_object": "https://www.bonn.sitzung-online.de/oparl/papers/1", "steps": []}


def _site(tmp):
    site = Path(tmp)
    base = site / "data" / "export" / "bonn"
    (base / "ortsteile").mkdir(parents=True)
    (base / "index.json").write_text(json.dumps({
        "ortsteile": [{"name": "Endenich", "slug": "endenich", "stadtbezirk": "Bonn", "count": 1},
                      {"name": "Hardthöhe", "slug": "hardthoehe", "stadtbezirk": "Hardtberg", "count": 0}],
        "bezirke": [{"name": "Bonn", "slug": "bonn", "count": 0}],
        "ohne_ortsbezug": [{"jahr": "2026", "count": 0}]}), encoding="utf-8")
    (base / "ortsteile" / "endenich.json").write_text(json.dumps({"meta": {}, "papers": [PAPER]}), encoding="utf-8")
    areas = {"ortsteil:endenich": [1], "ortsteil:hardthoehe": [], "bezirk:bonn": [], "ohne:2026": [], "gesamt": [1]}
    names = {"ortsteil:endenich": "Endenich", "ortsteil:hardthoehe": "Hardthöhe",
             "bezirk:bonn": "Stadtbezirk Bonn, ohne genaueren Ort", "ohne:2026": "stadtweit / ohne Ortsbezug 2026"}
    publish.write_feeds(base / "feeds", areas, {1: PAPER}, names, {1: "ortsteil:endenich"}, lambda r: r, "2025-01-01")
    return site


class Seite(unittest.TestCase):
    def test_seite_und_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = _site(tmp)
            seo.write(site, "https://ris-bonn.example/")
            html = (site / "rss" / "index.html").read_text(encoding="utf-8")
            sitemap = (site / seo.SITEMAP_SEITEN).read_text(encoding="utf-8")
            gebiet = (site / "ortsteil" / "endenich" / "index.html").read_text(encoding="utf-8")
        url = "https://ris-bonn.example/data/export/bonn/feeds/ganz-bonn.xml"
        self.assertIn("<h1>Inhalte abonnieren und weiterverwenden</h1>", html)
        self.assertIn(f'<input id="rss-url" class="rss-url" type="text" readonly value="{url}"', html)
        self.assertIn(">RSS-Adresse kopieren</button>", html)
        self.assertIn('<a class="rss-knopf rss-zweit" href="../data/export/bonn/feeds/ganz-bonn.xml" type="application/atom+xml">'
                      'Feed direkt ansehen</a>', html)
        for t in ("Einfach abonnieren", "In eine Website einbinden", "Automatisiert weiterverarbeiten"):
            self.assertIn(f">{t}</h2>", html)
        # Feed-Erkennung im Kopf, ohne Skripte von außen
        kopf = html.split("</head>")[0]
        self.assertIn('<link rel="alternate" type="application/atom+xml" title="Ratsatlas Bonn – ganz Bonn" '
                      'href="../data/export/bonn/feeds/ganz-bonn.xml">', kopf)
        self.assertNotRegex(html, r'<script[^>]+src="https?:')
        self.assertIn('<script src="../rss.js" defer></script>', html)
        # leere Feeds fehlen in der Liste
        self.assertIn('<a href="../data/export/bonn/feeds/ortsteil-endenich.xml" type="application/atom+xml" data-feed>Endenich</a>', html)
        self.assertNotIn('<ul class="rss-liste"></ul>', html)
        self.assertNotIn("ortsteil-hardthoehe.xml", html)
        self.assertNotIn("bezirk-bonn.xml", html)
        self.assertIn("<loc>https://ris-bonn.example/rss/</loc>", sitemap)
        # Gebietsseite: eigener Feed vor dem Feed über ganz Bonn
        k = gebiet.split("</head>")[0]
        self.assertLess(k.index("feeds/ortsteil-endenich.xml"), k.index("feeds/ganz-bonn.xml"))
        self.assertIn('<a href="../../rss/">Abonnieren (RSS)</a>', gebiet)

    def test_beispiel_laeuft_gegen_den_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = _site(tmp)
            feed = site / "data" / "export" / "bonn" / "feeds" / "ganz-bonn.xml"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exec(rssseite.beispiel(feed.resolve().as_uri()), {})
        zeilen = out.getvalue().splitlines()
        self.assertEqual(len(zeilen), 1)
        self.assertTrue(zeilen[0].startswith("2026-05-04 Neue Vorlage 261856: Radweg Endenicher Straße "))
        self.assertTrue(zeilen[0].endswith("?gebiet=ortsteil:endenich#261856"))

    def test_kopf_der_seiten(self):
        html = gebietsseiten._page("https://x/", "a/", "T", "D", "<p>b</p>", "../")
        self.assertIn('href="../data/export/bonn/feeds/ganz-bonn.xml"', html.split("</head>")[0])


if __name__ == "__main__":
    unittest.main()
