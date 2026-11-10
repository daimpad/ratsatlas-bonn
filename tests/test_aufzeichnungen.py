"""Aufzeichnungen der Sitzungen (pipeline/aufzeichnungen.py): Abruf mit Zwischenspeicher ohne Netz, Verweise in
Prozesslinie und Vorgangsseite; nur Video-Adressen, kein Text der Transkripte (transkripte/KONZEPT.md)."""
import json
import sqlite3
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
                                          "aufzeichnung": "https://www.youtube.com/watch?v=XU9",
                                          "transkript_q": "Nordbrücke"})
        self.assertIn('class="aufz-karte"', zeile)
        self.assertIn('href="https://www.youtube.com/watch?v=XU9" target="_blank" rel="noopener">Video der Sitzung', zeile)
        self.assertIn('href="https://bonn.biz/ratstranskripte?q=Nordbr%C3%BCcke"', zeile)
        self.assertIn("Im Transkript suchen: „Nordbrücke“", zeile)
        self.assertIn('<span class="aufz-kurz">nicht amtlich</span>', zeile)
        self.assertIn("<summary>Mehr über die Ratstranskripte erfahren</summary>", zeile)
        ohne = vorgangsseiten._beratung({"date": "2026-03-12", "label": "Rat", "aufzeichnung": "https://www.youtube.com/watch?v=XU9"})
        self.assertIn('href="https://bonn.biz/ratstranskripte"', ohne)
        fremd = vorgangsseiten._beratung({"date": "2026-03-12", "label": "Rat", "aufzeichnung": "javascript:alert(1)"})
        self.assertNotIn("Video", fremd)


class Stichwort(unittest.TestCase):
    def test_wort(self):
        self.assertEqual(az.wort("Hubschrauberlandeplatz UKB"), "Hubschrauberlandeplatz")
        # Verfahrenswörter, Ziffern und kleingeschriebene Wörter zählen nicht
        self.assertEqual(az.wort("Stellungnahme der Verwaltung zur Änderung der Satzung"), "")
        self.assertEqual(az.wort("Bebauungsplan 6621-1 Nassestraße"), "Bebauungsplan")
        self.assertEqual(az.wort("Erarbeitung Lupenraum"), "Lupenraum")

    def test_nur_mit_treffer_in_derselben_sitzung(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            db = tmp / "t.sqlite"
            c = sqlite3.connect(db)
            c.executescript("""
                create table paper (id, reference, name, paper_type);
                create table paper_relation (parent_id, child_id, source);
                create table consultation (paper_id, meeting_id, agenda_item_id);
                create table agenda_item (id, public);
                insert into paper values ('p1', '260001', 'Sperrung der Nordbrücke', 'Antrag'),
                  ('p2', '260002', 'Hubschrauberlandeplatz UKB', 'Beschlussvorlage'),
                  ('p3', '260003', 'Bürgerantrag Musterstraße', 'Bürgerantrag § 24 GO - Öffentlich'),
                  ('p4', '260003-01', 'Stellungnahme Lärmschutzwand', 'Stellungnahme der Verwaltung'),
                  ('p5', '260005', 'Nichtöffentliche Grundstücksangelegenheit', 'Beschlussvorlage');
                insert into paper_relation values ('p3', 'p4', 'x');
                insert into agenda_item values ('a1', 1), ('a2', 1), ('a3', 1), ('a4', 1), ('a5', 0);
                insert into consultation values ('p1', 'https://x/meetings/7', 'a1'), ('p2', 'https://x/meetings/7', 'a2'),
                  ('p3', 'https://x/meetings/7', 'a3'), ('p4', 'https://x/meetings/7', 'a4'), ('p5', 'https://x/meetings/7', 'a5');
            """)
            c.commit()
            c.close()
            aufz = tmp / "aufzeichnungen.json"
            aufz.write_text(json.dumps({"7": {"lite_id": "L7", "video": "https://www.youtube.com/watch?v=a",
                                              "datum": "2026-03-12", "dauer_min": 1, "abschnitte": 1}}))
            datei = tmp / "stichworte.json"
            aufrufe = []

            def post(url, query, variables):
                aufrufe.append(variables["q"])
                ids = {"Nordbrücke": ["L7", "L9"], "Hubschrauberlandeplatz": ["L9"]}.get(variables["q"], [])
                return {"transcriptPassageSearch": {"totalCount": len(ids), "items": [
                    {"passage": {"revision": {"recording": {"meeting": {"id": i}}}}} for i in ids]}}

            with mock.patch.object(az, "DATEI", aufz), mock.patch.object(az, "STICHWORTE", datei), \
                    mock.patch.object(az, "PAUSE", 0):
                az._video_je_sitzung.cache_clear()
                az._stichwort_je_paar.cache_clear()
                az.fetch_stichworte(db=db, post=post, heute="2026-11-10", datei=datei)
                d = json.loads(datei.read_text())
                # Einwohnerschaft und ihre Folgevorlagen ohne Stichwort, nichtöffentliche Punkte nicht
                self.assertEqual(sorted(d["paare"]), ["260001|7", "260002|7"])
                self.assertEqual(sorted(aufrufe), ["Hubschrauberlandeplatz", "Nordbrücke"])
                self.assertTrue(d["paare"]["260001|7"]["treffer"])
                self.assertFalse(d["paare"]["260002|7"]["treffer"])
                self.assertEqual(az.stichwort("260001", "https://x/meetings/7"), "Nordbrücke")
                self.assertIsNone(az.stichwort("260002", "https://x/meetings/7"))
                # zweiter Lauf: keine neuen Anfragen
                aufrufe.clear()
                az.fetch_stichworte(db=db, post=post, heute="2026-11-11", datei=datei)
                self.assertEqual(aufrufe, [])
            az._video_je_sitzung.cache_clear()
            az._stichwort_je_paar.cache_clear()

if __name__ == "__main__":
    unittest.main()
