"""Allgemeine Themenseiten (pipeline/themenseiten/, dossier.py, prozessbild.py): Die Kulturseite bleibt nach dem
Umbau Zeichen für Zeichen gleich (Referenz in tests/referenz/, erzeugt vor dem Umbau am 26.10.2026; am 27.10.2026 um
die Abschnitte „Haushalt im Produktbereich“ und „Wer berät mit“ sowie die Sprungleiste und den Link auf haushalt/ ergänzt,
am 28.10.2026 um target="_blank" an externen Links, die Feed-Erkennung im Kopf und den Link auf rss/, am 02.11.2026 um den
Link in die Kachel des Produktbereichs auf haushalt/ und das Akkordeon „Begriffe auf dieser Seite“, im Fuß der Link
auf einfach/, am 05.11.2026 im Fuß der Verweis „Teil des Ratsatlas“ auf ratsatlas.de); dazu die
Regeln der Zuordnung und ein Thema ohne Phasen."""
import json
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline import dossier, gebietsseiten, prozessbild
from pipeline.themenseiten import ALLE, kultur
from tests.test_dossier import vorlage
from tests.test_prozessbild import CACHE, MEETINGS

REFERENZ = Path(__file__).parent / "referenz"


# Besetzung des Fachausschusses fest vorgegeben (die Datei data/raw/besetzung.json ändert sich mit jedem Abruf)
AUSSCHUSS = {"name": "Kulturausschuss", "id": "17", "mitglieder": 21, "ohne_fraktion": 9, "sachkundig": 9, "stichtag": "2026-10-27",
             "vorsitz": [{"name": "Anna Beispiel", "rolle": "Vorsitz", "fraktion": "Beispiel-Fraktion"}],
             "sitze": [{"fraktion": "Beispiel-Fraktion", "n": 7}, {"fraktion": "Andere Fraktion", "n": 5}]}


def _kultur_daten():
    alt, dossier.fachausschuss = dossier.fachausschuss, lambda t, **kw: AUSSCHUSS
    try:
        return _kultur_daten_ohne()
    finally:
        dossier.fachausschuss = alt


def _kultur_daten_ohne():
    cache = dict(CACHE, h=vorlage("261064", "Rahmenterminplan Haushalt 2027/2028", amt="20 Stadtkämmerei"),
                 v=vorlage("240986", "Einbringung der Haushaltssatzung 2025/2026", date="2024-09-01"))
    meetings = MEETINGS + [dict(MEETINGS[0], date="2026-12-10", gremium="Rat", source_object="m9",
                                web="https://example.org/to/m9")]
    return dossier.daten(kultur.THEMA, cache, {"a": "ortsteil:endenich", "h": "ohne:2026"}, meetings, "2026-10-18",
                         {"stand": "2026-10-18"})


class KulturUnveraendert(unittest.TestCase):
    def setUp(self):
        self.d = _kultur_daten()

    def test_daten(self):
        self.assertEqual(json.loads(json.dumps(self.d)), json.loads((REFERENZ / "kultur.json").read_text()))

    def test_bild_zum_teilen(self):
        self.assertEqual(prozessbild.bild(kultur.THEMA, self.d, "https://example.org/thema/kunst-und-kultur/"),
                         (REFERENZ / "kultur-zeitleiste.svg").read_text())

    def test_seite(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            src = site / "data" / "export" / "bonn" / "dossiers" / "kultur.json"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(self.d))
            self.assertEqual(dossier.write(kultur.THEMA, site, "https://example.org/", gebietsseiten._page),
                             [kultur.THEMA.pfad])
            html = (site / kultur.THEMA.pfad / "index.html").read_text()
            alt = (site / "thema/kultur-und-haushalt/index.html").read_text()
        self.assertEqual(html, (REFERENZ / "kultur-seite.html").read_text())
        # frühere Adresse (bis 02.11.2026 „Kultur und Haushalt“) leitet weiter, nicht für Suchmaschinen
        self.assertIn('<meta http-equiv="refresh" content="0; url=https://example.org/thema/kunst-und-kultur/">', alt)
        self.assertIn('<meta name="robots" content="noindex">', alt)
        self.assertIn('<link rel="canonical" href="https://example.org/thema/kunst-und-kultur/">', alt)


class Beschreibungen(unittest.TestCase):
    def test_alle_themen_vollstaendig(self):
        keys = [t.key for t in ALLE]
        self.assertEqual(len(keys), len(set(keys)))
        for t in ALLE:
            strang = {k for k, _, _ in t.straenge}
            bahnen = [k for k, _ in t.bahnen]
            self.assertTrue(t.pfad.startswith("thema/") and t.pfad.endswith("/"), t.key)
            self.assertLessEqual(set(t.punkt_straenge), strang, t.key)
            self.assertLessEqual({r.strang for r in t.regeln} | {r.sonst for r in t.regeln if r.sonst}, strang, t.key)
            self.assertLessEqual(set(t.bahn_gremien), set(bahnen), t.key)
            self.assertLessEqual({b for b, *_ in t.phasen}, set(bahnen), t.key)
            self.assertTrue({"bv", "fach", "finanz", "rat"} <= set(bahnen), t.key)  # Bahnen ohne eigene Gremien
            if t.phasen:
                self.assertTrue(t.terminplan, t.key)


# ein kleines Thema ohne Phasen, Terminplan und Vergleich (Form einer neuen Themenseite)
SCHULE = dossier.Thema(
    key="schule", pfad="thema/schule/", titel="Schule", lead="Vorlagen zu Schulen seit {seit}.",
    seo_text="{n} Vorlagen zu Schulen.", seit="2025-11-01",
    straenge=[("bau", "Schulbau", "Titel nennt Neubau oder Sanierung"),
              ("weitere", "Weitere Vorlagen aus dem Schulamt", "Schulamt federführend oder Schulausschuss")],
    regeln=[dossier.Regel("bau", titel=re.compile(r"Neubau|Sanierung")),
            dossier.Regel("weitere", zustaendig=dossier.Zustaendig(aemter=("40 ",), gremien=("Schulausschuss",)))],
    punkt_straenge=("bau", "weitere"),
    bahnen=[("bv", "Bezirksvertretungen"), ("schule", "Schulausschuss"), ("fach", "andere Ausschüsse"),
            ("finanz", "Finanzausschuss"), ("rat", "Hauptausschuss, Rat")],
    bahn_gremien={"schule": ("Schulausschuss",)}, sitzungen=("Schulausschuss", "Rat"),
    achse=(date(2025, 11, 1), date(2027, 1, 1), date(2026, 7, 1), 0.5),
    bild_titel="Zeitleiste: Schule in Rat, Ausschüssen und Bezirksvertretungen", feed_text="zu Schulen",
    hinweis="Zuordnung abgeleitet", pruefung_text="Noch nicht von Hand geprüft.", nicht_gezeigt=["Beträge"])


class ThemaOhnePhasen(unittest.TestCase):
    def setUp(self):
        cache = {
            "a": vorlage("261900", "Neubau der Grundschule", amt="40 Schulamt", gremien=("Schulausschuss",),
                         result="beschlossen"),
            "b": vorlage("261901", "Schulentwicklungsplan", amt="01-2 Ratsbüro", gremien=("Schulausschuss",)),
            "c": vorlage("261902", "Ausstellung im Stadtmuseum", amt="41 Kulturamt"),
        }
        meetings = [{"date": "2026-12-01", "time": "17:00", "gremium": "Schulausschuss", "cancelled": False,
                     "web": None, "source_object": "m1"}]
        self.d = dossier.daten(SCHULE, cache, {}, meetings, "2026-10-26", {})

    def test_straenge_und_bahnen(self):
        by = {s["key"]: [(r["reference"], r["grund"]) for s2 in [s] for r in s2["vorlagen"]] for s in self.d["straenge"]}
        self.assertEqual(by["bau"], [("261900", "Titel: „Neubau“")])
        self.assertEqual(by["weitere"], [("261901", "Beratung im Schulausschuss")])
        self.assertEqual({p["bahn"] for p in self.d["punkte"]}, {"schule"})
        self.assertEqual([s["bahn"] for s in self.d["sitzungen"]], ["schule"])

    def test_seite_ohne_phasen(self):
        html = dossier.body(SCHULE, self.d, "../../")
        self.assertNotIn("Terminplan", html)
        self.assertNotIn("So entsteht", html)
        self.assertIn("(abgeleitet). Die Monate ab Juli 2026 sind breiter gezeichnet.", html)
        self.assertIn("Punkte und Sitzungen lassen sich anklicken", html)
        # Metaangaben eingeklappt (Entscheidung 10.11.2026): Regel je Strang, Quellen, Grenzen
        self.assertIn('<summary>Wie zugeordnet?</summary>\n      <p>Regel (abgeleitet): Titel nennt Neubau', html)
        self.assertIn("<summary>Quellen und Methode</summary>", html)
        self.assertNotIn('<p class="meta">Regel', html)
        self.assertIn('href="../../data/export/bonn/dossiers/schule.ics"', html)
        self.assertIn("Neue Vorlagen und Beratungsergebnisse zu Schulen im Feed-Reader.", html)
        svg = prozessbild.svg(SCHULE, self.d)
        self.assertIn("Zeitleiste von November 2025 bis Dezember 2026", svg)
        self.assertNotIn("geplant laut Terminplan", svg)
        self.assertIn("Zuordnung abgeleitet</text>", prozessbild.bild(SCHULE, self.d, "https://example.org/"))


if __name__ == "__main__":
    unittest.main()


class Verkehr(unittest.TestCase):
    """Regeln der Themenseite Verkehr und Mobilität (themenseiten/verkehr.py) und die Erweiterungen dafür:
    Regel nach Thema, Ausschluss, ganzes Verfahren nur über die Stammvorlage, Punkte nur aus bestimmten Gremien,
    Gliederung nach Stadtbezirk."""

    def setUp(self):
        from pipeline.themenseiten import verkehr

        def v(ref, name, gremien=("Ausschuss für Mobilität und Verkehr",), bezirk=None, thema=True, art="Antrag"):
            p = vorlage(ref, name, amt="61 Stadtplanungsamt", gremien=gremien)
            p["paper_type"] = art
            p["themes"] = [{"theme": "verkehr", "method": "amt", "evidence": "61-3 Stadtverkehr"}] if thema else []
            p["locations"] = [{"stadtbezirk": bezirk}] if bezirk else []
            return p
        self.t = verkehr.THEMA
        cache = {
            "a": v("261900", "Neuer Radweg an der Hauptstraße", bezirk="Beuel"),
            "b": v("261901", "Gehwegparken in der Lindenstraße", gremien=("Bezirksvertretung Beuel",), bezirk="Beuel"),
            "c": v("261902", "Fahrradparkhaus am Bahnhof"),
            "d": v("261903", "Pflegearbeiten im Verkehrsgrün"),
            "e": v("261904", "Fortschreibung des Nahverkehrsplans", art="Beschlussvorlage"),
            "f": v("261904-01 AA", "Ergänzungsantrag: Ersatzverkehr während der Sperrung der Nordbrücke"),
            "g": v("261905", "Sperrung der Nordbrücke: Maßnahmen", thema=False, art="Beschlussvorlage"),
            "h": v("261905-01 ST", "Stellungnahme der Verwaltung", thema=False, art="Stellungnahme der Verwaltung"),
            "i": v("261906", "Beleuchtung am Wasserland", gremien=("Bezirksvertretung Bonn",), bezirk="Bonn"),
        }
        self.d = dossier.daten(self.t, cache, {}, [], "2026-10-26", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["261900"], ("rad_fuss", "Thema „Verkehr und Mobilität“ (61-3 Stadtverkehr); "
                                             "Titel: „Radweg“"))
        self.assertEqual(self.by["261901"][0], "parken")  # Gehwegparken: Parken vor Rad und Fuß
        self.assertEqual(self.by["261902"][0], "bus_bahn")  # „Bahnhof“; Fahrradparkhaus zählt nicht als Parken
        self.assertNotIn("261903", self.by)  # Verkehrsgrün ausgeschlossen
        self.assertEqual(self.by["261904"][0], "bus_bahn")  # Änderungsantrag zieht das Verfahren nicht mit
        self.assertEqual(self.by["261904-01 AA"], ("nordbruecke", "Titel: „Nordbrücke“"))
        self.assertEqual(self.by["261905-01 ST"], ("nordbruecke", "Verfahren 261905; Titel: „Nordbrücke“"))
        self.assertEqual(self.by["261906"][0], "weitere")

    def test_punkte_nur_aus_rat_und_mobilitaetsausschuss(self):
        refs = {p["reference"] for p in self.d["punkte"]}
        self.assertIn("261900", refs)
        self.assertNotIn("261901", refs)  # nur in der Bezirksvertretung beraten
        self.assertEqual({p["bahn"] for p in self.d["punkte"] if p["reference"] == "261900"}, {"mobil"})

    def test_weitere_nach_stadtbezirk(self):
        weitere = next(s for s in self.d["straenge"] if s["key"] == "weitere")
        self.assertEqual([r["bezirk"] for r in weitere["vorlagen"]], ["Bonn"])
        self.assertNotIn("bezirk", next(s for s in self.d["straenge"] if s["key"] == "rad_fuss")["vorlagen"][0])
        html = dossier.body(self.t, self.d, "../../")
        self.assertIn("<summary>Bonn (1)</summary>", html)
        self.assertIn("Terminplan 261064", html)  # Haushaltsbahn wie bei Kultur

    def test_regeln_nach_pruefung(self):
        """Prüfung im Gespräch 26.10.2026 (verkehr/PRUEFUNG.md): Änderungen A bis E."""
        from pipeline.themenseiten import verkehr
        t = verkehr.THEMA

        def zu(name, thema=True):
            p = vorlage("262000", name)
            p["themes"] = [{"theme": "verkehr", "evidence": "61-3 Stadtverkehr"}] if thema else []
            return (dossier.zuordnen(t, p) or (None,))[0]
        self.assertEqual(zu("Übernahme der Parkplätze am Bahnhof"), "parken")  # A
        self.assertEqual(zu("Fahrrad- und Lastenradstellplätze an der Kita"), "rad_fuss")  # B
        self.assertEqual(zu("Stellplätze für Pkw"), "parken")
        self.assertEqual(zu("Prüfung der Park- und Verkehrssituation"), "parken")  # C
        self.assertIsNone(zu("Leerung der Altglascontainer an der Bushaltestelle"))  # D
        self.assertIsNone(zu("Abwasserbeseitigungskonzept 2024-2029"))
        self.assertEqual(zu("Überholverbot für einspurige Fahrzeuge", thema=False), "rad_fuss")  # E
        self.assertEqual(zu("Lärmschutzmaßnahmen Autobahn", thema=False), "weitere")
        self.assertIsNone(zu("Kita-Neubau in der Riemannstraße", thema=False))

    def test_tempo_und_strassenverkehrsbehoerde(self):
        """Ergänzung 02.11.2026 (verkehr/ERGAENZUNG.md): Strang „Tempo, Verkehrsregeln und Sicherheit“, Vorlagen
        der Straßenverkehrsbehörde (33-1) nur mit Verkehrswort, Regel A der Prüfung."""
        from pipeline.themenseiten import verkehr
        t = verkehr.THEMA
        self.assertIn("tempo", [k for k, *_ in t.straenge])

        def zu(name, thema=False, abt=None):
            p = vorlage("262000", name)
            p["themes"] = [{"theme": "verkehr", "evidence": "61-3 Stadtverkehr"}] if thema else []
            if abt:
                p["responsibility"] = [{"kind": "federfuehrend", "label": "33 Bürgerdienste", "name": abt}]
            return (dossier.zuordnen(t, p) or (None,))[0]
        stvb = "33-1 Ordnungs- und Straßenverkehrsbehörde"
        self.assertEqual(zu("Einrichtung einer Tempo-30-Zone in der Wurzerstraße"), "tempo")
        self.assertEqual(zu("Verkehrsberuhigende Maßnahmen", thema=True), "tempo")  # vorher „weitere“
        self.assertEqual(zu("Geschwindigkeitsüberwachung auf der B56"), "tempo")
        self.assertIsNone(zu("Bonn klimafit machen: Tempo erhöhen beim Hitzeschutz"))
        self.assertIsNone(zu("Projekt Verkehrssicherheit städtischer Bäume"))
        self.assertEqual(zu("Zusätzlicher Taxistand", abt=stvb), "tempo")
        self.assertIsNone(zu("Zusätzlicher Taxistand"))  # ohne Straßenverkehrsbehörde
        self.assertIsNone(zu("Rattenbekämpfung in Bad Godesberg", abt=stvb))  # Ordnungsthema ohne Verkehrswort
        self.assertEqual(zu("Optimierung der Parksituation", abt=stvb), "parken")
        self.assertEqual(zu("Abmarkierung von Kfz-Stellflächen", abt=stvb), "parken")  # Regel A
        self.assertEqual(zu("Einrichtung einer Brötchentaste", abt=stvb), "parken")  # Regel A
        self.assertIsNone(zu("Aufstellflächen für Fahrräder"))

    def test_veroeffentlicht_mit_uebersicht(self):
        self.assertIn(self.t.key, [t.key for t in ALLE])
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            src = site / "data" / "export" / "bonn" / "dossiers" / "verkehr.json"
            src.parent.mkdir(parents=True)
            src.write_text(json.dumps(self.d))
            self.assertEqual(dossier.uebersicht(ALLE, site, "https://example.org/", gebietsseiten._page), [])
            dossier.write(self.t, site, "https://example.org/", gebietsseiten._page)
            self.assertEqual(dossier.uebersicht(ALLE, site, "https://example.org/", gebietsseiten._page), ["thema/"])
            html = (site / "thema" / "index.html").read_text()
        self.assertIn('<h2><a href="../thema/verkehr-und-mobilitaet/">Verkehr und Mobilität</a></h2>', html)
        self.assertIn('<p class="kachel-zahl"><strong>8</strong> Vorlagen in 6 Strängen</p>', html)  # mit Strang Tempo (02.11.2026)
        self.assertIn('class="kachel-symbol"', html)
        self.assertNotIn("kunst-und-kultur", html)  # ohne Daten keine Zeile


class Schule(unittest.TestCase):
    """Regelentwurf der Themenseite Schule und Bildung (themenseiten/schule.py, Entwurf): Bedingung im Titel
    (Schulwort und Merkmal des Strangs), Schulamt und Schulausschuss, Ausschluss von Kitas und Sammellisten."""

    def setUp(self):
        from pipeline.themenseiten import schule

        def v(ref, name, amt="85 Städtisches Gebäudemanagement", gremien=("Bezirksvertretung Bonn",)):
            p = vorlage(ref, name, amt=amt, gremien=gremien)
            p["themes"], p["locations"] = [], []
            return p
        self.t = schule.THEMA
        cache = {
            "a": v("261900", "Querungshilfe vor der Grundschule Endenich"),
            "b": v("261901", "Sanierung der Toiletten am Beethoven-Gymnasium"),
            "c": v("261902", "Erhöhung der Zügigkeit der Gesamtschule Beuel"),
            "d": v("261903", "Schulbuchbeschaffung", amt="40 Schulamt"),
            "e": v("261904", "Anfrage: ABC-Klassen", amt="01 Ratsbüro", gremien=("Schulausschuss",)),
            "f": v("261905", "Sanierung des Rathauses"),
            "g": v("261906", "Neubau der Kita an der Schulstraße"),
            "h": v("261907", "Tagesordnungspunkte in nichtöffentlicher Sitzung", amt="40 Schulamt"),
            "i": v("261908", "Neubau der Musikschule"),
            "j": v("261909", "Abbau von Altschulden"),
            "k": v("261910", "Schulstraße in Lengsdorf - Gehwegergänzung"),
            "l": v("261911", "Kleine Anfrage zu Schulstraßen"),
            "m": v("261912", "Betreuungsangebot für Vorschulkinder"),
            "n": v("261913", "Errichtung einer Schranke am Berufskolleg"),
            "o": v("261914", "Errichtung einer dritten Gesamtschule in Beuel"),
        }
        self.d = dossier.daten(self.t, cache, {}, [], "2026-10-26", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["261900"], ("schulweg", "Titel: „Querungshilfe“ und „Grundschule“"))
        self.assertEqual(self.by["261901"][0], "bau")
        self.assertEqual(self.by["261902"][0], "plaetze")
        self.assertEqual(self.by["261903"], ("weitere", "federführend: 40 Schulamt"))
        self.assertEqual(self.by["261904"], ("weitere", "Beratung im Schulausschuss"))

    def test_ohne_schulwort_und_ausschluss(self):
        for ref in ("261905", "261906", "261907", "261908", "261909"):
            self.assertNotIn(ref, self.by, ref)

    def test_regeln_nach_pruefung(self):
        # A: „Schulstraße“ in der Einzahl ist ein Straßenname, „Schulstraßen“ zählen
        self.assertNotIn("261910", self.by)
        self.assertEqual(self.by["261911"], ("schulweg", "Titel: „Schulstraßen“"))
        # B: Errichtung nur einer Schule; C: „Vorschul…“ ist kein Schulwort
        self.assertEqual(self.by["261913"], ("weitere", "Titel: „Berufskolleg“"))
        self.assertEqual(self.by["261914"][0], "plaetze")
        self.assertNotIn("261912", self.by)

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertNotIn(self.t, ENTWUERFE)


class Wohnen(unittest.TestCase):
    """Regelentwurf der Themenseite Wohnen und Bauen (themenseiten/wohnen.py, Entwurf): Reihenfolge der Titelregeln,
    Zuständigkeit ohne Verkehr (ohne_thema), Ausschluss von Bühnen und „Miet…“ ohne Wohnbezug."""

    def setUp(self):
        from pipeline.themenseiten import wohnen

        def v(ref, name, amt="01-2 Ratsbüro", gremien=("Bezirksvertretung Bonn",), themen=()):
            p = vorlage(ref, name, amt=amt, gremien=gremien)
            p["themes"] = [{"theme": t, "method": "stichwort", "evidence": t} for t in themen]
            p["locations"] = []
            return p
        self.t = wohnen.THEMA
        cache = {
            "a": v("261900", "Verfahrensbeschleunigung in der Bauleitplanung"),
            "b": v("261901", "Bebauungsplan Nr. 1234-5 „Am Bach“ mit gefördertem Wohnraum"),
            "c": v("261902", "Antrag: Housing First"),
            "d": v("261903", "Eintragung in die Denkmalliste"),
            "e": v("261904", "Tempo 30 vor einem denkmalgeschützten Haus", themen=("verkehr",)),
            "f": v("261905", "Nutzungsänderung eines Ladens", amt="63 Bauordnungsamt"),
            "g": v("261906", "Neue Ampel an der Kreuzung", amt="61 Stadtplanungsamt", themen=("verkehr",)),
            "h": v("261907", "Fahrradmietsystem: neue Stationen"),
            "i": v("261908", "Zukunft Bonner Bühnen: Denkmalschutz"),
            "j": v("261909", "Sachstand", gremien=("Ausschuss für Planen, Bauen und Denkmalschutz",)),
            "k": v("261910", "Aufhebung des Fluchtlinienplans B 1"),
            "l": v("261911", "Straßenbenennung in Dransdorf", amt="63 Bauordnungsamt"),
            "m": v("261912", "Fortführung des Quartiersmanagements in Auerberg", amt="50 Amt für Soziales und Wohnen"),
        }
        self.d = dossier.daten(self.t, cache, {}, [], "2026-10-26", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["261900"][0], "turbo")  # vor Bebauungsplänen
        self.assertEqual(self.by["261901"][0], "bebauungsplan")  # vor Wohnraum
        self.assertEqual(self.by["261902"], ("wohnraum", "Titel: „Housing First“"))
        self.assertEqual(self.by["261903"][0], "denkmal")
        self.assertEqual(self.by["261905"], ("weitere", "federführend: 63 Bauordnungsamt"))
        self.assertEqual(self.by["261909"][0], "weitere")

    def test_ohne_verkehr_und_ausschluss(self):
        for ref in ("261904", "261906", "261907", "261908"):
            self.assertNotIn(ref, self.by, ref)

    def test_regeln_nach_pruefung(self):
        self.assertEqual(self.by["261910"][0], "bebauungsplan")  # A: Fluchtlinienplan
        self.assertNotIn("261911", self.by)  # B: Straßenbenennung
        self.assertEqual(self.by["261912"], ("weitere", "Titel: „Quartiersmanagements“"))  # C: Stadtentwicklung

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertNotIn(self.t, ENTWUERFE)


class Klima(unittest.TestCase):
    """Regelentwurf der Themenseite Klima und Umwelt (themenseiten/klima.py, Entwurf): Titelregeln ohne Verkehr,
    Umweltamt und Umweltausschuss, Sondervermögen kein Klimaschutz."""

    def setUp(self):
        from pipeline.themenseiten import klima

        def v(ref, name, amt="01-2 Ratsbüro", gremien=("Bezirksvertretung Bonn",), themen=()):
            p = vorlage(ref, name, amt=amt, gremien=gremien)
            p["themes"] = [{"theme": t, "method": "stichwort", "evidence": t} for t in themen]
            p["locations"] = []
            return p
        self.t = klima.THEMA
        cache = {
            "a": v("261900", "Fortschreibung Klimaplan"),
            "b": v("261901", "Hitzeschutz in Seniorenheimen"),
            "c": v("261902", "Neufassung der Baumschutzsatzung"),
            "d": v("261903", "Mehrweg statt Einweg: Verpackungssteuer"),
            "e": v("261904", "Gebührenkalkulation des Friedhofswesens", amt="67 Amt für Umwelt und Stadtgrün"),
            "f": v("261905", "Regionales Fahrradmietsystem nach Maßgabe des Klimasteckbriefes", themen=("verkehr",)),
            "g": v("261906", "Sondervermögen „Infrastruktur und Klimaneutralität“"),
            "h": v("261907", "Baumaßnahme an der Schule"),
            "i": v("261908", "Rasenmähroboter", gremien=("Ausschuss für Umwelt, Klima und Lokale Agenda",)),
            "j": v("261909", "Toilettensituation am Eingang der Rheinaue"),
            "k": v("261910", "Bonner Leitlinien zum „Bau-Turbo“", gremien=("Ausschuss für Umwelt, Klima und Lokale Agenda",)),
            "l": v("261911", "Heimische Fauna vor Neozoen schützen", amt="67 Amt für Umwelt und Stadtgrün"),
            "m": v("261912", "Lärmbelastung durch den Schienengüterverkehr"),
            "n": v("261913", "Klimagerechtes Hof- und Fassadenprogramm"),
        }
        self.d = dossier.daten(self.t, cache, {}, [], "2026-10-26", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["261900"][0], "klimaschutz")
        self.assertEqual(self.by["261901"][0], "anpassung")
        self.assertEqual(self.by["261902"][0], "gruen")
        self.assertEqual(self.by["261903"][0], "abfall")
        self.assertEqual(self.by["261904"], ("weitere", "federführend: 67 Amt für Umwelt und Stadtgrün"))
        self.assertEqual(self.by["261908"], ("weitere", "Beratung im Ausschuss für Umwelt, Klima und Lokale Agenda"))

    def test_ohne_verkehr_und_fehltreffer(self):
        for ref in ("261905", "261906", "261907"):
            self.assertNotIn(ref, self.by, ref)

    def test_regeln_nach_pruefung(self):
        self.assertEqual(self.by["261909"][0], "weitere")  # A: Toiletten in Parks
        self.assertNotIn("261910", self.by)  # B: Bau-Turbo auf der Seite Wohnen und Bauen
        self.assertEqual(self.by["261911"][0], "gruen")  # C: Artenschutz
        self.assertEqual(self.by["261912"], ("weitere", "Titel: „Lärmbelastung“"))  # D: Lärm
        self.assertEqual(self.by["261913"][0], "klimaschutz")  # E: klimagerecht

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertNotIn(self.t, ENTWUERFE)


class Kinder(unittest.TestCase):
    """Themenseite Kinder, Jugend und Familie (themenseiten/kinder.py): Titelregeln, Kitas als Ortsangabe beim Verkehr,
    Beirat nur mit Kindern oder Jugend im Titel, Ganztag auf der Schulseite; Regeln A und B nach der Prüfung."""

    def setUp(self):
        from pipeline.themenseiten import kinder

        def v(ref, name, amt="01-2 Ratsbüro", gremien=("Bezirksvertretung Bonn",), themen=()):
            p = vorlage(ref, name, amt=amt, gremien=gremien)
            p["themes"] = [{"theme": t, "method": "stichwort", "evidence": t} for t in themen]
            p["locations"] = []
            return p
        self.t = kinder.THEMA
        cache = {
            "a": v("261900", "Kita-Neubau an der Riemannstraße"),
            "b": v("261901", "Halteverbot vor der Kita am Markt", themen=("verkehr",)),
            "c": v("261902", "Umbau des Kinderspielplatzes Königsberger Weg"),
            "d": v("261903", "Fortschreibung des Kinder- und Jugendförderplans: Jugendarbeit"),
            "e": v("261904", "Arbeit der Frühen Hilfen Bonn"),
            "f": v("261905", "Kinder- und Jugendrechtewoche und Weltkindertag"),
            "g": v("261906", "Sachstand Personal", amt="51 Amt für Kinder, Jugend und Familie"),
            "h": v("261907", "Bericht aus dem Beirat", gremien=("Beirat Kinder- und Jugendbeteiligung",)),
            "i": v("261908", "Wünsche von Kindern an die Stadt", gremien=("Beirat Kinder- und Jugendbeteiligung",)),
            "j": v("261909", "Ausbau des Offenen Ganztags", amt="51 Amt für Kinder, Jugend und Familie"),
            "k": v("261910", "Neubau eines Einfamilienhauses"),
            "l": v("261911", "Tagesordnungspunkte in nichtöffentlicher Sitzung",
                   gremien=("Ausschuss für Kinder, Jugend und Familie",)),
            # vor dem Ziehen des Prüfbogens korrigiert (02.11.2026)
            "m": v("261912", "Antrag: Parksituation Zuwegung Kita In der Raste"),
            "n": v("261913", "Marktverzeichnis 2026 - Hier: Jubiläums-, Freundes- und Familienfest"),
            "o": v("261914", "Elternbefragung zum Bedarf an Gesamtschulplätzen"),
            "p": v("261915", "Deutsche Meisterschaft im Vert Skateboarding 2026"),
            "q": v("261916", "Organisationsuntersuchung im Amt für Kinder, Jugend und Familie",
                   amt="51 Amt für Kinder, Jugend und Familie"),
            "r": v("261917", "Zuschuss an den Verband binationaler Familien"),
            # nach der Prüfung (02.11.2026): A Bauen nicht allein über die Beratung im Ausschuss, B junge Menschen
            "s": v("261918", "Evaluation Baulandmodell", amt="61 Stadtplanungsamt",
                   gremien=("Ausschuss für Kinder, Jugend und Familie",), themen=("bauen",)),
            "t": v("261919", "Überplanmäßige Ausgaben im Dezernat 5", gremien=("Ausschuss für Kinder, Jugend und Familie",)),
            "u": v("261920", "Evaluation des freien Eintritts für Kinder und Jugendliche während der Sommerferien"),
            "w": v("261921", "Sichere Mobilität von Kindern und Jugendlichen - Tempo 30", themen=("verkehr",)),
            "x": v("261922", "Vertretung von Kindern und Jugendlichen im Klimabeirat",
                   gremien=("Beirat Kinder- und Jugendbeteiligung",)),
        }
        self.d = dossier.daten(self.t, cache, {}, [], "2026-11-02", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["261900"], ("kita", "Titel: „Kita-Neubau“"))
        self.assertEqual(self.by["261902"][0], "spiel")
        self.assertEqual(self.by["261903"][0], "jugend")
        self.assertEqual(self.by["261904"][0], "familie")
        self.assertEqual(self.by["261905"][0], "beteiligung")
        self.assertEqual(self.by["261906"], ("weitere", "federführend: 51 Amt für Kinder, Jugend und Familie"))
        self.assertEqual(self.by["261908"], ("beteiligung", "Beratung im Beirat Kinder- und Jugendbeteiligung; Titel: „Kindern“"))

    def test_abgrenzung(self):
        # Kita als Ortsangabe beim Verkehr, Beirat ohne Kinder/Jugend im Titel, Ganztag (Schulseite), Haustyp, Formalien
        for ref in ("261901", "261907", "261909", "261910", "261911", "261912", "261913", "261914", "261915"):
            self.assertNotIn(ref, self.by, ref)
        self.assertEqual(self.by["261916"], ("weitere", "federführend: 51 Amt für Kinder, Jugend und Familie"))
        self.assertEqual(self.by["261917"][0], "familie")

    def test_regeln_nach_pruefung(self):
        self.assertNotIn("261918", self.by)  # A
        self.assertEqual(self.by["261919"], ("weitere", "Beratung im Ausschuss für Kinder, Jugend und Familie"))
        self.assertEqual(self.by["261920"], ("weitere", "Titel: „für Kinder und Jugendliche“"))  # B
        self.assertNotIn("261921", self.by)  # B ohne Verkehr
        self.assertEqual(self.by["261922"][0], "beteiligung")  # Beirat vor Regel B

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertNotIn(self.t, ENTWUERFE)
        self.assertEqual([k for k, *_ in self.t.straenge], ["kita", "spiel", "jugend", "familie", "beteiligung", "weitere"])


class Soziales(unittest.TestCase):
    """Entwurf der Themenseite Soziales, Gesundheit und Integration (themenseiten/soziales.py): Abgrenzung zu Wohnen
    (Regel-Feld ohne_seite, Wohnungslosigkeit und Unterkünfte auf beiden Seiten), Fehltreffer vor dem Ziehen des
    Prüfbogens, Zuschüsse unter „weitere“."""

    def setUp(self):
        from pipeline.themenseiten import soziales, wohnen

        def v(ref, name, amt="01-2 Ratsbüro", gremien=("Rat",), themen=()):
            p = vorlage(ref, name, amt=amt, gremien=gremien)
            p["themes"] = [{"theme": t, "method": "stichwort", "evidence": t} for t in themen]
            p["locations"] = []
            return p
        self.t, self.wohnen = soziales.THEMA, wohnen.THEMA
        a50, a05 = "50 Amt für Soziales und Wohnen", "05 Amt für Integration und Vielfalt"
        self.cache = {
            # Wohnen bleibt auf der Seite Wohnen und Bauen
            "a": v("261900", "Fortschreibung des Bonner Mietspiegels 2026", amt=a50),
            "b": v("261901", "Wohnen in Bonn hier: Handlungskonzept Wohnen Bonn", amt=a50),
            "c": v("261902", "Programm zur Förderung von gemeinwohlorientierten Wohnprojekten", amt=a50),
            "d": v("261903", "Bebauungsplan Nr. 1234-5 Pflegeheim am Beispielweg", amt="61 Stadtplanungsamt"),
            # Wohnungslosigkeit und Unterkünfte auf beiden Seiten
            "e": v("261904", "Grüne-Antrag: Housing First", amt=a50),
            "f": v("261905", "Wohnungen für Wohnungslose", amt=a50),
            "g": v("261906", "Satzung über Unterkünfte für obdachlose und geflüchtete Menschen", amt=a50),
            "h": v("261907", "Wohnprojekt für Wohnungslose", amt=a50),
            # übrige Vorlagen der Ämter und Ausschüsse
            "i": v("261908", "Sachstand Personal", amt=a50),
            "j": v("261909", "Bericht über das Bürgerschaftliche Engagement",
                   gremien=("Ausschuss für Chancengerechtigkeit und Integration",)),
            # Fehltreffer vor dem Ziehen des Prüfbogens (02.11.2026)
            "k": v("261910", "Aufstellung eines Gedenksteins/-tafel"),
            "l": v("261911", "Pflege und Erneuerung der städtischen Grünflächen"),
            "m": v("261912", "Arbeitspaket „Migrationsunterstützung UDP“"),
            "n": v("261913", "Pilotprojekt: Integration von Bordsteinladesäulen in das Stadtgebiet"),
            "o": v("261914", "Barrierefreier Umbau der Haltestelle Markt"),
            "p": v("261915", "Barrierefreiheit im Stadthaus", amt=a50),
            "q": v("261916", "Wahl des/der Vorsitzenden des Ausschusses für Chancengerechtigkeit und Integration",
                   amt=a05),
            "r": v("261917", "Bestellung von Mitgliedern des Rates für den Ausschuss für Chancengerechtigkeit und "
                             "Integration", amt=a05),
            "s": v("261918", "Künftige Unterbringung des Stadtmuseums"),
            "t": v("261919", "Dialogforum Biodiversität"),
            "u": v("261920", "Zuschuss an den Verein Beispiel e.V.", amt=a05),
            "w": v("261921", "Bezuschussung MobilPass-Tickets aus Bonn-Ausweis-Mitteln", amt=a50),
            "x": v("261922", "Grüne Anfrage: Zukunft Bonner Tafel"),
            "y": v("261923", "Seniorenzentren Wirtschaftsplan 2026", amt="Seniorenzentren der Bundesstadt Bonn"),
            "z": v("261924", "Maßnahmen zur Bewältigung des Drogenkonsums"),
            "aa": v("261925", "Sicherheit auf dem Radweg vor dem Ärztehaus", themen=("verkehr",)),
        }
        self.d = dossier.daten(self.t, self.cache, {}, [], "2026-11-02", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_wohnen_bleibt_auf_der_wohnseite(self):
        for ref in ("261900", "261901", "261902", "261903"):
            self.assertNotIn(ref, self.by, ref)
        self.assertEqual(dossier.zuordnen(self.wohnen, self.cache["a"])[0], "wohnraum")

    def test_wohnungslosigkeit_auf_beiden_seiten(self):
        self.assertEqual(self.by["261904"], ("armut", "Titel: „Housing First“"))
        self.assertEqual(self.by["261905"][0], "armut")
        self.assertEqual(self.by["261906"][0], "gefluechtete")
        self.assertEqual(self.by["261907"][0], "armut")
        for k in ("e", "f"):
            self.assertEqual(dossier.zuordnen(self.wohnen, self.cache[k])[0], "wohnraum")

    def test_weitere_und_zuschuesse(self):
        self.assertEqual(self.by["261908"], ("weitere", "federführend: 50 Amt für Soziales und Wohnen"))
        self.assertEqual(self.by["261909"], ("weitere", "Beratung im Ausschuss für Chancengerechtigkeit und Integration"))
        self.assertEqual(self.by["261920"], ("weitere", "federführend: 05 Amt für Integration und Vielfalt; "
                                                        "Titel: „Zuschuss an“"))
        self.assertEqual(self.by["261921"][0], "armut")  # Bezuschussung von Tickets ist kein Zuschuss an Träger
        self.assertEqual(self.by["261922"][0], "armut")
        self.assertEqual(self.by["261923"][0], "senioren")
        self.assertEqual(self.by["261924"][0], "gesundheit")
        self.assertEqual(self.by["261915"], ("senioren", "federführend: 50 Amt für Soziales und Wohnen; "
                                                         "Titel: „Barrierefreiheit“"))

    def test_fehltreffer(self):
        for ref in ("261910", "261911", "261912", "261913", "261914", "261916", "261917", "261918", "261919",
                    "261925"):
            self.assertNotIn(ref, self.by, ref)

    def test_regeln_nach_pruefung(self):
        from pipeline import dossier
        # A: Friedhöfe und Bestattungswesen nicht, auch bei Mitberatung im ACI; muslimische Bestattungsflächen bleiben
        p = vorlage("261990", "Gebührenkalkulation des Friedhofs- und Bestattungswesens für das Jahr 2026",
                    amt="13 Amt für Umwelt", gremien=("Ausschuss für Chancengerechtigkeit und Integration",))
        self.assertIsNone(dossier.zuordnen(self.t, p))
        p = vorlage("261991", "Sicherung einer muslimischen Bestattungsfläche am Nordfriedhof")
        self.assertEqual(dossier.zuordnen(self.t, p)[0], "integration")
        # B: soziales Miteinander
        p = vorlage("261992", "Grüne/Linke-Antrag: Soziales Miteinander in der GGS Medinghoven")
        self.assertEqual(dossier.zuordnen(self.t, p)[0], "integration")

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertNotIn(self.t, ENTWUERFE)
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertEqual(self.t.fachausschuss, ("Ausschuss für Soziales, Migration, Gesundheit, Wohnen und Senioren",
                                                "Ausschuss für Chancengerechtigkeit und Integration"))
        strang = {k for k, _, _ in self.t.straenge}
        self.assertLessEqual({r.strang for r in self.t.regeln}, strang)
        self.assertLessEqual(set(self.t.punkt_straenge), strang)
        self.assertLessEqual(set(self.t.bahn_gremien), {k for k, _ in self.t.bahnen})
        self.assertEqual(sum(self.t.stichprobe_je_strang.values()), 25)


class OhneSeite(unittest.TestCase):
    """Regel-Feld ohne_seite: Vorlagen, die auf einer anderen Themenseite stehen, überspringen die Regel."""

    def test_ohne_seite(self):
        andere = dossier.Thema(**{**SCHULE.__dict__, "key": "andere", "regeln": SCHULE.regeln[:1]})  # nur Neubau
        thema = dossier.Thema(**{**SCHULE.__dict__, "regeln": [
            dossier.Regel("bau", titel=re.compile(r"Wohnungslos")),
            dossier.Regel("weitere", zustaendig=dossier.Zustaendig(aemter=("40 ",)), ohne_seite=andere)]})
        neubau = vorlage("261900", "Neubau der Grundschule", amt="40 Schulamt")
        personal = vorlage("261901", "Sachstand Personal", amt="40 Schulamt")
        beides = vorlage("261902", "Neubau einer Unterkunft für Wohnungslose", amt="40 Schulamt")
        self.assertEqual(dossier.zuordnen(andere, neubau)[0], "bau")
        self.assertIsNone(dossier.zuordnen(thema, neubau))           # steht auf der anderen Seite
        self.assertEqual(dossier.zuordnen(thema, personal)[0], "weitere")
        self.assertEqual(dossier.zuordnen(thema, beides)[0], "bau")   # Regel ohne ohne_seite gilt vorher


class MehrereFachausschuesse(unittest.TestCase):
    """Kasten „Wer berät mit“ mit zwei Ausschüssen (Thema.fachausschuss als Tupel); ein Name bleibt wie bisher."""

    def setUp(self):
        self.besetzung = {
            "Sozialausschuss": dict(AUSSCHUSS, name="Sozialausschuss", id="374", ohne_fraktion=8, sachkundig=8),
            "ACI": dict(AUSSCHUSS, name="ACI", id="368", mitglieder=28, ohne_fraktion=18, sachkundig=0,
                        vorsitz=[{"name": "Anna Beispiel", "rolle": "Vorsitz IntegrationsA", "fraktion": None}],
                        ohne_fraktion_rollen=[{"rolle": "Mitglied ACI", "n": 15}, {"rolle": "Vorsitz", "n": 3}]),
        }
        self.alt = dossier._besetzung
        dossier._besetzung = lambda name, seit, orgs, path: self.besetzung.get(name)

    def tearDown(self):
        dossier._besetzung = self.alt

    def test_str_und_tupel(self):
        ein = dossier.Thema(**{**SCHULE.__dict__, "fachausschuss": "Sozialausschuss"})
        zwei = dossier.Thema(**{**SCHULE.__dict__, "fachausschuss": ("Sozialausschuss", "ACI", "fehlt")})
        self.assertEqual(dossier.fachausschuss(ein, orgs={"x": {}})["id"], "374")
        self.assertEqual([a["id"] for a in dossier.fachausschuss(zwei, orgs={"x": {}})], ["374", "368"])
        d = dossier.daten(zwei, {}, {}, [], "2026-11-02", {})
        self.assertNotIn("fachausschuss", d)
        html = dossier.body(zwei, d, "../../")
        self.assertIn('<h2 id="fachausschuss">Wer berät mit</h2>\n    <p>Zu diesem Thema beraten zwei Fachausschüsse:</p>',
                      html)
        self.assertIn('<h3 id="fachausschuss-374">Sozialausschuss</h3>', html)
        self.assertIn('<h3 id="fachausschuss-368">ACI</h3>', html)
        self.assertIn("<li>ohne Angabe einer Fraktion: 18 (darunter 15 mit der Rolle „Mitglied ACI“, 3 im Vorsitz "
                      "oder in der Stellvertretung)</li>", html)
        self.assertIn("<li>ohne Angabe einer Fraktion: 8 (darunter 8 sachkundige Bürger:innen und Einwohner:innen)</li>",
                      html)
        self.assertIn("Vorsitz IntegrationsA: Anna Beispiel.", html)
        self.assertIn('<a href="#fachausschuss">Wer berät mit</a>', html)
        self.assertEqual(html.count('?prozesse=gremien&amp;gremium='), 2)


class Sicherheit(unittest.TestCase):
    """Entwurf der Themenseite Sicherheit und Ordnung (themenseiten/sicherheit.py): Abteilungsregel für das Amt 33
    (Zustaendig.abteilungen: 33-2, 33-5 und das Amt allgemein, nicht 33-1, 33-4, 33-6, 33-0), Amt 37 im Strang
    Feuerwehr, „Feuerwehrtopf“ ausgeschlossen, Verkehrs-, Versorgungs- und Cybersicherheit nicht, Fehltreffer vor dem
    Ziehen des Prüfbogens."""

    def setUp(self):
        from pipeline.themenseiten import sicherheit

        def v(ref, name, amt="01-2 Ratsbüro", abteilung=None, gremien=("Rat",), themen=()):
            p = vorlage(ref, name, amt=amt, gremien=gremien)
            p["themes"] = [{"theme": t, "method": "stichwort", "evidence": t} for t in themen]
            p["locations"] = []
            p["responsibility"] = [{"kind": "federfuehrend", "label": amt, "name": abteilung or amt}]
            return p
        self.t = sicherheit.THEMA
        a33, a37 = "33 Bürgerdienste", "37 Feuerwehr und Rettungsdienst"
        self.cache = {
            # Abteilungen des Amts 33 (Titel ohne Merkmal eines Strangs)
            "a": v("261900", "Sachstand Personal", amt=a33, abteilung="33-2 Ordnungswidrigkeiten, Stadtordnungsdienst"),
            "b": v("261901", "Rahmenbedingungen für Veranstaltungen im Stadtgarten", amt=a33,
                   abteilung="33-5 Veranstaltungskoordination und Märkte"),
            "c": v("261902", "Vertagungsbitte zum Bürgerantrag: Baden im Rhein", amt=a33, abteilung=a33),
            "d": v("261903", "Anordnung „Einfahrt verboten – Anlieger frei“", amt=a33,
                   abteilung="33-1 Ordnungs- und Straßenverkehrsbehörde"),
            "e": v("261904", "Controllingbericht 2025", amt=a33, abteilung="33-4 Dienstleistungszentrum"),
            "f": v("261905", "Stellungnahme zum Elternnachzug", amt=a33,
                   abteilung="33-6 Ausländeramt Allgemeines Aufenthaltsrecht, Verpflichtungserklärungen, "
                             "Internationale Angelegenheiten, Visa, Patientenaufenthalte"),
            "g": v("261906", "Bildung eines Wahlausschusses für die Kommunalwahlen", amt=a33, abteilung=a33),
            # Amt 37 und Titelregeln
            "h": v("261907", "Sachstand Abrechnung", amt=a37, abteilung="37-0 Verwaltung und Rettungsdienst"),
            "i": v("261908", "Neufassung der Gebührensatzung für den Rettungsdienst", amt=a37),
            "j": v("261909", "Antrag: Grundzüge des Bonner Bevölkerungsschutzes"),
            "k": v("261910", "Große Anfrage zur Sicherheitslage im Stadtteil Tannenbusch"),
            "l": v("261911", "Marktverzeichnis für den Stadtbezirk Beuel 2026", amt=a33,
                   abteilung="33-5 Veranstaltungskoordination und Märkte"),
            "m": v("261912", "Sachstand", gremien=("Ausschuss für Sicherheit, Ordnung und Bevölkerungsschutz",)),
            # Feuerwehrtopf (Mittel der Bezirksvertretungen für Vereine)
            "n": v("261913", "Bereitstellung von Mitteln aus dem Feuerwehrtopf für das Straßenfest"),
            "o": v("261914", "Sicherheit für den Bad Godesberger Nikolausmarkt; Bereitstellung von Mitteln aus dem "
                             "Feuerwehrtopf"),
            # Verkehrs-, Versorgungs-, Informations- und Cybersicherheit
            "p": v("261915", "Verkehrssicherheit an der Kreuzung Beispielstraße", amt=a33,
                   abteilung="33-1 Ordnungs- und Straßenverkehrsbehörde"),
            "q": v("261916", "Sicherheit für den Radverkehr auf der Beispielstraße", themen=("verkehr",)),
            "r": v("261917", "Verbesserung der Sicherheit für Radfahrer am ehemaligen Bahnübergang"),
            "s": v("261918", "Antrag: Sicherheit der Stromversorgungsinfrastruktur"),
            "t": v("261919", "Region Bonn als Zentrum für Cyber- und Informationssicherheit"),
            "u": v("261920", "Einleitung des Vergabeverfahrens zur mobilen Geschwindigkeitsüberwachung", amt=a33,
                   abteilung="33-2 Ordnungswidrigkeiten, Stadtordnungsdienst"),
            # Versorgungssicherheit nur über die Beratung im Ausschuss unter „weitere“
            "w": v("261921", "Große Anfrage: Versorgungssicherheit der Krankenhäuser mit Trinkwasser",
                   gremien=("Ausschuss für Sicherheit, Ordnung und Bevölkerungsschutz",)),
            # weitere Fehltreffer vor dem Ziehen des Prüfbogens (02.11.2026)
            "x": v("261922", "Personelle Aufstockung im Bauordnungsamt"),
            "y": v("261923", "Linksliberale Gesinnungspolizei abschaffen"),
            "z": v("261924", "Große Anfrage: Miet-, Reinigungs-, Sicherheits- und Hausmeisterkosten der Unterkünfte"),
            "aa": v("261925", "Aufsichtsrat der Internationalen Beethovenfeste Bonn gGmbH"),
            "ab": v("261926", "Förderung des Sozialkompetenztrainings: Gewaltprävention an der Gesamtschule"),
            "ac": v("261927", "Parksituation für Mitarbeitende des Bundesamts für Bevölkerungsschutz"),
            "ad": v("261928", "Tagesordnungspunkte in nichtöffentlicher Sitzung des Ausschusses für Sicherheit, Ordnung "
                              "und Bevölkerungsschutz",
                    gremien=("Ausschuss für Sicherheit, Ordnung und Bevölkerungsschutz",)),
            "ae": v("261929", "Erlass einer Ordnungsbehördlichen Verordnung über das Offenhalten von Verkaufsstellen aus "
                              "Anlass des Weihnachtsmarktes", amt=a33, abteilung=a33),
        }
        self.d = dossier.daten(self.t, self.cache, {}, [], "2026-11-02", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_abteilungen_des_amts_33(self):
        self.assertEqual(self.by["261900"], ("weitere", "federführend: 33-2 Ordnungswidrigkeiten, Stadtordnungsdienst"))
        self.assertEqual(self.by["261901"], ("veranstaltungen", "federführend: 33-5 Veranstaltungskoordination und Märkte"))
        self.assertEqual(self.by["261902"], ("weitere", "federführend: 33 Bürgerdienste"))
        for ref in ("261903", "261904", "261905", "261906"):  # 33-1, 33-4, 33-6, Wahlen
            self.assertNotIn(ref, self.by, ref)

    def test_abteilungen_rueckwaertskompatibel(self):
        # aemter prüft weiter nur die Amtsbezeichnung; abteilungen nur die federführende Organisationseinheit
        p = self.cache["d"]
        self.assertEqual(dossier._zustaendig(dossier.Zustaendig(aemter=("33 ",)), p), "federführend: 33 Bürgerdienste")
        self.assertIsNone(dossier._zustaendig(dossier.Zustaendig(abteilungen=("33 ", "33-2 ")), p))
        self.assertIsNone(dossier._zustaendig(dossier.Zustaendig(abteilungen=("33-2 ",)), vorlage("1", "x", amt="33 Bürgerdienste")))

    def test_feuerwehr_und_straenge(self):
        self.assertEqual(self.by["261907"], ("feuerwehr", "federführend: 37 Feuerwehr und Rettungsdienst"))
        self.assertEqual(self.by["261908"], ("feuerwehr", "Titel: „Rettungsdienst“"))
        self.assertEqual(self.by["261909"][0], "bevoelkerungsschutz")
        self.assertEqual(self.by["261910"], ("ordnung", "Titel: „Sicherheitslage“"))
        self.assertEqual(self.by["261911"][0], "veranstaltungen")
        self.assertEqual(self.by["261912"], ("weitere", "Beratung im Ausschuss für Sicherheit, Ordnung und "
                                                        "Bevölkerungsschutz"))
        self.assertEqual(self.by["261929"], ("veranstaltungen", "Titel: „Offenhalten von Verkaufsstellen“"))
        bezirke = [r for s in self.d["straenge"] for r in s["vorlagen"] if "bezirk" in r]
        self.assertTrue(bezirke and all(r["reference"] in ("261901", "261911", "261929") for r in bezirke))

    def test_feuerwehrtopf(self):
        self.assertNotIn("261913", self.by)
        self.assertNotIn("261914", self.by)

    def test_verkehrs_versorgungs_und_cybersicherheit(self):
        for ref in ("261915", "261916", "261917", "261918", "261919", "261920"):
            self.assertNotIn(ref, self.by, ref)
        self.assertEqual(self.by["261921"][0], "weitere")

    def test_fehltreffer(self):
        for ref in ("261922", "261923", "261924", "261925", "261926", "261927", "261928"):
            self.assertNotIn(ref, self.by, ref)

    def test_regel_a_abfallwirtschaft(self):
        from pipeline import dossier
        # Prüfung 02.11.2026: Altpapier und Wertstoffe nicht, auch bei Mitberatung im Sicherheitsausschuss
        p = vorlage("262090", "Große Anfrage: Einführung smarter Altpapiercontainer mit Füllstandsüberwachung",
                    gremien=("Ausschuss für Sicherheit, Ordnung und Bevölkerungsschutz",))
        self.assertIsNone(dossier.zuordnen(self.t, p))

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertNotIn(self.t, ENTWUERFE)
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertEqual(self.t.pfad, "thema/sicherheit-und-ordnung/")
        self.assertEqual([k for k, *_ in self.t.straenge],
                         ["feuerwehr", "bevoelkerungsschutz", "ordnung", "veranstaltungen", "weitere"])
        self.assertEqual(self.t.fachausschuss, "Ausschuss für Sicherheit, Ordnung und Bevölkerungsschutz")
        self.assertEqual(self.t.produktbereich, "02")
        self.assertEqual(self.t.nach_bezirk, frozenset({"veranstaltungen"}))
        self.assertEqual(self.t.punkt_gremien, ("Rat", "Hauptausschuss", self.t.fachausschuss))
        strang, bahnen = {k for k, _, _ in self.t.straenge}, [k for k, _ in self.t.bahnen]
        self.assertLessEqual({r.strang for r in self.t.regeln}, strang)
        self.assertLessEqual(set(self.t.punkt_straenge), strang)
        self.assertLessEqual(set(self.t.bahn_gremien), set(bahnen))
        self.assertLessEqual({b for b, *_ in self.t.phasen}, set(bahnen))
        self.assertTrue({"bv", "fach", "finanz", "rat"} <= set(bahnen))
        self.assertEqual(sum(self.t.stichprobe_je_strang.values()), 25)
        self.assertNotIn(self.t.farben, [t.farben for t in ALLE if t.key != self.t.key])  # eigene Farben
        self.assertNotIn(self.t.symbol, [t.symbol for t in ALLE if t.key != self.t.key])

    def test_kandidat_ohne_teilwoerter(self):
        k = self.t.kandidat
        for titel in ("Verkehrssicherheit an der Kreuzung", "Spielplatz im Brandengarten", "Kanalsanierung Auf dem Brand",
                      "Mietspiegel aufgrund der Marktentwicklung", "Cyber- und Informationssicherheit"):
            self.assertIsNone(k.search(titel), titel)
        for titel in ("Sicherheit am Rheinufer", "Brand in der Innenstadt", "Kirmes in Beuel", "Rettungswagen"):
            self.assertIsNotNone(k.search(titel), titel)


def _v(ref, name, amt="01-2 Ratsbüro", abteilung=None, gremien=("Rat",), themen=()):
    """Vorlage mit Federführung (Abteilung), Themen und ohne Ortsbezug (für die Entwürfe Wirtschaft und Digital)."""
    p = vorlage(ref, name, amt=amt, gremien=gremien)
    p["themes"] = [{"theme": t, "method": "stichwort", "evidence": t} for t in themen]
    p["locations"] = []
    p["responsibility"] = [{"kind": "federfuehrend", "label": amt, "name": abteilung or amt}]
    return p


class Wirtschaft(unittest.TestCase):
    """Themenseite Wirtschaft und Wissenschaft (themenseiten/wirtschaft.py): mehrdeutige Wörter
    („Wirtschaft“, „Liegenschaften“), Liegenschaften ohne Vorlagen der Wohnseite, Amt 02 und Abteilung 03-4, „weitere“
    ohne Vorlagen anderer Themenseiten, zwei Fachausschüsse, Produktbereich 15."""

    def setUp(self):
        from pipeline.themenseiten import wirtschaft
        self.t = wirtschaft.THEMA
        a03, a02 = "03 Amt für Wirtschaftsförderung", "02 Amt für Internationales und globale Nachhaltigkeit"
        w, s = wirtschaft.WIRTSCHAFT, wirtschaft.WISSENSCHAFT
        self.cache = {
            "a": _v("262100", "Jahreswirtschaftsbericht 2026", amt=a03),
            "b": _v("262101", "Bonn-Information: Rückblick 2025 und Ausblick auf das Jahr 2026", amt=a03),
            "c": _v("262102", "Fortsetzung der Zwischennutzung des Viktoriabads ermöglichen", amt=a03,
                    abteilung="03-4 Liegenschaften"),
            "d": _v("262103", "Sachstand", amt=a03, abteilung="03-4 Liegenschaften"),
            "e": _v("262104", "30 Jahre UN-Stadt Bonn", amt=a02),
            "f": _v("262105", "Hilfe für die Menschen in Cherson", amt=a02),
            "g": _v("262106", "Grüne-Antrag: Wissenschaft im öffentlichen Raum sichtbarer machen", gremien=(s,)),
            "h": _v("262107", "Obst- und Gemüseverkaufsstand an der Erwin-Kranz-Halle", amt=a03),
            "i": _v("262108", "Große Anfrage: Hightech-Standort", gremien=(w,)),
            "j": _v("262109", "Sachstand zum Antrag", gremien=(w,)),
            # mehrdeutiges „Wirtschaft“
            "k": _v("262110", "Wirtschaftsplan des Theater Bonn 2026/27", gremien=(w,)),
            "l": _v("262111", "Bericht zur haushaltswirtschaftlichen Lage nach dem 3. Quartal 2026", gremien=(w,)),
            "m": _v("262112", "Anpassung der Regeln in der Parkraumbewirtschaftungszone Nordstadt", gremien=(w,)),
            "n": _v("262113", "Vertretung der Bundesstadt Bonn in Organen wirtschaftlicher Unternehmen, hier: "
                              "Aufsichtsrat der Tourismus & Congress GmbH", amt=a03),
            "o": _v("262114", "Verpachtung städtischer landwirtschaftlicher Flächen"),  # Liegenschaften, nicht Wirtschaft
            "p": _v("262115", "Wirtschaftsplan SGB 2027; Einsparungen", amt="85-St Stabsstelle"),
            # mehrdeutiges „Liegenschaften“
            "q": _v("262116", "Zukunft Bonner Bühnen – Bauliche Zukunft der Theaterliegenschaften", gremien=(w,)),
            "r": _v("262117", "Große Anfrage: Energieverbrauch kommunaler Liegenschaften", gremien=(w,)),
            "s": _v("262118", "Statusbericht zum Photovoltaikausbau auf den städtischen Liegenschaften"),
            "t": _v("262119", "Rahmenvereinbarung über die Lieferung von Schließfachsystemen für die Liegenschaften",
                    amt="10 Personal- und Organisationsamt"),
            # Formalien, Sammellisten, Bauanträge
            "u": _v("262120", "Punkte der nichtöffentlichen Sitzung", amt=a03, gremien=(w,)),
            "x": _v("262121", "Bestellung der Schriftführung für den Ausschuss für Wirtschaft, Liegenschaften und Arbeit",
                    amt=a03),
            "y": _v("262122", "Grundstück in Bonn, Beispielstraße [Hausnummer ausgelassen] - Neubau eines Wohnhauses",
                    amt="63-0 Besondere Verfahren"),
            # andere Themenseiten
            "z": _v("262123", "Beschlussvorlage \"Rhein in Flammen\"", amt="33 Bürgerdienste",
                    abteilung="33-5 Veranstaltungskoordination und Märkte", gremien=(w,)),
            "aa": _v("262124", "Weiterführung des moveBonn-Programms (Förderung des betrieblichen Mobilitätsmanagements "
                               "in Bonner Unternehmen)", amt="61-3 Stadtverkehr"),
            "ab": _v("262125", "FDP-Große Anfrage: Beethovenhalle", gremien=(w,)),
            "ac": _v("262126", "Langer Tag der Region 2026 in der Beethovenhalle", amt=a03),
            "ad": _v("262127", "Sanierung der Kunstrasenplätze gemäß EU-Verordnung"),
            "ae": _v("262128", "Einwohnerfrage: Trafostation und Glasfaserverteiler am Beispielplatz"),
        }
        self.d = dossier.daten(self.t, self.cache, {}, [], "2026-11-02", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["262100"], ("wirtschaft", "Titel: „Jahreswirtschaftsbericht“"))
        self.assertEqual(self.by["262101"][0], "zentren")
        self.assertEqual(self.by["262102"], ("liegenschaften", "Titel: „Zwischennutzung“"))
        self.assertEqual(self.by["262103"], ("liegenschaften", "federführend: 03-4 Liegenschaften"))
        self.assertEqual(self.by["262104"], ("wissenschaft", "Titel: „UN-Stadt“"))
        self.assertEqual(self.by["262105"], ("wissenschaft", "federführend: 02 Amt für Internationales und globale "
                                                             "Nachhaltigkeit"))
        self.assertEqual(self.by["262106"], ("wissenschaft", "Titel: „Wissenschaft“"))
        self.assertEqual(self.by["262107"], ("weitere", "federführend: 03 Amt für Wirtschaftsförderung"))
        self.assertEqual(self.by["262108"][0], "wirtschaft")
        self.assertEqual(self.by["262109"], ("weitere", "Beratung im Ausschuss für Wirtschaft, Liegenschaften und Arbeit"))
        self.assertEqual(self.by["262114"], ("liegenschaften", "Titel: „Verpachtung“"))
        self.assertEqual(self.by["262126"][0], "weitere")  # Veranstaltung in der Beethovenhalle bleibt

    def test_mehrdeutige_woerter(self):
        for ref in ("262110", "262111", "262112", "262113", "262115", "262116", "262117", "262118", "262119",
                    "262124", "262125", "262127", "262128"):
            self.assertNotIn(ref, self.by, ref)

    def test_formalien(self):
        for ref in ("262120", "262121", "262122"):
            self.assertNotIn(ref, self.by, ref)

    def test_liegenschaften_ohne_wohnseite(self):
        from pipeline.themenseiten import wohnen
        p = _v("262130", "Amerikanischer Club / Ergebnis des 4. Wertgutachtens", amt="03 Amt für Wirtschaftsförderung",
               abteilung="03-4 Liegenschaften")
        alt = dossier.zuordnen
        try:  # die Vorlage steht auf der Wohnseite (nachgebildet): weder Liegenschaften noch „weitere“
            dossier.zuordnen = lambda t, x, v=None: ("denkmal", "x") if t is wohnen.THEMA else alt(t, x, v)
            self.assertIsNone(alt(self.t, p))
        finally:
            dossier.zuordnen = alt
        self.assertEqual(dossier.zuordnen(self.t, p)[0], "liegenschaften")
        regeln = [r for r in self.t.regeln if r.strang == "liegenschaften"]
        self.assertTrue(regeln and all(r.ohne_seite is wohnen.THEMA for r in regeln))

    def test_andere_seiten_in_weitere(self):
        self.assertNotIn("262123", self.by)  # „Rhein in Flammen“ steht auf der Seite Sicherheit und Ordnung
        weitere = [r for r in self.t.regeln if r.strang == "weitere"]
        # alle anderen Seiten außer der Digitalseite, die ihrerseits alle Vorlagen dieser Seite überspringt
        ohne = {t.key for t in ALLE} - {self.t.key, "digital"}
        self.assertTrue(weitere and all({t.key for t in r.ohne_seite} == ohne for r in weitere))

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertNotIn(self.t, ENTWUERFE)
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertEqual(self.t.pfad, "thema/wirtschaft-und-wissenschaft/")
        self.assertEqual([k for k, *_ in self.t.straenge],
                         ["wirtschaft", "zentren", "liegenschaften", "wissenschaft", "weitere"])
        self.assertEqual(self.t.fachausschuss, ("Ausschuss für Wirtschaft, Liegenschaften und Arbeit",
                                                "Ausschuss für Wissenschaft, Europa und Internationales"))
        self.assertEqual(self.t.produktbereich, "15")
        self.assertEqual(self.t.seit, "2025-11-01")
        self.assertEqual(self.t.punkt_gremien, ("Rat", "Hauptausschuss", *self.t.fachausschuss))
        strang, bahnen = {k for k, _, _ in self.t.straenge}, [k for k, _ in self.t.bahnen]
        self.assertLessEqual({r.strang for r in self.t.regeln}, strang)
        self.assertLessEqual(set(self.t.punkt_straenge), strang)
        self.assertLessEqual(set(self.t.bahn_gremien), set(bahnen))
        self.assertLessEqual({b for b, *_ in self.t.phasen}, set(bahnen))
        self.assertTrue({"bv", "fach", "finanz", "rat", "wirtschaft", "wissenschaft"} <= set(bahnen))
        self.assertEqual(sum(self.t.stichprobe_je_strang.values()), 25)
        self.assertEqual(self.t.stichprobe_pfad.name, "stichprobe_wirtschaft.tsv")
        andere = [t for t in ALLE if t.key != self.t.key]
        self.assertNotIn(self.t.farben, [t.farben for t in andere])  # eigene Farben und eigenes Symbol
        self.assertNotIn(self.t.symbol, [t.symbol for t in andere])
        self.assertIn("WorldCCBonn", "".join(self.t.nicht_gezeigt).replace("World Conference Center Bonn", "WorldCCBonn"))

    def test_kandidat_ohne_teilwoerter(self):
        k = self.t.kandidat
        for titel in ("Verpachtung landwirtschaftlicher Flächen", "Parkraumbewirtschaftung in Beuel",
                      "Bericht zur haushaltswirtschaftlichen Lage", "Gremien in Beteiligungsunternehmen",
                      "Bauliche Zukunft der Theaterliegenschaften", "Lehrmittel für naturwissenschaftliche Fächer",
                      "Fortschreibung des Einzelhandelskonzepts", "Arbeitsprogramm des Amts für Umwelt",
                      "Müllbehälter am Europaring"):
            self.assertIsNone(k.search(titel), titel)
        for titel in ("Wirtschaftsplan 2027", "Liegenschaften der Stadt", "Internationale Konferenzen",
                      "Arbeitsmarkt in Bonn"):
            self.assertIsNotNone(k.search(titel), titel)


class Digital(unittest.TestCase):
    """Themenseite Digitale Verwaltung (themenseiten/digital.py): Stabsstelle CDO und Abteilung 10-2,
    vom Amt 10 sonst nur Wörter im Titel, keine Personalangelegenheiten und Büromöbel, „IT“ nur groß, digitale Wirtschaft
    nur auf der Wirtschaftsseite, kein Haushaltsabschnitt."""

    def setUp(self):
        from pipeline.themenseiten import digital
        self.t = digital.THEMA
        a10, d = "10 Personal- und Organisationsamt", digital.DIGITAL
        self.cache = {
            "a": _v("262200", "Dachstrategie Digitale Transformation", amt="Dezernat OB", abteilung="Stabsstelle CDO",
                    gremien=(d,)),
            "b": _v("262201", "Sachstand", amt="Dezernat OB", abteilung="Stabsstelle CDO"),
            "c": _v("262202", "Volt-Dringlichkeitsantrag: Aufarbeitung des IT-Ausfalls bei RegioIT am 3. März 2026",
                    gremien=(d,)),
            "e": _v("262203", "Sachstand Beschaffung", amt=a10, abteilung="10-2 IT"),
            "f": _v("262204", "Benutzungsfreundlichkeit der städtischen Website und des Terminbuchungsportals verbessern"),
            "g": _v("262205", "Organisationsuntersuchung im Amt für Kinder, Jugend und Familie",
                    amt="51 Amt für Kinder, Jugend und Familie"),
            "h": _v("262206", "Einleitungsbeschluss für das Projekt „Kinderspielplatzkontrolle–Digitales "
                              "Spielplatzmanagement“", amt=a10),
            "i": _v("262207", "Controllingbericht 2025", amt="33 Bürgerdienste", abteilung="33-4 Dienstleistungszentrum",
                    gremien=(d,)),
            # Personalangelegenheiten und Büromaterial (Amt 10)
            "j": _v("262208", "Wahl einer Beigeordneten bzw. eines Beigeordneten", amt=a10,
                    abteilung="10-1 Personal- und Organisationsentwicklung"),
            "k": _v("262209", "Monitoringbericht zur Stellenplan- und personalwirtschaftlichen Entwicklung I/2026",
                    amt=a10, abteilung="10-1 Personal- und Organisationsentwicklung", gremien=(d,)),
            "l": _v("262210", "Ausschreibung der Stelle einer bzw. eines Beigeordneten für das Dezernat I", amt=a10),
            "m": _v("262211", "Einleitung des Vergabeverfahrens für die Lieferung von Bürostühlen", amt=a10,
                    abteilung="10-3 Zentrale Dienste und internes Mobilitätszentrum"),
            "n": _v("262212", "Gesundheitsbericht für das Jahr 2025", amt=a10,
                    abteilung="10-4 Personalservice / Stabstelle Gesundheit"),
            "o": _v("262213", "Sachstand", amt=a10, abteilung="10-1 Personal- und Organisationsentwicklung"),
            # „IT“ nur in Großbuchstaben, digitale Wirtschaft, Verkehr, Stadthaus-Areal
            "p": _v("262214", "Bürgerantrag: Einführung von Kurzzeit-Anwohnerausweisen", amt="33 Bürgerdienste"),
            "q": _v("262215", "Anmeldeverfahren an den Schulen: Möglichkeit eines Zweit- und Drittwunsches"),
            "r": _v("262216", "Firmenjubiläum – 10 Jahre Digital Hub Region Bonn AG und Startup Week",
                    amt="03 Amt für Wirtschaftsförderung"),
            "s": _v("262217", "Koalitionsantrag: Digitale Fahrgastanzeige an der Haltestelle Universität/Markt",
                    themen=("verkehr",)),
            "t": _v("262218", "Zukunft Stadthaus-Areal: Sachstandsbericht"),
            "u": _v("262219", "Tagesordnungspunkte in nichtöffentlicher Sitzung", amt=a10, gremien=(d,)),
            "w": _v("262220", "Vertretung der Stadt Bonn im AR der Digital Hub AG", amt="03 Amt für Wirtschaftsförderung"),
        }
        self.d = dossier.daten(self.t, self.cache, {}, [], "2026-11-02", {})
        self.by = {r["reference"]: (s["key"], r["grund"]) for s in self.d["straenge"] for r in s["vorlagen"]}

    def test_straenge(self):
        self.assertEqual(self.by["262200"], ("strategie", "Titel: „Dachstrategie“"))
        self.assertEqual(self.by["262201"], ("strategie", "federführend: Stabsstelle CDO"))
        self.assertEqual(self.by["262202"], ("it", "Titel: „IT-Ausfalls“"))
        self.assertEqual(self.by["262203"], ("it", "federführend: 10-2 IT"))
        self.assertEqual(self.by["262204"][0], "online")
        self.assertEqual(self.by["262205"][0], "organisation")
        self.assertEqual(self.by["262206"], ("it", "Titel: „Digitales“"))
        self.assertEqual(self.by["262207"], ("weitere", "Beratung im Ausschuss für Digitalisierung, Dienstleistung und "
                                                        "Verwaltungsmodernisierung"))

    def test_leerer_strang_ausgeblendet(self):
        # „weitere“ erscheint nicht, solange er leer ist (Entscheidung 02.11.2026); die Regel bleibt
        cache = {k: v for k, v in self.cache.items() if k != "i"}
        d = dossier.daten(self.t, cache, {}, [], "2026-11-02", {})
        self.assertNotIn("weitere", [s["key"] for s in d["straenge"]])
        self.assertIn("weitere", [s.strang for s in self.t.regeln])
        self.assertIn("weitere", [s["key"] for s in self.d["straenge"]])

    def test_personalangelegenheiten(self):
        for ref in ("262208", "262209", "262210", "262211", "262212", "262213"):
            self.assertNotIn(ref, self.by, ref)

    def test_fehltreffer(self):
        for ref in ("262214", "262215", "262216", "262217", "262218", "262219", "262220"):
            self.assertNotIn(ref, self.by, ref)

    def test_ohne_wirtschaftsseite(self):
        from pipeline.themenseiten import wirtschaft
        self.assertEqual(dossier.zuordnen(wirtschaft.THEMA, self.cache["r"])[0], "wirtschaft")
        for r in self.t.regeln:  # jede Regel überspringt Vorlagen der Wirtschaftsseite: keine Doppelnennung
            seiten = r.ohne_seite if isinstance(r.ohne_seite, tuple) else (r.ohne_seite,)
            self.assertIn(wirtschaft.THEMA, seiten, r.strang)

    def test_ohne_haushaltsabschnitt(self):
        self.assertIsNone(self.t.produktbereich)
        self.assertNotIn("haushalt_betraege", self.d)
        html = dossier.body(self.t, self.d, "../../")
        self.assertNotIn('id="haushalt-produktbereich"', html)
        self.assertNotIn("#haushalt-produktbereich", html)
        self.assertIn('<a href="../../haushalt/">Haushalt auf einen Blick</a>', html)  # Hinweis unter „nicht zeigt“
        self.assertIn('<a href="#sitzungen">Nächste Sitzungen</a>', html)
        self.assertNotIn("kachel-haushalt", dossier._kachel(self.t, self.d))

    def test_veroeffentlicht(self):
        from pipeline.themenseiten import ENTWUERFE
        self.assertNotIn(self.t, ENTWUERFE)
        self.assertIn(self.t.key, [t.key for t in ALLE])
        self.assertEqual(self.t.pfad, "thema/digitale-verwaltung/")
        self.assertEqual([k for k, *_ in self.t.straenge], ["strategie", "online", "it", "organisation", "weitere"])
        self.assertEqual(self.t.fachausschuss, "Ausschuss für Digitalisierung, Dienstleistung und "
                                               "Verwaltungsmodernisierung")
        self.assertEqual(self.t.seit, "2025-11-01")
        self.assertEqual(self.t.punkt_gremien, ("Rat", "Hauptausschuss", self.t.fachausschuss))
        strang, bahnen = {k for k, _, _ in self.t.straenge}, [k for k, _ in self.t.bahnen]
        self.assertLessEqual({r.strang for r in self.t.regeln}, strang)
        self.assertLessEqual(set(self.t.punkt_straenge), strang)
        self.assertLessEqual(set(self.t.bahn_gremien), set(bahnen))
        self.assertLessEqual({b for b, *_ in self.t.phasen}, set(bahnen))
        self.assertLessEqual(set(self.t.stichprobe_je_strang), strang)
        self.assertEqual(sum(self.t.stichprobe_je_strang.values()), 25)
        andere = [t for t in ALLE if t.key != self.t.key]
        self.assertNotIn(self.t.farben, [t.farben for t in andere])
        self.assertNotIn(self.t.symbol, [t.symbol for t in andere])

    def test_kandidat_ohne_teilwoerter(self):
        k = self.t.kandidat
        for titel in ("Kurzzeit-Bewohnerparkausweise", "Zweit- und Drittwunsch", "Stellungnahme der Verwaltung",
                      "Anbindung der Klinik durch einen Serviceweg"):
            self.assertIsNone(k.search(titel), titel)
        for titel in ("IT-Ausfall", "Digitalisierung der Bauaufsicht", "Online-Terminvergabe", "Verwaltungsprozesse"):
            self.assertIsNotNone(k.search(titel), titel)
