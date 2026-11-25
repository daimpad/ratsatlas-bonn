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

    def test_flurstueckskennzeichen_und_haus(self):
        # Prüfung 25.11.2026: Formen aus 202262-02, 190118, 220082, 230030 (Ziffern verändert), 220279
        m = self.m
        F = "[Flurstück ausgelassen]"
        self.assertEqual(m("Ecke Muffendorfer Straße, Kennung Flurstücke 05300100100123-05300100100124; DS 202262", "261847"),
                         f"Ecke Muffendorfer Straße, Kennung {F}; DS 202262")
        self.assertEqual(m("Peter-Schwingen-Straße, Flurstück 1234-12-123 (alt: 1900123)", "261847"),
                         f"Peter-Schwingen-Straße, {F} (alt: 1900123)")
        self.assertEqual(m("Gemarkung Beuel, Flur 3, Flurstücke 1234. 567 - Errichtung", "261847"),
                         f"Gemarkung Beuel, {F} - Errichtung")
        self.assertEqual(m("Gemarkung Ippendorf, Flur 4, Flurstücke 123/456, 78, 90, 1.234 und 5.678", "261847"),
                         f"Gemarkung Ippendorf, {F}")
        # Entscheidung 25.11.2026: Flurstücke in jedem Titel, Hausnummern nur bei geschützten Drucksachen
        self.assertEqual(m("Bebauungsplan, Flurstück 1234/5, Reichsstraße 12", "250001"), f"Bebauungsplan, {F}, Reichsstraße 12")
        self.assertTrue(m.offen("Bebauungsplan, Flurstück 1234/5", "250001"))
        self.assertTrue(m.offen(f"Kennung {F}05300100100123", "250001"))   # Rest hinter einer Auslassung
        self.assertTrue(m.offen(f"Gemarkung Beuel, {F}. 567", "250001"))
        self.assertFalse(m.offen("[Hausnummer ausgelassen], 53113 Bonn", "261847"))
        self.assertEqual(m("Friedhof Gemarkung Beuel,  Flur 12, Flurstücksnummer 34.", "250001"), "Friedhof Gemarkung Beuel,  [Flurstück ausgelassen].")
        # ältere Auslassungen in eingecheckten Audits: der Rest der Nummer fällt weg
        self.assertEqual(m(f"Kennung {F}05300100100123-05300100100124; DS", "250001"), f"Kennung {F}; DS")
        self.assertEqual(m(f"Gemarkung Beuel, {F}. 567 - Errichtung", "250001"), f"Gemarkung Beuel, {F} - Errichtung")
        self.assertEqual(m(f"Ippendorf, {F}.123 und 4.567", "250001"), f"Ippendorf, {F}")
        # „zwischen Haus 12 und …“
        self.assertEqual(m("Ernst-Moritz-Arndt-Straße zwischen Haus 12 und der Kreuzung", "261847"),
                         "Ernst-Moritz-Arndt-Straße zwischen [Hausnummer ausgelassen] und der Kreuzung")

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
        # Prüfung 25.11.2026: Federführung im Titel (190224, 190590), formal eine andere Stelle
        self.assertTrue(maske.privat({"amt_name": "Bezirksverwaltungsstelle Beuel", "name": "Grundstück in Bonn-Beuel (alt: 1900123NV1, FF: Amt 63)"}))
        self.assertTrue(maske.privat({"amt_name": "x", "name": "Neubau eines Hotels (FF: Amt 63; alt: 1900123)"}))
        self.assertFalse(maske.privat({"amt_name": "x", "name": "Bericht (alt: 1900123, FF: Amt 61)"}))
        self.assertFalse(maske.privat({"amt_name": "x", "name": "Bericht (FF: Amt 630)"}))
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
