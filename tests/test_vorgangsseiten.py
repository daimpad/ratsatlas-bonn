"""Seiten je Vorgang (pipeline/vorgangsseiten.py) und die Regel, welche Vorlagen eine Seite erhalten (publish.has_page)."""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline import chat, publish, seo, vorgangsseiten


def _paper(ref, **kw):
    return {"reference": ref, "name": f"Titel {ref}", "paper_type": "Antrag", "date": "2026-05-04", "amt": None,
            "web": None, "main_file": None, "responsibility": [], "originators": [], "superordinated": [],
            "subordinated": [], "locations": [], "plans": [], "steps": [], "stand": "offen",
            "source_object": f"https://example.org/oparl/papers/{ref}", **kw}


ANTRAG = _paper(
    "261856", name="Radweg <Endenicher> Straße", seite=True, stand="entschieden",
    web="https://example.org/vo?x=1&y=2", main_file="https://example.org/doc.pdf",
    responsibility=[{"kind": "federfuehrend", "label": "66 Tiefbauamt", "name": "66-1 Verkehr", "derived": 0}],
    originators=[{"actor": "SPD-Fraktion", "actor_type": "Fraktion", "derived": 1}],
    locations=[{"level": "strasse", "name": "Endenicher Straße", "ortsteil": "Endenich", "stadtbezirk": "Bonn", "stage": "B",
                "evidence": "Endenicher Straße"}],
    steps=[{"typ": "beratung", "label": "Bezirksvertretung Bonn", "role": "Empfehlung", "date": "2026-06-02",
            "result": "abgelehnt"},
           {"typ": "entscheidung", "label": "Rat", "role": "Entscheidung", "date": "2026-07-03",
            "result": "ungeändert beschlossen"},
           {"typ": "folgevorlage", "label": "Stellungnahme der Verwaltung", "date": "2026-07-20"}],
    subordinated=[{"reference": "261856-01 ST", "paper_type": "Stellungnahme der Verwaltung", "name": "Stellungnahme",
                   "date": "2026-07-20"}],
    superordinated=[{"reference": "250001", "paper_type": "Antrag", "name": "Älterer Antrag", "date": "2025-01-10"}])
FOLGE = _paper("261856-01 ST", paper_type="Stellungnahme der Verwaltung", date="2026-07-20", seite=True,
               superordinated=[{"reference": "261856", "paper_type": "Antrag", "name": "Radweg", "date": "2026-05-04"}])
OHNE = _paper("250001", date="2025-01-10", stand="entschieden")   # ohne Feld „seite“


def _site(tmp):
    site = Path(tmp)
    base = site / "data" / "export" / "bonn"
    (base / "ortsteile").mkdir(parents=True)
    (base / "ohne-ortsbezug").mkdir()
    (base / "index.json").write_text(json.dumps({
        "ortsteile": [{"name": "Endenich", "slug": "endenich", "stadtbezirk": "Bonn", "count": 1}],
        "bezirke": [], "ohne_ortsbezug": [{"jahr": "2026", "count": 2}]}), encoding="utf-8")
    (base / "ortsteile" / "endenich.json").write_text(json.dumps({"meta": {}, "papers": [ANTRAG]}), encoding="utf-8")
    (base / "ohne-ortsbezug" / "2026.json").write_text(json.dumps({"meta": {}, "papers": [ANTRAG, FOLGE, OHNE]}),
                                                       encoding="utf-8")
    return site


class Regel(unittest.TestCase):
    def test_feedregel_ohne_einwohnerschaft(self):
        papers = [
            {"reference": "1", "paper_type": "Antrag", "name": "Radweg", "date": "2026-02-01", "stand": "entschieden",
             "superordinated": [], "subordinated": []},
            {"reference": "2", "paper_type": "Antrag", "name": "Alt, aber offen", "date": "2020-02-01", "stand": "offen",
             "superordinated": [], "subordinated": []},
            {"reference": "3", "paper_type": "Antrag", "name": "Alt und entschieden", "date": "2020-02-01",
             "stand": "entschieden", "superordinated": [], "subordinated": []},
            {"reference": "4", "paper_type": "Anregungen und Beschwerden", "name": "Ampel", "date": "2026-02-01",
             "stand": "offen", "superordinated": [], "subordinated": [{"reference": "4-01 ST"}]},
            {"reference": "4-01 ST", "paper_type": "Stellungnahme der Verwaltung", "name": "Stellungnahme",
             "date": "2026-03-01", "stand": "offen", "superordinated": [{"reference": "4"}], "subordinated": []},
        ]
        einwohner = set(chat.einwohner(papers))
        self.assertEqual([p["reference"] for p in papers if publish.has_page(p, "2025-01-01", einwohner)], ["1", "2"])


class Seiten(unittest.TestCase):
    def test_seiten_links_und_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = _site(tmp)
            seo.write(site, "https://ris-bonn.example/")
            page = (site / "vorgang" / "261856" / "index.html").read_text(encoding="utf-8")
            folge = (site / "vorgang" / "261856-01-st" / "index.html").read_text(encoding="utf-8")
            gebiet = (site / "ortsteil" / "endenich" / "index.html").read_text(encoding="utf-8")
            self.assertFalse((site / "vorgang" / "250001").exists())
            index = [e.text for e in ET.parse(site / "sitemap.xml").getroot().iter(f"{{{seo.NS}}}loc")]
            vorgaenge = ET.parse(site / seo.SITEMAP_VORGAENGE).getroot()
            seiten = (site / seo.SITEMAP_SEITEN).read_text(encoding="utf-8")
        self.assertEqual(index, ["https://ris-bonn.example/sitemap-seiten.xml",
                                 "https://ris-bonn.example/sitemap-vorgaenge.xml"])
        eintraege = {u.find(f"{{{seo.NS}}}loc").text: u.find(f"{{{seo.NS}}}lastmod").text for u in vorgaenge}
        # lastmod: jüngstes Datum aus der Quelle (hier die Folgevorlage), kein Erzeugungszeitpunkt
        self.assertEqual(eintraege, {"https://ris-bonn.example/vorgang/261856/": "2026-07-20",
                                     "https://ris-bonn.example/vorgang/261856-01-st/": "2026-07-20"})
        self.assertNotIn("/vorgang/", seiten)
        self.assertIn('<link rel="canonical" href="https://ris-bonn.example/vorgang/261856/">', page)
        self.assertIn("<h1>Radweg &lt;Endenicher&gt; Straße</h1>", page)
        # Karte im Gebiet, in dem die Vorlage zuerst steht (wie die Feeds)
        self.assertIn('href="../../?gebiet=ortsteil:endenich#261856"', page)
        self.assertIn('href="https://example.org/vo?x=1&amp;y=2" target="_blank" rel="noopener"', page)
        self.assertIn(">Dokument (PDF)</a>", page)
        self.assertIn('href="../../data/export/bonn/feeds/vorlagen/261856.xml"', page)
        self.assertIn("<dt>Federführend</dt><dd>66-1 Verkehr (66 Tiefbauamt)</dd>", page)
        self.assertIn('<dt>Eingereicht von</dt><dd>SPD-Fraktion <span class="pb-abgeleitet">abgeleitet</span></dd>', page)
        # Ort nur mit Namen, ohne Fundstelle; Ortsteil verlinkt auf die Gebietsseite
        self.assertIn('Endenicher Straße, <a href="../../ortsteil/endenich/">Endenich</a> <span class="pb-abgeleitet">', page)
        # Ergebnisse wörtlich, Folgevorlagen nicht in der Beratungsfolge
        self.assertIn("<strong>Rat</strong> (Entscheidung) – „ungeändert beschlossen“", page)
        self.assertEqual(page.count("<li><span class=\"pb-folge-datum\">"), 2)
        self.assertIn("Eine entscheidende Beratung hat ein abschließendes Ergebnis.", page)
        # Bezüge: mit Seite verlinkt, ohne Seite nur die Drucksache
        self.assertIn('<a href="../../vorgang/261856-01-st/">261856-01 ST</a>', page)
        self.assertIn("<li>250001: Älterer Antrag", page)
        self.assertIn('<a href="../../vorgang/261856/">261856</a>', folge)
        self.assertIn("<h2>Beratungsfolge</h2>\n    <p>Für diese Vorlage ist keine Beratung", folge)
        self.assertIn("Begriffe auf dieser Seite", page)
        self.assertNotRegex(page, r"<script")
        self.assertNotIn("Endenicher Straße\"", page)   # keine Fundstelle als Zitat
        # interne Links (Search Console 13.11.2026): die Gebietsseite verlinkt die Drucksache auf ihre Seite je Vorgang,
        # die Karte bleibt als Zusatz; Vorlagen ohne eigene Seite weiter auf die Karte
        self.assertIn('<a href="../../vorgang/261856/">261856</a>', gebiet)
        self.assertIn('<a href="../../?gebiet=ortsteil:endenich#261856">Karte</a>', gebiet)

    def test_themenseiten_verlinkt(self):
        from pipeline.themenseiten import verkehr
        with tempfile.TemporaryDirectory() as tmp:
            site = _site(tmp)
            d = site / "data" / "export" / "bonn" / "dossiers"
            d.mkdir()
            (d / f"{verkehr.THEMA.key}.json").write_text(json.dumps(
                {"straenge": [{"key": "rad", "vorlagen": [{"reference": "261856"}]},
                              {"key": "weitere", "vorlagen": [{"reference": "261856"}]}]}), encoding="utf-8")
            self.assertEqual(vorgangsseiten.themen_je_vorlage(d.parent),
                             {"261856": [(verkehr.THEMA.titel, verkehr.THEMA.pfad)]})
            vorgangsseiten.write(site, "https://ris-bonn.example/", lambda *a: a[4])
            page = (site / "vorgang" / "261856" / "index.html").read_text(encoding="utf-8")
            folge = (site / "vorgang" / "261856-01-st" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'<dt>Themenseite</dt><dd><a href="../../{verkehr.THEMA.pfad}">{verkehr.THEMA.titel}</a> '
                      '<span class="pb-abgeleitet">abgeleitet</span></dd>', page)
        self.assertNotIn("<dt>Themenseite</dt>", folge)

    def test_ohne_gebietsdaten_keine_seiten(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(vorgangsseiten.write(Path(tmp), "https://ris-bonn.example/", None), [])

    def test_titel_gekuerzt(self):
        lang = "Wort " * 40
        self.assertLessEqual(len(vorgangsseiten._kurz(lang)), vorgangsseiten.TITEL_MAX + 2)
        self.assertTrue(vorgangsseiten._kurz(lang).endswith(" …"))
        self.assertEqual(vorgangsseiten._kurz("kurz"), "kurz")


if __name__ == "__main__":
    unittest.main()
