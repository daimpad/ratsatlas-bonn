import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline import anliegen


def meldung(nr, tag="2026-10-26", code="1.5", name="Wilde Müllkippe", status="closed", stufe="Erledigt / Beauftragt"):
    return {"service_request_id": nr, "requested_datetime": f"{tag}T13:05:58+01:00", "status": status,
            "service_code": code, "service_name": name, "lat": 50.7267, "long": 7.0732,
            "description": "Container überfüllt, Kennzeichen BN-AB 123, Hausnummer 7",
            "address_string": "53121 Bonn, Magdalenenstraße 7", "media_url": "/api/images/x.jpg",
            "status_notes": "Ihr Anliegen wurde beauftragt.",
            "extended_attributes": {"markaspot": {"status_descriptive_name": stufe, "media_alt_text": ["Person vor Haus"]}}}


class Orte:
    def locate(self, lon, lat):
        return {"ortsteil_bez": "Endenich", "bezirk_bez": "Bonn"} if lon > 7 else None


def fetcher(monate, fail=()):
    def run(first):
        if f"{first:%Y-%m}" in fail:
            raise RuntimeError(f"{first:%Y-%m}: 3 Versuche ohne vollständige Antwort")
        items = monate.get(f"{first:%Y-%m}", [])
        return items, len(items)
    return run


class Abruf(unittest.TestCase):
    def test_seitenweise_und_gegen_gesamtzahl_geprueft(self):
        seiten = {0: [meldung(f"{i}-2026") for i in range(500)], 500: [meldung("900-2026")]}
        urls = []

        def opener(url):
            urls.append(url)
            off = int(url.rsplit("offset=", 1)[1])
            return {"requests": seiten[off], "meta": {"total": 501}}
        items, total = anliegen.fetch_month(date(2026, 10, 1), opener=opener, pause=0)
        self.assertEqual((len(items), total), (501, 501))
        self.assertIn("start_date=2026-10-01", urls[0])
        self.assertIn("end_date=2026-10-31T23%3A59%3A59", urls[0])

    def test_unvollstaendig_wird_wiederholt_dann_fehler(self):
        with self.assertRaises(RuntimeError):
            anliegen.fetch_month(date(2026, 2, 1), opener=lambda url: {"requests": [meldung("1-2026")], "meta": {"total": 2}},
                                 tries=2, pause=0)


class Archiv(unittest.TestCase):
    def test_speichert_nur_kategorie_tag_ortsteil_status(self):
        m = anliegen.normalize(meldung("44312-2026"), Orte())
        self.assertEqual(m, {"nummer": "44312-2026", "tag": "2026-10-26", "kategorie_code": "1.5",
                             "kategorie": "Wilde Müllkippe", "gruppe": "Abfall", "ortsteil": "Endenich",
                             "stadtbezirk": "Bonn", "status": "closed", "status_name": "Erledigt / Beauftragt"})
        self.assertEqual(anliegen.normalize(meldung("1-2026", code="2.3"), Orte())["gruppe"], "Stadtbild und Grün")
        self.assertEqual(anliegen.normalize(meldung("1-2026", code="4.0"), Orte())["gruppe"], "Straßen und Verkehr")
        ohne = meldung("2-2026"); ohne["long"] = 6.9
        self.assertEqual(anliegen.normalize(ohne, Orte())["ortsteil"], "")

    def test_erster_lauf_ab_beginn_dann_fenster_und_keine_texte(self):
        with tempfile.TemporaryDirectory() as d:
            gefragt = []
            def run(first):
                gefragt.append(first)
                return fetcher({"2021-11": [meldung("1-2021", tag="2021-11-23")],
                                "2026-10": [meldung("44312-2026", status="open", stufe="Unbearbeitet")]})(first)
            anliegen.archive(d, now=datetime(2026, 10, 28, 5, tzinfo=timezone.utc), fetcher=run, ortsteile=Orte())
            self.assertEqual(gefragt[0], date(2021, 11, 1))
            self.assertEqual(len(gefragt), 60)
            text = (Path(d) / "anliegen" / "meldungen.tsv").read_text(encoding="utf-8")
            for verboten in ("Magdalenenstraße", "BN-AB", "beauftragt.", "50.72", "7.07", "jpg", "Person"):
                self.assertNotIn(verboten, text)
            # zweiter Lauf: nur die Monate der letzten 120 Tage; Status geändert, erstes Auftreten bleibt
            gefragt.clear()
            rows = anliegen.archive(d, now=datetime(2026, 10, 29, 5, tzinfo=timezone.utc),
                                    fetcher=lambda f: (gefragt.append(f), fetcher({"2026-10": [meldung("44312-2026")]})(f))[1],
                                    ortsteile=Orte())
            self.assertEqual(gefragt[0], date(2026, 7, 1))
            state = anliegen.read_state(Path(d) / "anliegen" / "meldungen.tsv")
            self.assertEqual(state["44312-2026"]["erstmals_gesehen"], "2026-10-28")
            self.assertEqual(state["44312-2026"]["zuletzt_gesehen"], "2026-10-29")
            self.assertEqual(state["44312-2026"]["status"], "closed")
            self.assertEqual(state["1-2021"]["zuletzt_gesehen"], "2026-10-28")   # nicht mehr abgefragt, bleibt erhalten
            self.assertIn(["2026-10-29", "2026-10", 1, 1, 0, 1, ""], rows)
            self.assertEqual(list(state), ["1-2021", "44312-2026"])

    def test_fehlgeschlagener_monat_wird_protokolliert(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "anliegen").mkdir()
            anliegen.write_state(Path(d) / "anliegen" / "meldungen.tsv",
                                 {"5-2026": {**anliegen.normalize(meldung("5-2026"), Orte()),
                                             "erstmals_gesehen": "2026-10-01", "zuletzt_gesehen": "2026-10-01"}})
            rows = anliegen.archive(d, now=datetime(2026, 10, 28, tzinfo=timezone.utc),
                                    fetcher=fetcher({}, fail={"2026-09"}), ortsteile=Orte())
            self.assertTrue(any(r[1] == "2026-09" and r[6] for r in rows))
            with self.assertRaises(SystemExit):
                anliegen.archive(d, now=datetime(2026, 10, 28, tzinfo=timezone.utc),
                                 fetcher=fetcher({}, fail={f"2026-{m:02d}" for m in range(6, 11)}), ortsteile=Orte())



class Seite(unittest.TestCase):
    def test_zaehlt_90_tage_rundet_kleine_werte_und_meldet_beginn(self):
        with tempfile.TemporaryDirectory() as d:
            st = {}
            for i in range(4):
                st[f"{i}-2026"] = {**anliegen.normalize(meldung(f"{i}-2026", tag="2026-10-20"), Orte()),
                                   "erstmals_gesehen": "2026-10-28", "zuletzt_gesehen": "2026-10-28"}
            st["9-2026"] = {**anliegen.normalize(meldung("9-2026", tag="2026-10-20", code="3.6"), Orte()),
                            "erstmals_gesehen": "2026-10-28", "zuletzt_gesehen": "2026-10-28"}
            st["1-2025"] = {**anliegen.normalize(meldung("1-2025", tag="2025-01-05"), Orte()),   # außerhalb der 90 Tage
                            "erstmals_gesehen": "2026-10-28", "zuletzt_gesehen": "2026-10-28"}
            (Path(d) / "anliegen").mkdir()
            anliegen.write_state(Path(d) / "anliegen" / "meldungen.tsv", st)
            (Path(d) / "anliegen" / "STAND.json").write_text('{"abruf": "2026-10-28T05:30:00+00:00", "archiv_beginn": "2026-10-28"}')
            out = Path(d) / "anliegen.json"
            doc = anliegen.seite(d, out)
            self.assertEqual(doc["ortsteile"]["Endenich"], {"Abfall": 4, "Stadtbild und Grün": "unter 3",
                                                           "Straßen und Verkehr": "unter 3", "gesamt": "mindestens 4"})
            # Prüfung November 2026 (Nr. 28): die genaue Summe (5) hätte den verdeckten Wert (1) verraten
            self.assertEqual(anliegen._zaehlen([{"gruppe": "Abfall"}] * 5 + [{"gruppe": "Stadtbild und Grün"}] * 3
                                               + [{"gruppe": "Straßen und Verkehr"}] * 4)["gesamt"], 12)
            self.assertEqual(anliegen._zaehlen([{"gruppe": "Abfall"}] * 2 + [{"gruppe": "Stadtbild und Grün"}] * 2)["gesamt"],
                             "mindestens 3")
            self.assertEqual(anliegen._zaehlen([{"gruppe": "Abfall"}] * 2)["gesamt"], "unter 3")
            self.assertEqual((doc["meta"]["von"], doc["meta"]["bis"]), ("2026-07-31", "2026-10-28"))
            self.assertEqual(doc["meta"]["unvollstaendig_vor"], "2026-10-28")
            self.assertNotIn("9-2026", out.read_text(encoding="utf-8"))
            self.assertEqual(anliegen.pruefen(out), [])

    def test_ohne_archiv_keine_datei(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "anliegen.json"
            out.write_text("{}")
            self.assertIsNone(anliegen.seite(Path(d) / "fehlt", out))
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
