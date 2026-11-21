"""Abruf: unvollständige Antworten ersetzen den vorhandenen Stand nicht (Code-Prüfung 23.10.2026)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import config, fetch


def pages(total, per_page, empty=()):
    """Nachgebildete OParl-Liste: Seite → Antwort."""
    n = -(-total // per_page)
    def get(url):
        p = int(url.split("page=")[1].split("&")[0])
        data = [] if p in empty else [{"id": f"x{(p - 1) * per_page + i}"}
                                      for i in range(min(per_page, total - (p - 1) * per_page))]
        return {"data": data, "pagination": {"totalPages": n, "totalElements": total}}
    return get


class Liste(unittest.TestCase):
    def test_vollstaendig(self):
        with mock.patch.object(fetch, "get_json", pages(250, 100)):
            self.assertEqual(len(fetch._oparl_list("u")), 250)

    def test_leere_seite_bricht_ab(self):
        with mock.patch.object(fetch, "get_json", pages(500, 100, empty={3})):
            with self.assertRaises(RuntimeError):
                fetch._oparl_list("u")

    def test_luecke_von_mehr_als_einer_seite_bricht_ab(self):
        # Prüfung November 2026 (Nr. 34): bisher durften 10 % fehlen (bei 25.000 Vorlagen rund 2.500)
        def kurz(fehlend):
            voll = pages(3000, 100)
            def get(url):
                d = voll(url)
                p = int(url.split("page=")[1].split("&")[0])
                if p > 1:   # jede weitere Seite liefert einige Objekte zu wenig, keine ist leer
                    d["data"] = d["data"][:len(d["data"]) - fehlend]
                return d
            return get
        with mock.patch.object(fetch, "get_json", kurz(2)):      # 58 fehlen: neue Objekte während des Abrufs
            self.assertEqual(len(fetch._oparl_list("u")), 3000 - 58)
        with mock.patch.object(fetch, "get_json", kurz(5)):      # 145 fehlen: mehr als eine Seite
            with self.assertRaises(RuntimeError):
                fetch._oparl_list("u")


class Stand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.papers = Path(self.tmp.name) / "papers.jsonl"
        self.papers.write_text("".join(json.dumps({"id": i}) + "\n" for i in range(100)))
        stand = Path(self.tmp.name) / "STAND.json"
        self.patch = [mock.patch.object(config, "PAPERS", self.papers), mock.patch.object(config, "STAND", stand)]
        for p in self.patch:
            p.start()

    def tearDown(self):
        for p in self.patch:
            p.stop()
        self.tmp.cleanup()

    def test_deutlich_weniger_vorlagen_ersetzen_den_stand_nicht(self):
        with mock.patch.object(fetch, "_oparl_list", lambda url: [{"id": i} for i in range(50)]):
            with self.assertRaises(RuntimeError):
                fetch.fetch_papers()
        self.assertEqual(fetch._jsonl_count(self.papers), 100)

    def test_mehr_vorlagen_ersetzen_den_stand(self):
        with mock.patch.object(fetch, "_oparl_list", lambda url: [{"id": i} for i in range(101)]):
            fetch.fetch_papers()
        self.assertEqual(fetch._jsonl_count(self.papers), 101)
        self.assertFalse(self.papers.with_name("papers.jsonl.tmp").exists())


class Overpass(unittest.TestCase):
    def test_vermerk_zur_zeitueberschreitung_gilt_als_fehler(self):
        antwort = {"elements": [{"id": 1}], "remark": "runtime error: Query timed out in \"query\" at line 1"}
        with mock.patch.object(fetch, "post_form", lambda url, fields, tries: antwort):
            with self.assertRaises(RuntimeError):
                fetch._overpass("q")


class Ortsangaben(unittest.TestCase):
    def test_hausnummern_der_stadt_werden_auf_die_strasse_reduziert(self):
        from pipeline.build import ohne_hausnummer
        self.assertEqual(ohne_hausnummer("Kölnstraße 12a, 53111 Bonn"), "Kölnstraße, 53111 Bonn")
        self.assertEqual(ohne_hausnummer("Endenicher Allee 11 - 13"), "Endenicher Allee")
        self.assertEqual(ohne_hausnummer("Markt"), "Markt")
        self.assertIsNone(ohne_hausnummer(None))


if __name__ == "__main__":
    unittest.main()
