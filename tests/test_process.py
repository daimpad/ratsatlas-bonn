import unittest

from pipeline import process


def cons(gremium, role="Empfehlung", authoritative=False, start=None, result=None, status="beraten"):
    return {"gremium": gremium, "role": role, "authoritative": authoritative, "start_date": start,
            "result": result, "status": status, "number": None}


def paper(ptype="Beschlussvorlage", process_=(), subordinated=(), originators=(), date="2024-03-01"):
    return {"paper_type": ptype, "date": date, "source_object": "oparl/papers/1",
            "process": list(process_), "subordinated": list(subordinated),
            "originators": [{"actor": a} for a in originators]}


def typen(p):
    return [s["typ"] for s in process.steps(p)]


class Steps(unittest.TestCase):
    def test_verwaltungsvorlage_hat_nichtoeffentliche_vorbereitung(self):
        steps = process.steps(paper())
        self.assertEqual(typen(paper()), ["initiierung", "vorbereitung", "veroeffentlichung"])
        self.assertEqual(steps[1]["status"], "nicht_öffentlich")

    def test_antrag_ohne_vorbereitung(self):
        self.assertNotIn("vorbereitung", typen(paper("Antrag", originators=["CDU"])))

    def test_beratung_mit_lite_datum_ist_abgeleitet_und_sortiert(self):
        p = paper(process_=[cons("Rat", "Entscheidung", True, "2024-05-02T17:00:00", "ungeändert beschlossen"),
                            cons("Hauptausschuss", start="2024-04-10T17:00:00", result="vertagt")])
        steps = process.steps(p)
        mid = [s for s in steps if s["typ"] in ("beratung", "entscheidung")]
        self.assertEqual([s["label"] for s in mid], ["Hauptausschuss", "Rat"])
        self.assertTrue(all(s["date_status"] == "abgeleitet" for s in mid))
        self.assertTrue(mid[0].get("schleife"))
        self.assertEqual(steps[-1]["typ"], "vollzug")
        self.assertEqual(steps[-1]["status"], "unklar")

    def test_beratung_ohne_sitzung_bleibt_als_luecke(self):
        s = [x for x in process.steps(paper(process_=[cons("Rat", status="")])) if x["typ"] == "beratung"][0]
        self.assertEqual((s["date"], s["date_status"], s["note"]), (None, "unklar", "ohne_sitzung"))

    def test_kein_vollzug_ohne_beschluss(self):
        p = paper(process_=[cons("Rat", "Entscheidung", True, "2024-05-02", "zur Kenntnis genommen")])
        self.assertNotIn("vollzug", typen(p))

    def test_sonderweg_und_nichtoeffentlich(self):
        self.assertEqual(process.steps(paper("Dringlichkeitsentscheidung OB"))[0]["note"], "sonderweg")
        t = typen(paper(process.NICHTOEFFENTLICH_TYPE))
        self.assertIn("beratung", t)

    def test_folgevorlage_undatiert_ans_ende_der_mitte(self):
        p = paper(subordinated=[{"paper_type": "Stellungnahme der Verwaltung", "reference": "1-01",
                                 "name": "x", "date": None}])
        self.assertEqual(typen(p)[-1], "folgevorlage")


class StandUndWeg(unittest.TestCase):
    def test_stand(self):
        self.assertEqual(process.stand(paper()), "ohne Beratungsfolge")
        self.assertEqual(process.stand(paper(process_=[cons("Rat")])), "offen")
        self.assertEqual(process.stand(paper(process_=[cons("BV", result="ungeändert beschlossen"), cons("Rat")])),
                         "in Beratung")
        self.assertEqual(process.stand(paper(process_=[cons("Rat", "Entscheidung", True,
                                                            result="geändert beschlossen")])), "entschieden")

    def test_vertagt_ist_nicht_entschieden(self):
        p = paper(process_=[cons("Rat", "Entscheidung", True, result="vertagt")])
        self.assertEqual(process.stand(p), "in Beratung")

    def test_ohne_abstimmung_ist_nicht_entschieden(self):
        for r in ("nicht abgestimmt", "ohne Votum - mit Maßgabe", "zurückgezogen"):   # 25.11.2026
            p = paper(process_=[cons("Rat", "Entscheidung", True, result=r)])
            self.assertEqual(process.stand(p), "beraten, ohne Entscheidung", r)
        p = paper(process_=[cons("Rat", "Entscheidung", True, result="weitere Lesung erforderlich")])
        self.assertEqual(process.stand(p), "in Beratung")

    def test_kenntnisnahme_ohne_entscheidung(self):
        p = paper("Mitteilungsvorlage", process_=[cons("BV Bonn", "Kenntnisnahme", result="zur Kenntnis genommen")])
        self.assertEqual(process.stand(p), "beraten, ohne Entscheidung")

    def test_path_key(self):
        p = paper(process_=[cons("BV Bonn", "Anhörung"),
                            cons("Rat", "Entscheidung", True, result="geändert beschlossen")])
        self.assertEqual(process.path_key(p),
                         (("BV Bonn (Anhörung)", "Rat (Entscheidung)"), "geändert beschlossen", "ergebnis"))
        self.assertEqual(process.path_key(paper(process_=[cons("Rat")]))[1:], ("offen", "stand"))


class Datum(unittest.TestCase):
    def test_local_day_utc_nach_mitternacht(self):
        self.assertEqual(process.local_day("2024-05-02T22:30:00.000Z"), "2024-05-03")
        self.assertEqual(process.local_day("2024-05-02T17:00:00.000Z"), "2024-05-02")
        self.assertEqual(process.local_day("2019-11-26T18:00:00+01:00"), "2019-11-26")
        self.assertIsNone(process.local_day(None))

    def test_ergebnis_ohne_sitzung_hat_kein_abgeleitetes_datum(self):
        s = [x for x in process.steps(paper(process_=[cons("Rat", result="vertagt")])) if x["typ"] == "beratung"][0]
        self.assertEqual((s["date"], s["date_status"], s["note"], s["result_source"]),
                         (None, "unklar", None, "oparl-lite"))

    def test_beratung_vor_datum_der_vorlage_wird_markiert(self):
        p = paper(date="2024-06-01", process_=[cons("Rat", start="2024-03-01T17:00:00Z", result="vertagt")])
        s = [x for x in process.steps(p) if x["typ"] == "beratung"][0]
        self.assertEqual(s["note"], "datum_vor_vorlage")

    def test_undatierte_beratung_folgt_der_vorigen(self):
        p = paper(process_=[cons("BV", start="2024-04-01T17:00:00Z", result="vertagt"), cons("HA"),
                            cons("Rat", "Entscheidung", True, "2024-05-02T17:00:00Z", "zur Kenntnis genommen")],
                  subordinated=[{"paper_type": "Stellungnahme der Verwaltung", "reference": "1-01",
                                 "name": "x", "date": "2024-04-20"}])
        mid = [x["label"] if x["typ"] != "folgevorlage" else "FV" for x in process.steps(p)
               if x["typ"] in ("beratung", "entscheidung", "folgevorlage")]
        self.assertEqual(mid, ["BV", "HA", "FV", "Rat"])


if __name__ == "__main__":
    unittest.main()
