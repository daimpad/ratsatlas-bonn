import json
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

from pipeline import gebietsseiten, seo

SITE = Path(__file__).resolve().parent.parent / "site"


class Head(HTMLParser):
    """Sammelt meta-, link- und JSON-LD-Angaben aus dem Kopf von index.html."""

    def __init__(self):
        super().__init__()
        self.meta, self.links, self.ld, self._ld = {}, [], [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            self.meta[a.get("name") or a.get("property") or a.get("http-equiv")] = a.get("content")
        if tag == "link":
            self.links.append(a)
        self._ld = tag == "script" and a.get("type") == "application/ld+json"

    def handle_data(self, data):
        if self._ld and data.strip():
            self.ld.append(data)

    def handle_endtag(self, tag):
        self._ld = False


def head(text):
    h = Head()
    h.feed(text)
    return h


class Auffindbarkeit(unittest.TestCase):
    def test_kopf_vollstaendig(self):
        h = head((SITE / "index.html").read_text(encoding="utf-8"))
        for key in ("description", "robots", "theme-color", "og:title", "og:description", "og:url", "og:image",
                    "og:image:alt", "twitter:card", "author"):
            self.assertTrue(h.meta.get(key), key)
        self.assertLessEqual(len(h.meta["description"]), 170)
        rels = {link["rel"] for link in h.links}
        self.assertTrue({"canonical", "icon", "apple-touch-icon", "manifest"} <= rels)
        data = json.loads(h.ld[0])
        self.assertEqual({x["@type"] for x in data["@graph"]}, {"WebSite", "WebApplication"})

    def test_dateien_vorhanden(self):
        h = head((SITE / "index.html").read_text(encoding="utf-8"))
        local = [link["href"] for link in h.links if link["rel"] in ("icon", "apple-touch-icon", "manifest")]
        local.append(h.meta["og:image"].removeprefix(seo.DEFAULT_URL))
        manifest = json.loads((SITE / "site.webmanifest").read_text(encoding="utf-8"))
        local += [i["src"] for i in manifest["icons"]]
        for path in local:
            # Versionszusatz (?v=2 gegen den Browser-Zwischenspeicher) gehört nicht zum Dateinamen
            self.assertTrue((SITE / path.split("?")[0]).is_file(), path)

    def test_adressen_robots_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            for name in seo.PAGES:
                shutil.copy(SITE / name, site / name)
            seo.write(site, "https://ris-bonn.example/")
            for name in seo.PAGES:
                text = (site / name).read_text(encoding="utf-8")
                self.assertNotIn(seo.DEFAULT_URL, text, name)
                self.assertIn("https://ris-bonn.example/", text)
            h = head((site / "index.html").read_text(encoding="utf-8"))
            self.assertEqual(next(x["href"] for x in h.links if x["rel"] == "canonical"), "https://ris-bonn.example/")
            json.loads(h.ld[0])  # bleibt gültiges JSON
            robots = (site / "robots.txt").read_text(encoding="utf-8")
            self.assertIn("Sitemap: https://ris-bonn.example/sitemap.xml", robots)
            index = [e.text for e in ET.parse(site / "sitemap.xml").getroot().iter(f"{{{seo.NS}}}loc")]
            self.assertEqual(index, ["https://ris-bonn.example/sitemap-seiten.xml"])   # ohne Gebietsdaten keine Vorgänge
            urls = [e.text for e in ET.parse(site / seo.SITEMAP_SEITEN).getroot().iter(f"{{{seo.NS}}}loc")]
            # ohne Gebietsdaten keine Gebiets- und Themenseiten; haushalt/ beruht auf data/haushalt/ im Repository
            self.assertEqual(urls, ["https://ris-bonn.example/", "https://ris-bonn.example/datenschutz.html",
                                    "https://ris-bonn.example/haushalt/", "https://ris-bonn.example/rss/",
                            "https://ris-bonn.example/begriffe/", "https://ris-bonn.example/einfach/",
                    "https://ris-bonn.example/technik/"])
            self.assertIsNone(re.search(r"lastmod", (site / seo.SITEMAP_SEITEN).read_text(encoding="utf-8")))


class Gebietsseiten(unittest.TestCase):
    def test_seiten_und_sitemap(self):
        paper = {"reference": "261856", "name": "Radweg <Endenicher> Straße", "paper_type": "Antrag", "date": "2026-05-04",
                 "stand": "in Beratung", "web": "https://example.org/vo?x=1&y=2", "themes": [{"theme": "verkehr"}]}
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            base = site / "data" / "export" / "bonn"
            (base / "ortsteile").mkdir(parents=True)
            (base / "index.json").write_text(json.dumps({
                "ortsteile": [{"name": "Endenich", "slug": "endenich", "stadtbezirk": "Bonn", "count": 1},
                              {"name": "Leer", "slug": "leer", "stadtbezirk": "Bonn", "count": 0}],
                "bezirke": [{"name": "Bonn", "slug": "bonn", "count": 0}], "ohne_ortsbezug": []}), encoding="utf-8")
            (base / "ortsteile" / "endenich.json").write_text(json.dumps({"meta": {}, "papers": [paper]}), encoding="utf-8")
            seo.write(site, "https://ris-bonn.example/")
            page = (site / "ortsteil" / "endenich" / "index.html").read_text(encoding="utf-8")
            self.assertIn('<link rel="canonical" href="https://ris-bonn.example/ortsteil/endenich/">', page)
            self.assertIn("Radweg &lt;Endenicher&gt; Straße", page)
            self.assertIn('href="https://example.org/vo?x=1&amp;y=2" target="_blank" rel="noopener"', page)
            self.assertIn('href="../../?gebiet=ortsteil:endenich#261856"', page)
            self.assertFalse((site / "ortsteil" / "leer").exists())
            self.assertIn('href="../ortsteil/endenich/"', (site / "gebiete" / "index.html").read_text(encoding="utf-8"))
            urls = [e.text for e in ET.parse(site / seo.SITEMAP_SEITEN).getroot().iter(f"{{{seo.NS}}}loc")]
            self.assertIn("https://ris-bonn.example/ortsteil/endenich/", urls)
            self.assertIn("https://ris-bonn.example/gebiete/", urls)


class NeuerTab(unittest.TestCase):
    def test_nur_externe_links_ohne_target(self):
        html = ('<a href="https://www.bonn.de/plan.pdf">PDF</a> <a class="x" href="https://example.org/a" rel="license">L</a> '
                '<a href="../haushalt/">intern</a> <a href="https://ris-bonn.datenatlas.de/thema/">eigen</a> '
                '<a href="https://example.org/b" target="_self">fest</a> <a href="mailto:a@example.org">Mail</a>')
        out = gebietsseiten.neuer_tab(html)
        self.assertIn('<a href="https://www.bonn.de/plan.pdf" target="_blank" rel="noopener">PDF</a>', out)
        self.assertIn('<a class="x" href="https://example.org/a" rel="license" target="_blank">L</a>', out)
        for unveraendert in ('<a href="../haushalt/">', '<a href="https://ris-bonn.datenatlas.de/thema/">',
                             '<a href="https://example.org/b" target="_self">', '<a href="mailto:a@example.org">'):
            self.assertIn(unveraendert, out)
        self.assertEqual(gebietsseiten.neuer_tab(out), out)


if __name__ == "__main__":
    unittest.main()
