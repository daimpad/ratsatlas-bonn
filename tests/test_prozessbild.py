"""Prozessbild der Themenseite (pipeline/prozessbild.py): Zeitachse, Punkte, Sitzungen mit Frist, Aufrufe."""
import tempfile
import unittest
from pathlib import Path

from pipeline import dossier, prozessbild
from pipeline.themenseiten.kultur import THEMA as K
from tests.test_dossier import vorlage

CACHE = {
    "a": vorlage("261285", "Gleichbehandlung der Kulturangebote", amt="01-2 Ratsbüro", gremien=("Kulturausschuss",),
                 result="geändert beschlossen"),
    "b": vorlage("261724", "Neufassung der Gebührenordnung der Stadtbibliothek", amt="42 Stadtbibliothek",
                 date="2026-09-22"),
    "c": vorlage("261677", "Erlass einer haushaltswirtschaftlichen Sperre", amt="20 Stadtkämmerei"),
}
for p in CACHE.values():
    p["stand"] = "entschieden" if p["reference"] == "261285" else "offen"
MEETINGS = [
    {"date": "2026-11-26", "time": "18:00", "gremium": "Ausschuss für Finanzen, Beteiligungen und Vergabe",
     "cancelled": False, "web": None, "source_object": "m1"},
    {"date": "2026-11-04", "time": "18:00", "gremium": "Bezirksvertretung Bad Godesberg", "cancelled": False,
     "web": None, "source_object": "m2"},
]


class Prozessbild(unittest.TestCase):
    def setUp(self):
        self.d = dossier.daten(K, CACHE, {"a": "ortsteil:endenich"}, MEETINGS, "2026-10-18", {})

    def test_daten(self):
        self.assertEqual([(p["nr"], p["reference"], p["art"], p["bahn"]) for p in self.d["punkte"]],
                         [(1, "261677", "offen", "rat"), (2, "261285", "entschieden", "kultur"),
                          (3, "261724", "offen", "rat")])  # ohne Beratungsfolge: Bahn des Rates am Tag der Vorlage
        frist = {s["source_object"]: (s["bahn"], s["frist"]) for s in self.d["sitzungen"]}
        self.assertEqual(frist, {"m1": ("finanz", "2026-11-05"), "m2": ("bv", "2026-10-14")})

    def test_zeitachse_zweigeteilt(self):
        self.assertEqual(prozessbild.Achse(K).x("2025-11-01"), prozessbild.LINKS)
        self.assertAlmostEqual(prozessbild.Achse(K).x("2027-04-01"), prozessbild.W - prozessbild.RECHTS)
        rueckblick = prozessbild.Achse(K).x("2026-02-01") - prozessbild.Achse(K).x("2026-01-01")
        demnaechst = prozessbild.Achse(K).x("2026-12-01") - prozessbild.Achse(K).x("2026-11-01")
        self.assertGreater(demnaechst, 1.8 * rueckblick)  # kommende Monate breiter

    def test_bild(self):
        svg = prozessbild.svg(K, self.d)
        self.assertIn("Stand 18.10.", svg)
        self.assertEqual(svg.count('href="#pb-hand"'), 2 + 1)  # zwei Sitzungen und die Legende
        self.assertIn("Frist für Anträge und Fragen zur Sitzung Ausschuss für Finanzen", svg)
        self.assertNotIn("zur Sitzung Bezirksvertretung Bad Godesberg", svg)  # Frist 14.10. schon vorbei
        self.assertIn("3 Beschlüsse und Anträge: 1 entschieden, 0 beraten", svg)

    def test_links_nur_auf_der_seite(self):
        svg = prozessbild.svg(K, self.d, "../../")
        self.assertNotIn('role="img"', svg)  # Kinder eines Bildes wären für Screenreader nicht erreichbar
        self.assertIn('<a class="pb-ziel" href="../../?gebiet=ortsteil:endenich#261285" aria-label="2: 261285 '
                      'Gleichbehandlung der Kulturangebote – entschieden (Kulturausschuss, 10.06.2026)" data-ziel="punkt-2" '
                      'data-strang="kultur_finanzen">', svg)
        self.assertIn('href="https://example.org/261724"', svg)  # ohne Gebiet: Original
        self.assertEqual(svg.count('href="#sitzungen"'), 2)  # ohne Tagesordnung: Terminliste der Seite
        self.assertEqual(svg.count('<a '), 3 + 2)  # ohne Terminplan 261064 bleiben die Phasen ohne Link
        ohne = prozessbild.svg(K, self.d)
        self.assertNotIn("<a ", ohne)
        self.assertIn('role="img"', ohne)
        self.assertNotIn("<a ", prozessbild.bild(K, self.d, "https://example.org/"))

    def test_sitzung_mit_tagesordnung_und_terminplan(self):
        meetings = [dict(MEETINGS[0], web="https://example.org/to/m1")]
        cache = dict(CACHE, h=vorlage("261064", "Rahmenterminplan Haushalt 2027/2028", amt="20 Stadtkämmerei"))
        d = dossier.daten(K, cache, {"h": "ohne:2026"}, meetings, "2026-10-18", {})
        svg = prozessbild.svg(K, d, "../../")
        self.assertIn('href="https://example.org/to/m1" aria-label="Ausschuss für Finanzen, Beteiligungen und '
                      'Vergabe, 26.11.2026: öffentliche Sitzung, Tagesordnung"', svg)
        self.assertEqual(svg.count('href="../../?gebiet=ohne:2026#261064"'), len(d["phasen"]))

    def test_detailfeld_daten_und_schalter(self):
        import json
        html = prozessbild.abschnitt(K, self.d, "../../")
        roh = html.split('<script type="application/json" id="pb-daten">')[1].split("</script>")[0]
        daten = json.loads(roh)
        p = daten["punkte"]["2"]
        self.assertEqual((p["reference"], p["strang"], p["paper_type"]),
                         ("261285", "Kulturförderung, Zuschüsse, Gebühren", "Beschlussvorlage"))
        self.assertEqual(p["beratungen"], [{"gremium": "Kulturausschuss", "date": "2026-06-10",
                                            "result": "geändert beschlossen", "cancelled": False}])
        self.assertEqual(p["karte"], "../../?gebiet=ortsteil:endenich#261285")
        self.assertEqual(len(daten["sitzungen"]), 2)
        self.assertIn('data-strang="kultur_finanzen" aria-pressed="true">Kulturförderung', html)
        self.assertNotIn('data-strang="buehnen"', html)  # Strang ohne Punkte: kein Schalter
        self.assertIn('class="pb-filter" role="group" aria-label="Stränge im Bild ein- und ausblenden" hidden', html)

    def test_detailfeld_daten_ohne_skriptende(self):
        d = dict(self.d, punkte=[dict(self.d["punkte"][0], name="Antrag </script><script>alert(1)</script>")])
        roh = prozessbild.detaildaten(K, d, "../../")
        self.assertNotIn("</", roh)

    def test_aufrufe_und_balken(self):
        html = prozessbild.abschnitt(K, self.d, "../../")
        # Kacheln ohne tagesaktuelle Termine und Fristen (Rückmeldung des Auftraggebers 10.11.2026)
        self.assertNotIn("Nächste offene Frist", html)
        self.assertNotIn("Nächste Sitzung:", html)
        self.assertIn('<h3 class="pb-filter-text">Stränge im Bild</h3>', html)
        self.assertIn('href="../../data/export/bonn/dossiers/kultur.ics"', html)
        self.assertIn('href="../../?gebiet=ortsteil:endenich#261285"', html)
        self.assertIn('title="1 entschieden"', html)
        self.assertIn('data-start="0.', html)


    def test_bild_zum_teilen(self):
        text = prozessbild.bild(K, self.d, "https://example.org/thema/kunst-und-kultur/")
        self.assertIn("Datenstand 18.10.2026", text)
        self.assertIn("https://example.org/thema/kunst-und-kultur/", text)
        self.assertIn('<svg x="0" y="74"', text)  # Zeitleiste eingebettet
        with tempfile.TemporaryDirectory() as tmp:
            png = prozessbild.schreibe_bild(K, self.d, Path(tmp), "https://example.org/")
            self.assertTrue((Path(tmp) / "kultur-zeitleiste.svg").exists())
            self.assertEqual(png, (Path(tmp) / "kultur-zeitleiste.png").exists())
            if png:
                self.assertEqual((Path(tmp) / "kultur-zeitleiste.png").read_bytes()[:4], b"\x89PNG")


if __name__ == "__main__":
    unittest.main()
