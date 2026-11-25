"""Zu- und Wegzüge (pipeline/wanderung.py): Auszug aus der Kreiswanderungsmatrix, Seite aus den Auszügen."""
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import gebietsseiten, wanderung


def zeile(herkunft, alter, z, f, ziel="05314", name="Kreis"):
    return {"zielkreis_ags": ziel, "herkunftskreis_ags": herkunft, "herkunftskreis": name, "herkunftsland": "Nordrhein-Westfalen",
            "alter": alter, "zuzug_ins_i": z, "fortzug_ins_i": f, "saldo_ins_i": "" if "" in (z, f) else str(int(z) - int(f))}


class Auszug(unittest.TestCase):
    def test_partner_und_alter(self):
        zeilen = [zeile("5382", "insgesamt", "3450", "5079", name="Rhein-Sieg-Kreis"),
                  zeile("5315", "insgesamt", "1465", "1637", name="Köln, Kreisfreie Stadt"),
                  zeile("9999", "insgesamt", "", "4"),                          # geheim gehalten
                  zeile("5382", "unter 18 Jahre", "10", "30"), zeile("5315", "unter 18 Jahre", "", "5"),
                  zeile("5314", "insgesamt", "1", "1", ziel="05382")]          # Bonn als Herkunft: nicht gezählt
        partner, alter = wanderung.auszug_matrix(zeilen)
        self.assertEqual([p["ags"] for p in partner], ["05382", "05315", "09999"])
        self.assertIsNone(partner[2]["zuzuege"])
        self.assertEqual(partner[0]["saldo"], -1629)
        u18 = next(a for a in alter if a["alter"] == "unter 18 Jahre")
        self.assertEqual((u18["zuzuege"], u18["fortzuege"], u18["saldo"]), (10, 35, -25))

    def test_wegweiser(self):
        antwort = {"years": [2021, 2022, 2023], "data": {"indicators": [{"regionYearValues": [[77.0, None, 79.3]]}]}}
        self.assertEqual(wanderung.zeitreihe_aus_wegweiser(antwort), [(2021, 77.0), (2023, 79.3)])

    def test_klassen(self):
        self.assertEqual(wanderung._klasse(-1629)[1], "−500 und weniger")
        self.assertEqual(wanderung._klasse(-20)[1], "−99 bis −20")
        self.assertEqual(wanderung._klasse(19)[1], "−19 bis +19")
        self.assertEqual(wanderung._klasse(500)[1], "+500 und mehr")
        self.assertEqual(wanderung._klasse(None)[1], "kein Austausch oder geheim")


class Seite(unittest.TestCase):
    def test_seite_aus_auszuegen(self):
        with tempfile.TemporaryDirectory() as tmp:
            o, site = Path(tmp) / "w", Path(tmp) / "site"
            o.mkdir()
            self.assertEqual(wanderung.write(site, "https://example.org/", gebietsseiten._page, o), [])   # ohne Daten keine Seite
            wanderung._tsv(o / "partner_2025.tsv", ["ags", "kreis", "land", "zuzuege", "fortzuege", "saldo"],
                           [{"ags": "05382", "kreis": "Rhein-Sieg-Kreis", "land": "Nordrhein-Westfalen", "zuzuege": 3450, "fortzuege": 5079, "saldo": -1629},
                            {"ags": "05315", "kreis": "Köln, Kreisfreie Stadt", "land": "Nordrhein-Westfalen", "zuzuege": 1465, "fortzuege": 1637, "saldo": -172}])
            wanderung._tsv(o / "alter_2025.tsv", ["alter", "zuzuege", "fortzuege", "saldo"],
                           [{"alter": a, "zuzuege": 10, "fortzuege": 20, "saldo": -10} for a in wanderung.ALTER])
            wanderung._tsv(o / "zeitreihe.tsv", ["indikator", "bezeichnung", "jahr", "wert"],
                           [{"indikator": k, "bezeichnung": k, "jahr": j, "wert": 70 + j - 2020} for k in ("zuzuege", "fortzuege") for j in (2021, 2022, 2023)])
            quadrat = lambda x: {"type": "Polygon", "coordinates": [[[x, 50], [x + 0.2, 50], [x + 0.2, 50.2], [x, 50.2], [x, 50]]]}
            (o / "kreise_region.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"ags": "05314", "name": "Bonn", "art": "Kreisfreie Stadt"}, "geometry": quadrat(7.0)},
                {"type": "Feature", "properties": {"ags": "05382", "name": "Rhein-Sieg-Kreis", "art": "Kreis"}, "geometry": quadrat(7.3)}]}))
            (o / "STAND.json").write_text(json.dumps({"abruf": "2026-11-24T12:00:00+00:00"}))
            self.assertEqual(wanderung.write(site, "https://example.org/", gebietsseiten._page, o), ["zu-und-wegzuege/"])
            html = (site / "zu-und-wegzuege" / "index.html").read_text()
            self.assertIn("4.915", html)            # Zuzüge gesamt
            self.assertIn("−1.801", html)           # Saldo gesamt
            self.assertIn("Rhein-Sieg-Kreis: 3.450 Zuzüge nach Bonn", html)
            self.assertIn("dl-de/by-2-0", html)
            self.assertIn("Melderegister", html)


class Robust(unittest.TestCase):
    """Prüfung 25.11.2026: unvollständiger Stand bricht die Veröffentlichung nicht ab."""

    def test_unvollstaendig(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "partner_2025.tsv").write_text("ags\tkreis\tland\tzuzuege\tfortzuege\tsaldo\n")
            self.assertIsNone(wanderung.lesen(ordner))
            self.assertEqual(wanderung.write(ordner, "https://example.org/", lambda *a: "", ordner), [])

    def test_satz_alter_aus_den_daten(self):
        alter = [{"alter": "unter 18 Jahre", "saldo": 5}, {"alter": "18 bis unter 25 Jahre", "saldo": -3}]
        satz = wanderung._satz_alter(alter)
        self.assertIn("Mehr Zuzüge als Fortzüge: unter 18 Jahre.", satz)
        self.assertNotIn("Studium", satz)


if __name__ == "__main__":
    unittest.main()
