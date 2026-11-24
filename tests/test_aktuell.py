"""Block „Aktuell“ im Startfenster (export._aktuell): Auswahl und Reihenfolge der Sitzungen und Vorlagen."""
import unittest

from pipeline import export


def sitzung(datum, zeit="18:00", gremium="Rat", abgesagt=False):
    return {"date": datum, "time": zeit, "gremium": gremium, "web": "https://example.org/to", "cancelled": abgesagt,
            "source_object": f"m-{datum}-{gremium}"}


class Aktuell(unittest.TestCase):
    def test_sitzungen_ab_heute_ohne_abgesagte(self):
        ms = [sitzung("2026-11-10"), sitzung("2026-11-17", "18:00", "B"), sitzung("2026-11-17", "17:00", "A"),
              sitzung("2026-11-18", abgesagt=True), sitzung("2026-11-19")]
        a = export._aktuell({}, {}, {}, ms, "2026-11-17")
        self.assertEqual([m["gremium"] for m in a["sitzungen"]], ["A", "B", "Rat"])
        self.assertEqual(a["sitzungen"][0]["frist"], "2026-10-27")   # 21 Tage vorher

    def test_vorlagen_nach_datum_mit_ort(self):
        cache = {1: {"reference": "262001", "date": "2026-11-15", "paper_type": "Antrag", "name": "A"},
                 2: {"reference": "262003", "date": "2026-11-16", "paper_type": "Anfrage", "name": "B", "seite": True},
                 3: {"reference": "262004", "date": "2026-12-01", "paper_type": "Antrag", "name": "zukünftig"},
                 4: {"reference": "262002", "date": "2026-11-16", "paper_type": None, "name": "C"}}
        home = {1: "ortsteil:endenich", 2: "ohne:2026", 4: "bezirk:beuel"}
        names = {"ortsteil:endenich": "Endenich", "ohne:2026": "stadtweit / ohne Ortsbezug 2026",
                 "bezirk:beuel": "Stadtbezirk Beuel, ohne genaueren Ort"}
        v = export._aktuell(cache, home, names, [], "2026-11-17")["vorlagen"]
        self.assertEqual([x["reference"] for x in v], ["262003", "262002", "262001"])
        self.assertEqual([x["ort"] for x in v], ["stadtweit / ohne Ortsbezug", "Stadtbezirk Beuel", "Endenich"])
        self.assertTrue(v[0]["seite"])

    def test_letzte_aufzeichnung(self):
        ms = [{**sitzung("2026-11-12"), "video": "https://www.youtube.com/watch?v=a"},
              {**sitzung("2026-12-12"), "video": "https://www.youtube.com/watch?v=b"}, sitzung("2026-11-16")]
        self.assertEqual(export._aktuell({}, {}, {}, ms, "2026-11-17")["video"],
                         {"date": "2026-11-12", "gremium": "Rat", "video": "https://www.youtube.com/watch?v=a"})
        self.assertIsNone(export._aktuell({}, {}, {}, [sitzung("2026-11-16")], "2026-11-17")["video"])


if __name__ == "__main__":
    unittest.main()
