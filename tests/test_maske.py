"""Hausnummern in Titeln aus der Einwohnerschaft (pipeline/maske.py; Entscheidung 24.10.2026: überall ausblenden)."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pipeline import check, maske

STRASSEN = ["Reichsstraße", "Endenicher Straße", "An der Nesselburg"]


class Maske(unittest.TestCase):
    def setUp(self):
        self.m = maske.Maske({"261847", "231681-12 ST"}, STRASSEN)

    def test_nur_vorlagen_aus_der_einwohnerschaft(self):
        t = "Bürgerantrag: im Bereich Reichsstraße 12 in Bonn-Röttgen"
        self.assertEqual(self.m(t, "261847"), "Bürgerantrag: im Bereich Reichsstraße [Hausnummer ausgelassen] in Bonn-Röttgen")
        self.assertEqual(self.m("Sanierung Reichsstraße 12", "250001"), "Sanierung Reichsstraße 12")

    def test_bereiche_buchstaben_und_endungen(self):
        m = self.m
        self.assertEqual(m("Endenicher Straße 308 und 328", "261847"), "Endenicher Straße [Hausnummer ausgelassen]")
        self.assertEqual(m("Vor der Hausnr. An der Nesselburg 18a", "261847"), "Vor der Hausnr. An der Nesselburg [Hausnummer ausgelassen]")
        # unbekannte Straße, erkannt an der Endung; Postleitzahl bleibt
        self.assertEqual(m("Kapitelshof 3, 53229 Bonn", "231681-12 ST"), "Kapitelshof [Hausnummer ausgelassen], 53229 Bonn")
        self.assertEqual(m("Tempo 30 in der Reichsstraße", "261847"), "Tempo 30 in der Reichsstraße")
        # Lücke 01.11.2026: Nummer hinter „Hausnummer“, „Haus-Nr.“, „Haus Nr.“ oder „Straße Nr.“
        self.assertEqual(m("Endenicher Allee in Höhe der Hausnummer 82", "261847"), "Endenicher Allee in Höhe der [Hausnummer ausgelassen]")
        self.assertEqual(m("vor Haus-Nr. 264 und Haus Nr. 5", "261847"), "vor [Hausnummer ausgelassen] und [Hausnummer ausgelassen]")
        self.assertEqual(m("zwischen den Hausnummern 36 bis 40", "261847"), "zwischen den [Hausnummer ausgelassen]")
        self.assertEqual(m("Reichsstraße Nr. 12", "261847"), "Reichsstraße [Hausnummer ausgelassen]")
        self.assertEqual(m("Reichsstraße (neben Haus-Nr.) 68 - Neubau", "261847"), "Reichsstraße (neben [Hausnummer ausgelassen]) - Neubau")
        self.assertTrue(m.offen("vor der Hausnummer 82", "261847"))
        self.assertFalse(m.offen("vor der Hausnummer 82", "250001"))
        self.assertIsNone(m(None, "261847"))

    def test_aufzaehlungen_haeuser_und_flurstuecke(self):
        # Prüfung November 2026 (Nr. 5, 28): Formen aus 241240, 240963, 200240 und Flurstücke; gleich in tools.js
        m = self.m
        A = "[Hausnummer ausgelassen]"
        self.assertEqual(m("im Bereich Reichsstraße 12 oder 14-16", "261847"), f"im Bereich Reichsstraße {A}")
        self.assertEqual(m("Promenadenweg vor den Häusern Nr. 73 - 89", "261847"), f"Promenadenweg vor den {A}")
        self.assertEqual(m("Ostseestr. 3 + 5, Gotenstr. 7 sowie 9 & 11", "261847"), f"Ostseestr. {A}, Gotenstr. {A}")
        self.assertEqual(m("Hofstr 12 in Bonn", "261847"), f"Hofstr {A} in Bonn")
        # schon nach älteren Regeln ausgeblendet (eingecheckte Audits): der Rest der Aufzählung fällt weg
        self.assertEqual(m(f"Reichsstraße {A} oder 14-16", "261847"), f"Reichsstraße {A}")
        self.assertEqual(m("Gemarkung Beuel, Flur 3, Flurstück 1234/5 und 77 - Garage", "261847"),
                         "Gemarkung Beuel, [Flurstück ausgelassen] - Garage")
        # bleibt: Postleitzahl, Jahr, Plannummer, Liniennummern ohne Straße
        for t in ["Reichsstraße 2025", "Bebauungsplan Nr. 7923-2 Reichsstraße", "Buslinien 601, 602 oder 603",
                  f"Kapitelshof {A}, 53229 Bonn"]:
            self.assertEqual(m(t, "261847"), t)
            self.assertFalse(m.offen(t, "261847"), t)
        self.assertTrue(m.offen("Flurstück 12", "261847"))
        # Gegenprobe (Warnliste): Zahl kurz hinter einem Straßenwort, die keine Regel erfasst
        self.assertTrue(m.moeglich("Reichsstraße in Höhe 12", "261847"))
        self.assertFalse(m.moeglich(f"Reichsstraße {A} - Neubau von 12 Wohnungen im 3. Obergeschoss", "261847"))
        self.assertFalse(m.moeglich("Reichsstraße in Höhe 12", "250001"))

    def test_tsv_dateien_nachziehen(self):
        # Prüfung November 2026 (Nr. 2): einmalig gezogene Prüfbögen trugen volle Titel; je Zelle, Urteile bleiben
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "bonn").mkdir()
            (base / "pruef").mkdir()
            kopf = "nr\tdrucksache\ttitel\tlink\tstrasse\tzahl\turteil\n"
            zeilen = ("1\t261847\tBürgerantrag: Reichsstraße 12\thttps://x/VO020?VOLFDNR=12\tReichsstraße\t7\trichtig\n"
                      "2\t250001\tSanierung Reichsstraße 12\thttps://x\tReichsstraße\t7\tfalsch\n")
            (base / "pruef" / "stichprobe.tsv").write_text(kopf + zeilen)
            (base / "bonn" / "kurzfassungen.tsv").write_text(kopf + zeilen)
            self.assertEqual(maske.tsv_offen(base / "pruef" / "stichprobe.tsv", self.m), ["261847"])
            self.assertEqual(check.tsv_mit_hausnummer(self.m, base), ["bonn/kurzfassungen.tsv (1)", "pruef/stichprobe.tsv (1)"])
            self.assertEqual(maske.bestand(self.m, base), {"pruef/stichprobe.tsv": 1})
            neu = (base / "pruef" / "stichprobe.tsv").read_text().splitlines()
            self.assertEqual(neu[1], "1\t261847\tBürgerantrag: Reichsstraße [Hausnummer ausgelassen]\thttps://x/VO020?VOLFDNR=12\tReichsstraße\t7\trichtig")
            self.assertEqual(neu[2], zeilen.splitlines()[1])   # andere Drucksache unverändert, „Reichsstraße<Tab>7“ kein Treffer
            self.assertEqual(maske.bestand(self.m, base), {})   # zweiter Lauf ändert nichts
            self.assertEqual((base / "bonn" / "kurzfassungen.tsv").read_text(), kopf + zeilen)   # bonn/ prüft check.py

    def test_pruefung_von_kurzfassungen_und_fundstellen(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "ortsteile").mkdir()
            (base / "kurzfassungen.tsv").write_text("drucksache\tkurzfassung\n261847\tZwischen den Hausnummern 5 und 9 soll geparkt werden.\n"
                                                    "250001\tDie Verwaltung schlägt einen Radweg vor.\n")
            self.assertEqual(check.kurzfassungen_mit_hausnummer(base), ["261847"])
            vorlage = {"reference": "261847", "name": "Bürgerantrag Reichsstraße [Hausnummer ausgelassen]",
                       "originators": [{"evidence": "Bürgerantrag Reichsstraße 12"}], "responsibility": [], "plans": [],
                       "superordinated": [], "subordinated": [{"reference": "231681-12 ST", "name": "Stellungnahme Reichsstraße 5"}]}
            (base / "ortsteile" / "x.json").write_text(json.dumps({"papers": [vorlage]}))
            (base / "plaene.json").write_text(json.dumps({"plaene": [{"vorlagen": [
                {"drucksache": "261847", "titel": "Bürgerantrag", "fundstelle": "Bebauungsplan Reichsstraße 12"}]}]}))
            self.assertEqual(check.felder_mit_hausnummer(self.m, base), ["231681-12 ST", "261847"])
            (base / "suche.json").write_text(json.dumps({"rows": [["261847", "Reichsstraße in Höhe 12"]]}))
            self.assertEqual(check.moegliche_hausnummern(self.m, base), ["261847"])

    def test_kette_ueber_folgevorlagen(self):
        db = sqlite3.connect(":memory:")
        db.executescript("""CREATE TABLE paper (id TEXT, reference TEXT, paper_type TEXT, name TEXT);
            CREATE TABLE paper_relation (parent_id TEXT, child_id TEXT);
            INSERT INTO paper VALUES ('a', '231681', 'Bürgerantrag § 24 GO - Öffentlich', 'Bürgerantrag Reichsstraße 5'),
              ('b', '231681-12 ST', 'Stellungnahme der Verwaltung', 'Stellungnahme Reichsstraße 5'),
              ('c', '250001', 'Beschlussvorlage', 'Sanierung Reichsstraße 5');
            INSERT INTO paper_relation VALUES ('a', 'b');""")
        m = maske.aus_db(db, STRASSEN)
        self.assertEqual(m("Stellungnahme Reichsstraße 5", "231681-12 ST"), "Stellungnahme Reichsstraße [Hausnummer ausgelassen]")
        self.assertEqual(m("Sanierung Reichsstraße 5", "250001"), "Sanierung Reichsstraße 5")

    def test_pruefung_findet_offene_titel(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "suche.json").write_text(json.dumps({"rows": [["261847", "Reichsstraße 12"], ["250001", "Reichsstraße 12"]]}))
            (base / "vorlagen.geojson").write_text(json.dumps({"features": [
                {"properties": {"reference": "261847", "name": "Reichsstraße [Hausnummer ausgelassen]"}}]}))
            self.assertEqual(check.titel_mit_hausnummer(self.m, base), ["261847"])


if __name__ == "__main__":
    unittest.main()


class BauordnungUndNaturschutz(unittest.TestCase):
    """Erweiterung 26.10.2026: Titel aus Bauordnungsamt und Unterer Naturschutzbehörde ohne Hausnummer."""

    def test_federfuehrung(self):
        self.assertTrue(maske.privat({"amt_name": "63-1 Allgemeine Verwaltungs- und Beitragsangelegenheiten"}))
        self.assertTrue(maske.privat({"amt": "67 Amt für Umwelt und Stadtgrün",
                                      "responsibility": [{"kind": "federfuehrend", "name": "67-6 Untere Naturschutzbehörde"}]}))
        self.assertTrue(maske.privat({"amt_name": "56-3 Untere Naturschutzbehörde"}))
        self.assertFalse(maske.privat({"amt_name": "61 Stadtplanungsamt"}))
        # Prüfung November 2026 (Nr. 28): Fällgenehmigungen für private Bäume auch bei anderer Federführung
        self.assertTrue(maske.privat({"amt_name": "Bezirksverwaltungsstelle Bonn", "name": "Erteilte Fällgenehmigungen für private Bäume"}))
        self.assertFalse(maske.privat({"amt_name": "Bezirksverwaltungsstelle Bonn", "name": "Baumfällungen im Stadtwald"}))
        self.assertFalse(maske.privat({"amt_name": "630 Sonstiges"}))
        self.assertFalse(maske.privat({"amt": "67 Amt für Umwelt und Stadtgrün",
                                       "responsibility": [{"kind": "fachlich", "name": "67-6 Untere Naturschutzbehörde"}]}))

    def test_aus_db_mit_amt(self):
        db = sqlite3.connect(":memory:")
        db.executescript("""CREATE TABLE organization (id TEXT, name TEXT);
            CREATE TABLE paper (id TEXT, reference TEXT, paper_type TEXT, name TEXT, under_direction_of TEXT);
            CREATE TABLE paper_relation (parent_id TEXT, child_id TEXT);
            INSERT INTO organization VALUES ('o1', '63-1 Allgemeine Verwaltung'), ('o2', '61 Stadtplanungsamt');
            INSERT INTO paper VALUES ('a', '261900', 'Beschlussvorlage', 'Grundstück in Bonn, Reichsstraße 5 - Anbau', 'o1'),
              ('b', '261900-01 ST', 'Stellungnahme der Verwaltung', 'Anfrage Reichsstraße 5', 'o2'),
              ('c', '261901', 'Beschlussvorlage', 'Sanierung Reichsstraße 5', 'o2');
            INSERT INTO paper_relation VALUES ('a', 'b');""")
        m = maske.aus_db(db, STRASSEN)
        self.assertEqual(m("Grundstück in Bonn, Reichsstraße 5 - Anbau", "261900"),
                         "Grundstück in Bonn, Reichsstraße [Hausnummer ausgelassen] - Anbau")
        self.assertEqual(m("Anfrage Reichsstraße 5", "261900-01 ST"), "Anfrage Reichsstraße [Hausnummer ausgelassen]")
        self.assertEqual(m("Sanierung Reichsstraße 5", "261901"), "Sanierung Reichsstraße 5")
