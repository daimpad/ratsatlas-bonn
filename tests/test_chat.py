import unittest

from pipeline import chat, glossar, process as proc

LOC = {"level": "strasse", "name": "Frongasse", "ortsteil": "Endenich", "stadtbezirk": "Bonn", "lon": 7.07, "lat": 50.72,
       "stage": "B", "method": "strasse", "confidence": "mittel", "evidence": "Frongasse",
       "source_object": "https://example.org/papers/1", "source": "osm"}
PAPER = {
    "reference": "261088", "name": "Antrag: Bäume an der Frongasse", "paper_type": "Antrag", "date": "2026-06-02",
    "amt": "67 Amt für Umwelt und Stadtgrün", "web": "https://example.org/vo", "main_file": None,
    "source_object": "https://example.org/papers/1", "stand": "in Beratung", "parties": ["CDU"], "plans": [],
    "responsibility": [{"kind": "federfuehrend", "method": "underDirectionOf", "evidence": None, "derived": 0,
                        "label": "67 Amt für Umwelt und Stadtgrün", "name": "67-3 Stadtgrün"}],
    "originators": [{"actor": "CDU", "actor_type": "Bezirksfraktion", "organization_id": None, "method": "titel",
                     "evidence": "CDU-Bezirksfraktion", "derived": 1}],
    "themes": [{"theme": "umwelt", "method": "stichwort", "evidence": "bäume", "confidence": "niedrig"}],
    "process": [], "locations": [LOC, {**LOC, "stage": "A", "method": "oparl_location"}],
    "superordinated": [], "subordinated": [{"reference": "261088-01 ST", "paper_type": "Stellungnahme der Verwaltung",
                                             "name": "Stellungnahme", "date": "2026-08-31", "extra": 1}],
    "steps": [{"typ": "initiierung", "label": "Antrag", "status": "belegt", "source_object": "https://example.org/papers/1"}],
}


class Chat(unittest.TestCase):
    def test_kompakt_ohne_koordinaten_und_quellobjekt_je_schritt(self):
        d = chat.compact(PAPER)
        self.assertEqual(d["reference"], "261088")
        self.assertNotIn("lon", d["locations"][0])
        self.assertNotIn("source_object", d["steps"][0])
        self.assertEqual(d["subordinated"], [{"reference": "261088-01 ST", "paper_type": "Stellungnahme der Verwaltung",
                                              "name": "Stellungnahme", "date": "2026-08-31"}])
        self.assertIs(d["originators"][0]["derived"], True)

    def test_orte_je_ort_und_vorlage_einmal(self):
        out = chat.places([PAPER, {**PAPER, "reference": "261090"}])
        self.assertEqual(len(out), 1)
        self.assertEqual([p[0] for p in out[0]["papers"]], ["261090", "261088"])

    def test_titel_der_einwohnerschaft_ohne_wortteile(self):
        # Prüfung November 2026 (Nr. 35): „einwohner“, „anregung“ und „beschwerde“ als Wortteile erfassten 73 Drucksachen
        for t in ["Bürgerantrag: Tempo 30", "Stellungnahme zum Bürgerantrag 261847", "Einwohnerfrage: Bauvorhaben",
                  "Einwohnerfragen zur Sanierung", "Einwohnerantrag nach § 25 GO", "Anregungen und Beschwerden: Lärm"]:
            self.assertTrue(chat.EINWOHNER_TITEL.search(t), t)
        for t in ["Urteil zur Verfassungsbeschwerde gegen das GFG", "Weitergabe von Daten durch das Einwohnermeldeamt",
                  "Benennung von sachkundigen Einwohnerinnen und Einwohnern", "Feststellung der Einwohnerzahl",
                  "BBB-Anfrage zum Kulturgarten; hier: Lärmbeschwerden", "Rücknahme der Beschwerde gegen den Beschluss"]:
            self.assertFalse(chat.EINWOHNER_TITEL.search(t), t)

    def test_einwohner_mit_allen_vorlagen_des_vorgangs(self):
        antrag = {**PAPER, "reference": "221454", "paper_type": "Bürgerantrag § 24 GO - Öffentlich",
                  "subordinated": [{"reference": "221454-01 ST"}], "superordinated": []}
        stellung = {**PAPER, "reference": "221454-01 ST", "paper_type": "Stellungnahme der Verwaltung",
                    "name": "Bebauung an der Grimmgasse", "superordinated": [{"reference": "221454"}],
                    "subordinated": [{"reference": "221454-02"}]}
        mitteilung = {**PAPER, "reference": "221454-02", "paper_type": "Mitteilungsvorlage", "name": "Mitteilung",
                      "superordinated": [{"reference": "221454-01 ST"}], "subordinated": []}
        anderes = {**PAPER, "subordinated": [], "superordinated": []}
        self.assertEqual(chat.einwohner([antrag, stellung, mitteilung, anderes]),
                         ["221454", "221454-01 ST", "221454-02"])

    def test_teildatei_nach_praefix(self):
        self.assertEqual(chat.shard_key("261088-01 ST"), chat.shard_key("261088"))


class Glossar(unittest.TestCase):
    def test_eine_quelle_fuer_seite_und_pipeline(self):
        g = glossar.glossar()
        self.assertEqual(list(g["staende"]), list(proc.STAENDE))
        self.assertEqual(g["hinweise"], proc.NOTES)
        self.assertEqual(set(g["evidenz"]), {"belegt", "abgeleitet", "soll", "nicht_öffentlich", "unklar"})
        self.assertTrue(all(b["fundstelle"] for b in g["begriffe"]))


if __name__ == "__main__":
    unittest.main()
