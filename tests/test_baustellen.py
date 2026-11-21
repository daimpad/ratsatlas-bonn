import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from pipeline import baustellen


def feature(bid, von="01.10.2026", bis="31.12.2026", sperrung="keine Sperrung"):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.0712345678, 50.7298765432]},
            "properties": {"baustelle_id": bid, "bezeichnung": "Siemensstraße", "stadtbezirk_bez": "Bonn",
                           "adresse": "Siemensstraße 50", "von": von, "bis": bis, "traeger": "Bundesstadt Bonn - Amt 66-5",
                           "massnahme": "Straßenbau", "sperrung": sperrung}}


def fetcher(feeds, fail=()):
    """Nachgebildeter Abruf: feeds = {Thema: [Features]}, fail = Themen ohne gültige Antwort."""
    def run(thema):
        if thema in fail:
            raise RuntimeError(f"Thema {thema}: 10 Versuche ohne gültige Antwort")
        return feeds.get(thema, []), 1
    return run


class Abruf(unittest.TestCase):
    def test_wiederholt_bei_fehlern_und_prueft_anzahl(self):
        answers = [ValueError("HTTP 400"), {}, {"type": "FeatureCollection", "numberMatched": 2, "features": [feature(1)]},
                   {"type": "FeatureCollection", "numberMatched": 1, "features": [feature(1)]}]

        def opener(url):
            a = answers.pop(0)
            if isinstance(a, Exception):
                raise a
            return a
        feats, tries = baustellen.fetch(14403, tries=5, pause=0, opener=opener)
        self.assertEqual((len(feats), tries), (1, 4))
        with self.assertRaises(RuntimeError):
            baustellen.fetch(14403, tries=2, pause=0, opener=lambda url: {})

    def test_normalisierung(self):
        n = baustellen.normalize([feature(9746), {"properties": {}}])
        self.assertEqual(list(n), ["9746"])
        self.assertEqual((n["9746"]["lon"], n["9746"]["lat"]), (7.071235, 50.729877))


class Archiv(unittest.TestCase):
    def run_day(self, base, day, feeds, fail=()):
        return baustellen.archive(base, datetime.fromisoformat(f"{day}T05:00:00+00:00"), fetcher(feeds, fail))

    def test_neu_geaendert_entfallen(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            all_feeds = lambda f: {14403: f, 14698: f, 14755: f}
            rows = self.run_day(base, "2026-10-19", all_feeds([feature(1), feature(2)]))
            self.assertEqual(sorted((r[1], r[2]) for r in rows), [("1", "neu"), ("2", "neu")])
            # Termin verschoben, Baustelle 2 fehlt in einem Feed (Abruf fehlgeschlagen) → nicht entfallen
            rows = self.run_day(base, "2026-10-20", {14403: [feature(1, bis="31.03.2027")], 14698: [feature(1, bis="31.03.2027")]},
                                fail=(14755,))
            self.assertIn(["2026-10-20", "1", "geaendert", "bis", "31.12.2026", "31.03.2027",
                           "geplant_1_jahr,tagesaktuell"], rows)
            self.assertNotIn("entfallen", [r[2] for r in rows])
            self.assertIn("abruf_fehlgeschlagen", [r[2] for r in rows])
            # vollständiger Abruf ohne Baustelle 2 → entfallen
            rows = self.run_day(base, "2026-10-21", all_feeds([feature(1, bis="31.03.2027")]))
            self.assertEqual([(r[1], r[2]) for r in rows], [("2", "entfallen")])
            state = json.loads((base / "baustellen.json").read_text())
            self.assertEqual((state["1"]["first_seen"], state["1"]["last_seen"], state["2"]["aktiv"], state["2"]["entfallen"]),
                             ("2026-10-19", "2026-10-21", False, "2026-10-21"))
            self.assertEqual(state["1"]["aenderungen"][0]["feld"], "bis")
            # Momentaufnahmen nur bei geändertem Inhalt
            snaps = sorted(p.relative_to(base).as_posix() for p in (base / "snapshots").rglob("*.json"))
            self.assertIn("snapshots/2026/10/19/thema_14403.json", snaps)
            self.assertIn("snapshots/2026/10/20/thema_14403.json", snaps)
            self.assertNotIn("snapshots/2026/10/21/thema_14403.json", snaps)  # unverändert gegenüber 20.10.
            log = (base / "protokoll.tsv").read_text().splitlines()
            self.assertEqual(log[0].split("\t"), baustellen.LOG_HEAD)
            # Prüfung November 2026 (Nr. 33): alle Feeds antworten leer → nichts gilt als entfallen
            rows = self.run_day(base, "2026-10-22", all_feeds([]))
            self.assertEqual([(r[1], r[2]) for r in rows], [("", "abruf_leer")])
            self.assertTrue(json.loads((base / "baustellen.json").read_text())["1"]["aktiv"])

    def test_kein_feed_abrufbar(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.run_day(Path(tmp), "2026-10-19", {}, fail=(14403, 14698, 14755))


if __name__ == "__main__":
    unittest.main()
