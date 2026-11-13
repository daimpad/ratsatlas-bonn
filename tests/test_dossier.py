"""Themenseite „Kunst und Kultur“ (pipeline/dossier.py): Regeln der Stränge, Daten und Seite."""
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pipeline import dossier, gebietsseiten
from pipeline.themenseiten.kultur import THEMA as K


def vorlage(ref, name, amt=None, date="2026-06-01", gremien=(), result=None):
    return {"reference": ref, "name": name, "amt": amt, "date": date, "paper_type": "Beschlussvorlage",
            "stand": "offen", "web": f"https://example.org/{ref}",
            "process": [{"gremium": g, "start_date": "2026-06-10T16:00:00Z", "result": result, "cancelled": False}
                        for g in gremien]}


CACHE = {
    "a": vorlage("261677", "Erlass einer haushaltswirtschaftlichen Sperre", amt="20 Stadtkämmerei"),
    "b": vorlage("260127-05", "Zukunft der Bonner Bühnen, Änderungsantrag", amt="01-2 Ratsbüro", date="2024-01-01"),
    "c": vorlage("261033", "Umstellung der institutionellen Förderung auf Festbetragsfinanzierung", amt="41 Kulturamt"),
    "d": vorlage("261285", "Gleichbehandlung der Kulturangebote", amt="01-2 Ratsbüro", gremien=("Kulturausschuss",),
                 result="beschlossen"),
    "e": vorlage("261500", "Ausstellung im Stadtmuseum", amt="41 Kulturamt"),
    "f": vorlage("261501", "Sanierung einer Schule", amt="40 Schulamt"),
    "g": vorlage("250001", "Förderung von Kulturprojekten", amt="41 Kulturamt", date="2025-10-31"),
    "h": vorlage("261064", "Rahmenterminplan für die Einbringung der Haushaltssatzung 2027/2028", amt="20 Stadtkämmerei"),
    "i": vorlage("240986", "Einbringung der Haushaltssatzung 2025/2026", date="2024-09-01"),
    "j": vorlage("240986-01 AA", "Änderungsantrag zur Haushaltssatzung", date="2024-10-01"),
}
MEETINGS = [
    {"date": "2026-10-01", "time": "18:00", "gremium": "Kulturausschuss", "cancelled": False, "web": None, "source_object": "m0"},
    {"date": "2026-12-01", "time": "18:00", "gremium": "Kulturausschuss", "cancelled": False, "web": None, "source_object": "m1"},
    {"date": "2026-12-02", "time": None, "gremium": "Rat", "cancelled": True, "web": None, "source_object": "m2"},
    {"date": "2026-12-03", "time": "17:00", "gremium": "Rat", "cancelled": False, "web": None, "source_object": "m3"},
    {"date": "2026-12-04", "time": "17:00", "gremium": "Schulausschuss", "cancelled": False, "web": None, "source_object": "m4"},
]


class Straenge(unittest.TestCase):
    def setUp(self):
        self.d = dossier.daten(K, CACHE, {"a": "ohne:2026", "d": "ortsteil:endenich"}, MEETINGS, "2026-10-25", {})
        self.by = {s["key"]: [r["reference"] for r in s["vorlagen"]] for s in self.d["straenge"]}

    def test_zuordnung(self):
        self.assertEqual(self.by["haushalt"], ["261677", "261064"])  # gleiches Datum: Drucksache absteigend
        self.assertEqual(self.by["buehnen"], ["260127-05"])  # Stammnummer gilt auch vor Beginn der Wahlperiode
        self.assertEqual(self.by["kultur_finanzen"], ["261285", "261033"])
        self.assertEqual(self.by["kultur_weitere"], ["261500"])  # ohne Geldbezug im Titel

    def test_ausgeschlossen(self):
        alle = {r for refs in self.by.values() for r in refs}
        self.assertNotIn("261501", alle)  # anderes Amt, kein Kulturgremium
        self.assertNotIn("250001", alle)  # vor Beginn der Wahlperiode
        self.assertNotIn("240986", alle)

    def test_grund_mit_ganzem_wort(self):
        rows = {r["reference"]: r for s in self.d["straenge"] for r in s["vorlagen"]}
        self.assertEqual(rows["261033"]["grund"], "federführend: 41 Kulturamt; Titel: „Förderung“")
        self.assertEqual(rows["261285"]["grund"], "Beratung im Kulturausschuss; Titel: „Gleichbehandlung“")
        self.assertEqual(rows["261677"]["grund"], "Titel: „haushaltswirtschaftlichen“")
        self.assertEqual(rows["261285"]["letzte_beratung"],
                         {"gremium": "Kulturausschuss", "date": "2026-06-10", "result": "beschlossen"})

    def test_sitzungen_und_vergleich(self):
        self.assertEqual([m["source_object"] for m in self.d["sitzungen"]], ["m1", "m3"])
        self.assertEqual(self.d["vergleich"]["vorlagen"], 2)
        self.assertEqual(self.d["terminplan"]["reference"], "261064")


class RegelnNachPruefung(unittest.TestCase):
    """Prüfung im Gespräch 25.10.2026 (kultur/PRUEFUNG.md)."""

    def setUp(self):
        cache = {
            "a": vorlage("260756", "Volt-Antrag: Bürger:innenrat im Prozess „Zukunft der Bonner Bühnen“",
                         amt="01-2 Ratsbüro", gremien=("Kulturausschuss",)),
            "b": vorlage("260756-01 AA", "Änderungsantrag zum Bürgerrat", amt="01-2 Ratsbüro"),
            "c": vorlage("260949", "Absage des Kultur- und Begegnungsfestes 2026", amt="05 Amt für Integration und Vielfalt"),
            "d": vorlage("260949-01 ST", "Stellungnahme der Verwaltung", amt="05 Amt für Integration und Vielfalt"),
            "e": vorlage("260798", "Controllingbericht der Stabsstelle Beethovenhalle für das I.–IV. Quartal 2025",
                         amt="II-1 Stabsstelle Konferenzzentrum/Beethovenhalle"),
            "f": vorlage("250500", "Zukunft der Bonner Bühnen (alte Wahlperiode)", date="2025-03-01"),
            "h": vorlage("260148", "Sitzungstermine des Ausschusses für Finanzen 2026",
                         amt="II-1 Stabsstelle Konferenzzentrum/Beethovenhalle"),
            "g": vorlage("261500", "Ausstellung im Stadtmuseum", amt="41 Kulturamt"),
            "i": vorlage("261861", "Grünen-Antrag: Zukunft des Schauspiels", amt="01-2 Ratsbüro",
                         gremien=("Kulturausschuss",)),
        }
        self.d = dossier.daten(K, cache, {}, [], "2026-10-25", {})
        self.rows = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_buehnen_ganzes_verfahren(self):
        self.assertEqual(self.rows["260756"], ("buehnen", "Verfahren 260756; Titel: „Bühnen“"))
        self.assertEqual(self.rows["260756-01 AA"][0], "buehnen")  # Folgevorlage ohne Wort im Titel
        self.assertNotIn("250500", self.rows)  # vor Beginn der Wahlperiode
        self.assertEqual(self.rows["261861"], ("buehnen", "Verfahren 261861; Titel: „Schauspiels“"))

    def test_kulturfest_und_beethovenhalle(self):
        self.assertEqual(self.rows["260949"][0], "kultur_finanzen")
        self.assertEqual(self.rows["260949-01 ST"][0], "kultur_finanzen")
        self.assertEqual(self.rows["260798"], ("kultur_finanzen", "federführend: II-1 Stabsstelle "
                                                "Konferenzzentrum/Beethovenhalle; Titel: „Controllingbericht“"))
        self.assertNotIn("260148", self.rows)  # Stabsstelle ohne „Beethovenhalle“ im Titel

    def test_weitere_eingeklappt(self):
        weitere = next(s for s in self.d["straenge"] if s["key"] == "kultur_weitere")
        self.assertTrue(weitere["eingeklappt"])
        html = dossier.body(K, self.d, "../../")
        self.assertIn("<details>\n      <summary>Alle 1 Vorlagen anzeigen</summary>", html)
        self.assertEqual(html.count("<details>"), 1)


class Seite(unittest.TestCase):
    def test_seite_und_sitemap_pfad(self):
        d = dossier.daten(K, CACHE, {"d": "ortsteil:endenich"}, MEETINGS, "2026-10-25", {})
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            src = site / "data" / "export" / "bonn" / "dossiers" / "kultur.json"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(d))
            self.assertEqual(dossier.write(K, site, "https://example.org/", gebietsseiten._page), [K.pfad])
            html = (site / K.pfad / "index.html").read_text()
        self.assertIn('<link rel="canonical" href="https://example.org/thema/kunst-und-kultur/">', html)
        self.assertIn('href="../../?gebiet=ortsteil:endenich#261285"', html)
        self.assertIn("Kulturausschuss 10.06.2026: beschlossen", html)
        self.assertIn("01.12.2026, 18:00 Uhr: Kulturausschuss", html)
        self.assertNotIn("o. Ä..", html)
        self.assertNotIn("og:image", html)  # ohne PNG kein Vorschaubild

    def test_drucksache_mit_eigener_seite(self):
        # interne Links für Suchmaschinen (13.11.2026): Drucksache → Seite je Vorgang, Karte als Zusatz;
        # ohne eigene Seite bleibt der Link auf die Karte
        cache = {**CACHE, "d": {**CACHE["d"], "seite": True}}
        d = dossier.daten(K, cache, {"d": "ortsteil:endenich", "c": "ohne:2026"}, MEETINGS, "2026-10-25", {})
        zeilen = {r["reference"]: r for s in d["straenge"] for r in s["vorlagen"]}
        self.assertTrue(zeilen["261285"]["seite"])
        self.assertNotIn("seite", zeilen["261033"])
        self.assertIn('<td><a href="../../vorgang/261285/">261285</a></td>', dossier._row("../../", zeilen["261285"]))
        self.assertIn('<a href="../../?gebiet=ortsteil:endenich#261285">Karte</a>', dossier._row("../../", zeilen["261285"]))
        ohne = dossier._row("../../", zeilen["261033"])
        self.assertIn('<td><a href="../../?gebiet=ohne:2026#261033">261033</a></td>', ohne)
        self.assertNotIn(">Karte</a>", ohne)

    def test_ohne_daten_keine_seite(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dossier.write(K, Path(tmp), "https://example.org/", gebietsseiten._page), [])


class Stichprobe(unittest.TestCase):
    def test_zuordnung_und_gegenprobe_einmalig(self):
        d = dossier.daten(K, CACHE, {}, MEETINGS, "2026-10-25", {})
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "kultur.json").write_text(json.dumps(d))
            db = sqlite3.connect(tmp / "db.sqlite")
            db.executescript("""CREATE TABLE paper (id TEXT, reference TEXT, paper_type TEXT, name TEXT, date TEXT, web TEXT);
                INSERT INTO paper VALUES ('x', '261900', 'Antrag', 'Kulturfestival im Park', '2026-05-01', NULL),
                  ('y', '261900-01 ST', 'Stellungnahme der Verwaltung', 'Kulturfestival im Park', '2026-06-01', NULL),
                  ('z', '261901', 'Antrag', 'Sanierung Kunstrasenplatz', '2026-05-01', NULL),
                  ('w', '261285', 'Antrag', 'Gleichbehandlung der Kulturangebote', '2026-06-01', NULL);""")
            db.commit()
            db.close()
            out = tmp / "stichprobe.tsv"
            dossier.stichprobe(K, tmp / "kultur.json", out, db_path=tmp / "db.sqlite")
            with out.open(encoding="utf-8") as f:
                rows = list(csv.reader(f, delimiter="\t"))
            ohne = [r[1] for r in rows[1:] if r[6] == "nicht zugeordnet"]
            self.assertEqual(ohne, ["261900"])  # eine Vorlage je Verfahren, kein Kunstrasen, nichts Zugeordnetes
            self.assertEqual(len(rows) - 1, 6 + 1)  # alle 6 zugeordneten (je Strang höchstens die Sollzahl) + 1
            out.write_text("geprüft")
            dossier.stichprobe(K, tmp / "kultur.json", out, db_path=tmp / "db.sqlite")
            self.assertEqual(out.read_text(), "geprüft")


if __name__ == "__main__":
    unittest.main()


class GremiumDerSitzung(unittest.TestCase):
    """Sitzungen ohne Organisation (export.gremium_der_sitzung): Name aus dem Sitzungstitel, bei gleichem Namen ohne
    Satzzeichen in der Schreibweise des bekannten Gremiums (Sitzung am 25.11.2026: „Kinder-, Jugend“)."""

    def test_ausweichname(self):
        from pipeline.export import gremium_der_sitzung
        names = {"gr/6": "Ausschuss für Kinder, Jugend und Familie", "gr/352": "Beirat Kinder- und Jugendbeteiligung"}
        m = {"name": "Sitzung des Ausschusses für Kinder-, Jugend und Familie", "organization": None}
        self.assertEqual(gremium_der_sitzung(m, names), "Ausschuss für Kinder, Jugend und Familie")
        m = {"name": "Sitzung des Beirates Kinder- und Jugendbeteiligung"}
        self.assertEqual(gremium_der_sitzung(m, names), "Beirat Kinder- und Jugendbeteiligung")
        m = {"name": "Sitzung des Ausschusses für Neues", "organization": ["gr/999"]}
        self.assertEqual(gremium_der_sitzung(m, names), "Ausschuss für Neues")
        self.assertEqual(gremium_der_sitzung({"name": "x", "organization": ["gr/6"]}, names),
                         "Ausschuss für Kinder, Jugend und Familie")
