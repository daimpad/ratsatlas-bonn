"""Aufzeichnungen der Sitzungen (pipeline/aufzeichnungen.py): Abruf mit Zwischenspeicher ohne Netz, Verweise in
Prozesslinie und Vorgangsseite; nur Video-Adressen, kein Text der Transkripte (transkripte/KONZEPT.md)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import aufzeichnungen as az
from pipeline import vorgangsseiten


def _post(antworten, aufrufe):
    def post(url, query, variables):
        aufrufe.append(variables)
        if "meetingByIdRef" in query:
            return {"meetingByIdRef": {"id": f"lite-{variables['r']}"} if variables["r"] != "9" else None}
        rec = antworten.get(variables["m"])
        return {"transcriptPassages": {"totalCount": 3 if rec else 0,
                                       "items": [{"revision": {"recording": rec}}] if rec else []}}
    return post


class Abruf(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raw = Path(self._tmp.name)
        (self.raw / "meetings.json").write_text(json.dumps([
            {"id": "https://x/oparl/meetings/1", "name": "Sitzung des Rates", "start": "2026-03-12T17:00:00+01:00"},
            {"id": "https://x/oparl/meetings/2", "name": "Sitzung des Rates", "start": "2026-09-24T17:00:00+02:00"},
            {"id": "https://x/oparl/meetings/3", "name": "Sitzung der Bezirksvertretung Bonn", "start": "2026-05-01"},
            {"id": "https://x/oparl/meetings/4", "name": "Sitzung des Rates", "start": "2026-05-07", "cancelled": True},
            {"id": "https://x/oparl/meetings/5", "name": "Sitzung des Rates", "start": "2027-01-20"},
            {"id": "https://x/oparl/meetings/9", "name": "Sitzung des Hauptausschusses", "start": "2026-06-01"},
        ]))
        self.datei = self.raw / "aufzeichnungen.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _lauf(self, antworten, alle=False, heute="2026-11-10"):
        aufrufe = []
        with mock.patch.object(az.config, "RAW", self.raw), mock.patch.object(az, "PAUSE", 0):
            az.fetch(alle=alle, post=_post(antworten, aufrufe), heute=heute, datei=self.datei)
        return json.loads(self.datei.read_text()), aufrufe

    def test_nur_rat_und_hauptausschuss_vergangen_nur_youtube(self):
        d, _ = self._lauf({"lite-1": {"sourceUrl": "https://www.youtube.com/watch?v=a", "durationMs": "600000"},
                           "lite-2": {"sourceUrl": "https://example.org/fremd", "durationMs": "1"}})
        self.assertEqual(sorted(d), ["1", "2", "9"])          # ohne Bezirksvertretung, abgesagte und künftige
        self.assertEqual((d["1"]["video"], d["1"]["dauer_min"], d["1"]["abschnitte"]), ("https://www.youtube.com/watch?v=a", 10, 3))
        self.assertEqual(d["2"]["video"], "")                   # fremde Adresse wird nicht übernommen
        self.assertEqual(d["9"]["lite_id"], "")                 # Sitzung in OParl-Lite unbekannt

    def test_zwischenspeicher_fragt_nur_offene_erneut(self):
        self._lauf({"lite-1": {"sourceUrl": "https://www.youtube.com/watch?v=a", "durationMs": "0"}})
        _, aufrufe = self._lauf({}, heute="2026-11-11")
        # Sitzung 1 hat ein Video und wird nicht erneut abgefragt; 2 und 9 ohne Aufzeichnung aus dem letzten Jahr schon
        self.assertEqual(sorted(v["r"] for v in aufrufe if "r" in v), ["2", "9"])
        _, aufrufe = self._lauf({}, heute="2028-01-01")
        # 2 und 9 älter als ein Jahr: nicht mehr ohne --alle; 5 (20.01.2027) ist inzwischen vergangen und neu
        self.assertEqual([v["r"] for v in aufrufe if "r" in v], ["5"])
        _, aufrufe = self._lauf({}, alle=True, heute="2028-01-01")
        self.assertEqual(sorted(v["r"] for v in aufrufe if "r" in v), ["1", "2", "5", "9"])

    def test_fehler_behalten_den_stand(self):
        self._lauf({"lite-1": {"sourceUrl": "https://www.youtube.com/watch?v=a", "durationMs": "0"}})

        def kaputt(*a):
            raise OSError("nicht erreichbar")
        with mock.patch.object(az.config, "RAW", self.raw), mock.patch.object(az, "PAUSE", 0):
            az.fetch(alle=True, post=kaputt, heute="2026-11-12", datei=self.datei)
        self.assertEqual(json.loads(self.datei.read_text())["1"]["video"], "https://www.youtube.com/watch?v=a")


class Verweise(unittest.TestCase):
    def test_video_je_sitzung_und_vorgangsseite(self):
        with mock.patch.object(az, "_video_je_sitzung", lambda: {"2005576": "https://www.youtube.com/watch?v=XU9"}):
            self.assertEqual(az.video("https://www.bonn.sitzung-online.de/oparl/meetings/2005576"),
                             "https://www.youtube.com/watch?v=XU9")
            self.assertIsNone(az.video("https://www.bonn.sitzung-online.de/oparl/meetings/1"))
            self.assertIsNone(az.video(None))
        zeile = vorgangsseiten._beratung({"date": "2026-03-12", "label": "Rat", "result": "geändert beschlossen",
                                          "aufzeichnung": "https://www.youtube.com/watch?v=XU9"})
        self.assertIn('href="https://www.youtube.com/watch?v=XU9" target="_blank" rel="noopener">Video der Sitzung</a>', zeile)
        self.assertIn('href="https://bonn.biz/ratstranskripte"', zeile)
        self.assertIn("automatisch erkannt, nicht amtlich", zeile)
        fremd = vorgangsseiten._beratung({"date": "2026-03-12", "label": "Rat", "aufzeichnung": "javascript:alert(1)"})
        self.assertNotIn("Video", fremd)


if __name__ == "__main__":
    unittest.main()
