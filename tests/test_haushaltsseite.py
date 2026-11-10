"""Seite haushalt/ (pipeline/haushaltsseite.py): Treemap der Produktbereiche, Ebenen 2 (Produktgruppen) und 3
(Aufwandsarten einer Produktgruppe)."""
import os
import re
import unittest
from unittest import mock

from pipeline import config, haushaltsseite as hs


def daten(ebenen, erweiterung=False, ertragsarten=False):
    """Daten der Seite mit oder ohne Ebenen 2 und 3 und Erweiterung (Ist 2024, Investitionen), unabhängig von Freigabe
    und Umgebung."""
    with mock.patch.object(hs.haushaltsplan, "EBENEN_FREIGEGEBEN", ebenen), \
            mock.patch.object(hs.haushaltsplan, "ERWEITERUNG_FREIGEGEBEN", erweiterung), \
            mock.patch.object(hs.haushaltsplan, "ERTRAGSARTEN_FREIGEGEBEN", ertragsarten), \
            mock.patch.dict(os.environ, {"HAUSHALT_EBENEN": "", "HAUSHALT_ERWEITERUNG": "", "HAUSHALT_ERTRAGSARTEN": ""}):
        return hs.daten()


def abschnitt(html, ziel):
    return html.split(f'<section id="{ziel}"')[1].split("</section>")[0]


class Treemap(unittest.TestCase):
    def test_flaechen_proportional_und_im_rechteck(self):
        werte = [372, 304, 304, 167, 137, 135, 124, 93, 85, 38, 35, 33, 18, 18, 10, 9, 1]
        rects = hs.squarify(werte, 0, 0, 1000, 560)
        self.assertEqual(len(rects), len(werte))
        for v, (x, y, w, h) in zip(werte, rects):
            self.assertAlmostEqual(w * h, v * 1000 * 560 / sum(werte), places=6)
            self.assertTrue(-1e-6 <= x and x + w <= 1000 + 1e-6 and -1e-6 <= y and y + h <= 560 + 1e-6)
        self.assertAlmostEqual(sum(w * h for *_, w, h in rects), 1000 * 560, places=3)

    def test_beispiel_aus_der_literatur(self):
        # Bruls, Huizing, van Wijk (2000), Abb. 4: 6, 6, 4, 3, 2, 2, 1 in einem Rechteck 6 × 4
        rects = hs.squarify([6, 6, 4, 3, 2, 2, 1], 0, 0, 6, 4)
        self.assertEqual([tuple(round(v, 3) for v in r) for r in rects[:2]], [(0, 0, 3, 2), (0, 2, 3, 2)])

    def test_zeilen_und_betraege(self):
        self.assertEqual(hs._zeilen("Kinder-, Jugend- und Familienhilfe", 20), ["Kinder-, Jugend- und", "Familienhilfe"])
        self.assertIsNone(hs._zeilen("Natur- und Landschaftspflege", 12))
        self.assertEqual(hs._euro(-84508), "−84.508 €")
        self.assertEqual(hs._betrag(5000), "5.000 €")   # sonst 0,0 Mio. €
        self.assertEqual(hs._betrag(140000), "0,1 Mio. €")
        self.assertEqual(hs._anker("1.04.07"), "pg-1-04-07")


class Seite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = daten(False)
        cls.html = hs.body(cls.d, "../")

    def test_ansichten_und_summen(self):
        self.assertEqual([a["titel"] for a in self.d["ansichten"]], ["Plan 2026", "Plan 2025", "Ist 2023"])
        # Plan 2025: Summe der Produktbereiche = Gesamtergebnisplan (haushalt/phase0/BERICHT.md: 1.797,0 Mio. €)
        self.assertAlmostEqual(self.d["ansichten"][1]["summe"] / 1e6, 1797.0, delta=0.1)
        self.assertEqual(len(self.d["produktbereiche"]), 17)

    def test_je_ansicht_und_format_alle_produktbereiche(self):
        self.assertEqual(self.html.count('<svg class="hh-svg'), 6 + 2)   # dazu Zuschussbedarf breit und hoch
        self.assertEqual(len(re.findall(r'<a href="#pb-\d\d" class="s[1-5]" aria-label=', self.html)), 6 * 17)
        self.assertEqual(len(set(re.findall(r'<tr id="(pb-\d\d)"', self.html))), 17)
        self.assertNotIn("2027", self.html.split("Was diese Seite nicht zeigt")[0])   # keine Finanzplanung

    def test_freigegeben(self):
        self.assertTrue(hs.haushaltsplan.EBENEN_FREIGEGEBEN)   # Prüfbogen im Gespräch freigegeben 28.10.2026

    def test_ohne_freigabe_nur_ebene_1(self):
        self.assertFalse(self.d["zoom"])
        self.assertNotIn("hh-ebene", self.html)
        self.assertNotIn("#zoom-", self.html)
        self.assertNotIn("#pg-", self.html)
        self.assertIn("Die Seite zeigt eine Ebene", self.html)
        self.assertEqual(hs.stil(self.d), "")

    def test_vorschau_ueber_umgebungsvariable(self):
        with mock.patch.object(hs.haushaltsplan, "EBENEN_FREIGEGEBEN", False):
            with mock.patch.dict(os.environ, {"HAUSHALT_EBENEN": "vorschau"}):
                self.assertTrue(hs.ebenen_an())
            with mock.patch.dict(os.environ, {"HAUSHALT_EBENEN": "ja"}):
                self.assertFalse(hs.ebenen_an())

    def test_themenseiten_verlinkt(self):
        for pfad in ("thema/kunst-und-kultur/", "thema/schule-und-bildung/", "thema/klima-und-umwelt/"):
            self.assertIn(f'href="../{pfad}"', self.html)


class Ebenen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = daten(True)
        cls.html = hs.body(cls.d, "../")
        cls.pb = {p["pb"]: p for p in cls.d["produktbereiche"]}

    def test_ebene_1_fuehrt_zu_ebene_2_tabelle_bleibt(self):
        self.assertEqual(len(re.findall(r'<a href="#zoom-\d\d" class="s[1-5]" aria-label=', self.html)), 6 * 17)
        self.assertNotIn('<a href="#pb-', self.html)
        self.assertEqual(len(set(re.findall(r'<tr id="(pb-\d\d)"', self.html))), 17)   # Sprungziele der Themenseiten
        self.assertEqual(self.html.count('<a href="#zoom-01">Produktgruppen und Aufwandsarten</a>'), 1)

    def test_abschnitte_in_den_karten_und_ziele_vorhanden(self):
        karten = self.html.split('<div class="hh-karten">')[1].split('<h2 id="tabelle">')[0]
        self.assertEqual(re.findall(r'<section id="zoom-(\d\d)" class="hh-ebene"', karten), [f"{i:02d}" for i in range(1, 18)])
        ids = re.findall(r'id="([^"]+)"', self.html)
        self.assertEqual(len(set(ids)), len(ids))
        ziele = set(re.findall(r'href="#([^"]+)"', self.html))
        self.assertFalse(ziele - set(ids), "jeder Sprung hat ein Ziel")
        gruppen = re.findall(r'<section id="(pg-1-\d\d-\d\d)" class="hh-ebene hh-pg"', karten)
        self.assertEqual(len(gruppen), sum(hs._mit_werten(g, self.d["ansichten"]) for p in self.pb.values()
                                           for g in p["produktgruppen"]))
        self.assertGreater(len(gruppen), 130)

    def test_ebene_2_produktgruppen(self):
        z = abschnitt(self.html, "zoom-04")
        self.assertIn('<a href="#produktbereiche">Alle Produktbereiche</a> › <span aria-current="location">04 Kultur und Wissenschaft</span>', z)
        self.assertIn(">Produktbereich 04 Kultur und Wissenschaft</h2>", z)
        self.assertEqual(re.findall(r'<figure class="hh-ansicht (hh-v\d)">', z), ["hh-v0", "hh-v1", "hh-v2"])
        self.assertEqual(z.count("<svg "), 6)
        self.assertEqual(z.count('hh-balken" aria-hidden="true"'), 3)   # Aufwandsarten des Produktbereichs
        plan26 = re.search(r'<figure class="hh-ansicht hh-v0">(.*?)</figure>', z).group(1)
        self.assertIn("<title>1.04.07 Stadtarchiv: 3,2 Mio. €, 3,4 % (Plan 2026)</title>", plan26)
        self.assertEqual(plan26.count('<a href="#pg-'), 2 * 12)   # 14 Produktgruppen, zwei mit 0 €
        self.assertNotIn("#pg-1-04-13", z)   # 0 € in allen Ansichten: nur in der Tabelle, ohne Ebene 3
        self.assertIn("1.04.13 Internationale Wissenschaft", z)
        self.assertIn("Name in Haushaltsplan 2023/2024: Z. f. Stadtgesch. u. Erinnerungskulturen", z)
        self.assertIn("Name in Haushaltsplan 2023/2024: Stadtmuseum", z)
        self.assertIn("Begriffe oben unter „So lesen Sie die Zahlen“.", z)
        self.assertNotIn("Kontenarten", z)   # Erklärung einmal im Akkordeon, nicht in jedem Abschnitt
        self.assertNotIn("2027", z)   # keine Finanzplanung

    def test_ebene_3_aufwandsarten_der_produktgruppe(self):
        g = abschnitt(self.html, "pg-1-04-07")
        self.assertIn('<a href="#produktbereiche">Alle Produktbereiche</a> › <a href="#zoom-04">04 Kultur und Wissenschaft</a> › '
                      '<span aria-current="location">1.04.07 Stadtarchiv</span>', g)
        self.assertIn(">Produktgruppe 1.04.07 Stadtarchiv</h2>", g)
        self.assertIn("Amt 41-2 · Name in Haushaltsplan 2023/2024: Z. f. Stadtgesch. u. Erinnerungskulturen", g)
        self.assertNotIn("<svg", g)   # keine Treemap im HTML; die Kacheln zeichnet site/haushalt.js aus den Balken
        self.assertEqual(g.count('hh-balken" aria-hidden="true"'), 3)
        self.assertIn('<i class="hh-f11" style="width:', g)
        self.assertEqual(len(re.findall(r'<i class="hh-f\d\d" style="width:[\d.]+%" data-b="\d+"></i>', g)), 15)
        self.assertNotIn("Kontenarten", g)
        self.assertEqual(re.findall(r'<tr class="hh-z(\d\d)">', g), ["11", "12", "13", "14", "15", "16"])
        self.assertIn('PB04.pdf#page=29">Haushaltsplan 2025/2026, PB04.pdf, S. 29</a>', g)
        self.assertNotIn("verantwortlich", g)
        # 1.01.29: dass dort Gebäude der Schulen und Bühnen bewirtschaftet werden, belegt das PDF nicht – kein Zusatz
        self.assertNotRegex(abschnitt(self.html, "pg-1-01-29"), r"Schul|Bühne")

    def test_negative_werte_ohne_flaeche_und_balkenstueck(self):
        z = abschnitt(self.html, "zoom-09")
        self.assertIn("<td>−84.508 €<br><small>negativ, ohne Fläche</small></td>", z)
        ist = re.search(r'<div class="hh-ansicht hh-v2 hh-balken"[^>]*>(.*?)</div>', z).group(1)
        self.assertNotIn("hh-f15", ist)   # Transferaufwendungen im Ist 2023 negativ
        self.assertIn("Negativ sind: Transferaufwendungen im Ist 2023 (−84.508 €)", z)
        g = abschnitt(self.html, "pg-1-09-04")
        self.assertIn("<td>−86.000 €<br><small>negativ, ohne Fläche</small></td>", g)
        self.assertNotIn("hh-f15", re.search(r'<div class="hh-ansicht hh-v2 hh-balken"[^>]*>(.*?)</div>', g).group(1))
        self.assertIn("Negativ sind: Transferaufwendungen im Ist 2023 (−86.000 €)", g)

    def test_erklaerungen_einmal_im_akkordeon(self):
        oben = self.html.split('<div class="hh-wahl"')[0]
        self.assertIn('<details class="hh-mehr" id="lesen">', oben)
        self.assertNotIn("<details open", self.html)   # alle Akkordeons zugeklappt
        self.assertEqual(self.html.count("Kontenarten, keine Aufgaben"), 1)
        self.assertIn("<summary>Was diese Seite nicht zeigt</summary>", self.html)
        self.assertIn("<summary>Quellen, Prüfung und Lizenz</summary>", self.html)
        self.assertIn('<script src="../haushalt.js" defer></script>', hs.stil(self.d))

    def test_leere_zeilen(self):
        z = abschnitt(self.html, "zoom-16")
        zeile = re.search(r'<tr class="hh-z11">.*?</tr>', z).group(0)
        self.assertEqual(zeile.count("<td>leer</td>"), 3)
        self.assertNotIn("hh-f11", z)   # kein Balkenstück für Personalaufwendungen

    def test_summen_je_ansicht(self):
        for p in self.pb.values():
            for a in self.d["ansichten"]:
                z17 = p[a["art"]][a["jahr"]]["betrag"]
                self.assertEqual(sum(t[a["art"]][a["jahr"]]["betrag"] for t in p["aufwandsarten"]), z17)
                pgs = sum(g[a["art"]][a["jahr"]]["betrag"] for g in p["produktgruppen"] if a["jahr"] in g[a["art"]])
                self.assertLessEqual(abs(pgs - z17), hs.haushaltsplan.TOLERANZ, (p["pb"], a["titel"]))
                for g in p["produktgruppen"]:
                    self.assertEqual(sum(t[a["art"]][a["jahr"]]["betrag"] for t in g["aufwandsarten"]),
                                     g[a["art"]][a["jahr"]]["betrag"])

    def test_farbstufen_nach_anteil(self):
        # Entscheidung 28.10.2026: eine Farbe in fünf Stufen nach Anteil, Legende unter jeder Treemap
        self.assertEqual([hs._stufe(x) for x in (0.5, 2, 4.9, 5, 10, 19.8, 20, 45)], [1, 2, 2, 3, 4, 4, 5, 5])
        plan26 = re.search(r'<figure class="hh-ansicht hh-v0">(.*?)</figure>', self.html).group(1)
        self.assertIn('<a href="#zoom-06" class="s4" aria-label="06 Kinder-', plan26)   # 19,8 % der Summe
        z = abschnitt(self.html, "zoom-04")
        self.assertIn('<a href="#pg-1-04-11" class="s5">', z)   # Theater: 45 % des Produktbereichs
        self.assertIn('<p class="hh-legende">Anteil am Produktbereich:', z)
        self.assertEqual(self.html.count('<p class="hh-legende">'), 1 + 17 + 1)   # dazu Zuschussbedarf
        self.assertNotRegex(self.html, r'<svg[^>]+ fill=')   # keine Themenfarben mehr an den Flächen

    def test_groesse_und_spaltennamen(self):
        # Vorgabe: Seite höchstens etwa 850 KB ohne Skript (bis 02.11.2026 800 KB; Erträge und Ergebnis: +27 KB, gepackt +4 KB)
        self.assertLess(len(self.html.encode()), 850_000)
        self.assertIn('td:nth-of-type(1)::before { content: "Ist 2023: "; }', hs.stil(self.d))

    def test_farben_fest(self):
        css = (config.ROOT / "site" / "page.css").read_text(encoding="utf-8")
        farben = dict(re.findall(r"\.hh-f(1[1-6]), \.hh-z1[1-6] > th::before \{ background: (#[0-9a-f]{6}); \}", css))
        self.assertEqual(sorted(farben), ["11", "12", "13", "14", "15", "16"])
        self.assertEqual(len(set(farben.values())), 6)


class ErtraegeUndErgebnis(unittest.TestCase):
    """Erweiterung Phase 1 (Entscheidungen 02.11.2026): Zeile 10 und 18, je Einwohner mit IT.NRW je Jahr."""
    @classmethod
    def setUpClass(cls):
        cls.d = daten(False)
        cls.html = hs.body(cls.d, "../")
        cls.teil = cls.html.split('<h2 id="ergebnis">')[1].split('<details class="hh-mehr">')[0]

    def test_summen_wie_gesamtergebnisplan(self):
        # haushalt/phase0/ERWEITERUNG.md: Plan 2026 Erträge 1.776,1, Ergebnis −108,0 Mio. € (gepp.pdf S. 2)
        plan26 = self.d["ansichten"][0]
        self.assertAlmostEqual(plan26["ertrag"] / 1e6, 1776.1, delta=0.1)
        self.assertAlmostEqual(plan26["ergebnis"] / 1e6, -108.0, delta=0.1)
        self.assertEqual(plan26["ertrag"] - plan26["summe"], plan26["ergebnis"])

    def test_je_einwohner(self):
        self.assertEqual(hs.einwohner("plan", 2026), 323_336)   # jüngster Stand 31.12.2024
        self.assertEqual(hs.einwohner("ist", 2023), 321_680)
        z = self.teil.split('<tr id="erg-03">')[1].split("</tr>")[0]
        self.assertIn("−49,3 Mio. €<br><small>−152 € je Einwohner</small>", z)   # −49.254.097 / 323.336
        self.assertIn("−35,8 Mio. €<br><small>−111 € je Einwohner</small>", z)   # Ist 2023 / 321.680

    def test_zuschussbedarf_ohne_ueberschuesse(self):
        figur = self.teil.split('<figure class="hh-erg">')[1].split("</figure>")[0]
        flaechen = re.findall(r'<a href="#erg-(\d\d)"', figur)
        self.assertEqual(len(flaechen), 2 * 14)   # breit und hoch, je 14 Produktbereiche mit negativem Ergebnis
        for pb in ("11", "15", "16"):
            self.assertNotIn(pb, flaechen)
        self.assertIn("Einen Überschuss haben 11 Ver- und Entsorgung, 15 Wirtschaft und Tourismus, 16 Allgemeine Finanzwirtschaft;", figur)
        self.assertIn("IT.NRW", self.html)



class Erweiterung(unittest.TestCase):
    """Ist 2024 aus dem Jahresabschluss, Veränderung und Investitionen (haushalt/PHASE5.md)."""
    @classmethod
    def setUpClass(cls):
        cls.d = daten(True, erweiterung=True)
        cls.html = hs.body(cls.d, "../")

    def test_ohne_freigabe_nicht_sichtbar(self):
        d = daten(True)
        self.assertNotIn("erweiterung", d)
        self.assertNotIn('id="investitionen"', hs.body(d, "../"))

    def test_vier_ansichten_und_ist_2024_auf_allen_ebenen(self):
        self.assertEqual([a["titel"] for a in self.d["ansichten"]], ["Plan 2026", "Plan 2025", "Ist 2024", "Ist 2023"])
        p = next(p for p in self.d["produktbereiche"] if p["pb"] == "03")
        for x in (p["ist"][2024], p["ertrag"]["ist"][2024], p["produktgruppen"][0]["ist"][2024],
                  p["aufwandsarten"][0]["ist"][2024]):
            self.assertEqual(x["ausgabe"], "Jahresabschluss 2024")
        self.assertIn('id="hh-ist2024"', self.html)
        self.assertIn(".hh-v3", (config.ROOT / "site" / "page.css").read_text(encoding="utf-8"))

    def test_veraenderung_nur_gleicher_art(self):
        teil = self.html.split('<h2 id="veraenderung">')[1].split("</table>")[0]
        self.assertIn("<th scope=\"col\">Ist 2024 zu Ist 2023</th><th scope=\"col\">Ist 2024 zum Ansatz 2024</th>"
                      "<th scope=\"col\">Plan 2026 zu Plan 2025</th>", teil)
        self.assertEqual(hs._delta({"betrag": 5}, {"betrag": -10}), "+15 €")   # ohne Prozent bei negativem Ausgangswert
        self.assertEqual(hs._delta({"betrag": 3_000_000}, {"betrag": 2_000_000}), "+1,0 Mio. €<br><small>+50,0 %</small>")
        self.assertIn("1.771,1 Mio. €", self.html)   # Ansatz der Satzung
        self.assertIn("1.819,6 Mio. €", self.html)   # fortgeschriebener Ansatz (Jahresabschluss)

    def test_investitionen_summen(self):
        # haushalt/PHASE5.md: Gesamtfinanzplan und Gesamtfinanzrechnung, Zeilen 6, 13, 10 und 14
        teil = self.html.split('<h2 id="investitionen">')[1].split("</table>")[0]
        zeile = lambda name: re.sub(r"<[^>]+>", " ", teil.split(name)[1].split("</tr>")[0]).split()
        self.assertEqual(" ".join(zeile("Investive Auszahlungen (Zeile 13)")),
                         "169,0 Mio. € 225,6 Mio. € 447,6 Mio. € 369,4 Mio. € 368,6 Mio. €")
        self.assertEqual(" ".join(zeile("Saldo (Zeile 14)")),
                         "−109,6 Mio. € −190,1 Mio. € −343,3 Mio. € −297,3 Mio. € −285,6 Mio. €")
        self.assertIn("Ohne Teilfinanzrechnung im Jahresabschluss 2024: 17 Stiftungen.", self.html)
        self.assertIn("Jahresabschluss-2024_Teil-2.pdf#page=", self.html)



class Ertragsarten(unittest.TestCase):
    """Ertragsarten (Zeilen 1–9) in den Ebenen 2 und 3 (haushalt/PHASE6.md)."""
    @classmethod
    def setUpClass(cls):
        cls.d = daten(True, erweiterung=True, ertragsarten=True)
        cls.html = hs.body(cls.d, "../")

    def test_ohne_freigabe_nicht_sichtbar(self):
        self.assertNotIn("Woher kommt das Geld", hs.body(daten(True, erweiterung=True), "../"))

    def test_summe_und_ist_2024(self):
        p = next(p for p in self.d["produktbereiche"] if p["pb"] == "03")
        oeff = next(e for e in p["ertragsarten"] if e["zeile"] == 4)
        self.assertEqual(oeff["ist"][2024]["betrag"], 13_077_058)   # 13.077.057,82 € (Prüfbogen, S. 180)
        self.assertEqual(oeff["plan"][2026]["betrag"], 12_975_145)   # Prüfbogen, PB03.pdf S. 1
        for p in self.d["produktbereiche"]:
            for art, j in (("plan", 2026), ("ist", 2023), ("ist", 2024)):
                teile = sum(e[art][j]["betrag"] for e in p["ertragsarten"] if j in e[art])
                self.assertLessEqual(abs(teile - p["ertrag"][art][j]["betrag"]), 1_500, (p["pb"], art, j))

    def test_abschnitt_in_jeder_ebene(self):
        teil = self.html.split('<section id="zoom-03"')[1].split("</section>")[0]
        self.assertIn("Woher kommt das Geld? Ertragsarten", teil)
        self.assertIn("Ohne Betrag in allen Ansichten:", teil)   # leere Ertragsarten nur als Liste
        self.assertNotIn('<tr class="hh-e1">', teil)            # keine Steuern im PB 03
        pg = self.html.split('<section id="pg-1-11-03"')[1].split("</section>")[0]
        self.assertIn('<tr class="hh-e4"><th scope="row">Öffentlich-rechtliche Leistungsentgelte</th>', pg)
        self.assertIn('hh-balken hh-eb', pg)                     # Balken ohne Kacheln (site/haushalt.js)


if __name__ == "__main__":
    unittest.main()


class Massnahmen(unittest.TestCase):
    """Einzelmaßnahmen aus Teilfinanzplan B (Option 7, freigegeben 10.11.2026): nur mit den Investitionen."""
    @classmethod
    def setUpClass(cls):
        cls.d = daten(True, erweiterung=True)
        cls.html = hs.body(cls.d, "../")

    def test_nur_mit_investitionen(self):
        self.assertNotIn("massnahmen", daten(True))
        self.assertIn("massnahmen", self.d)

    def test_liste_je_produktgruppe(self):
        z = abschnitt(self.html, "pg-1-12-01")
        self.assertIn('<details class="hh-mn"><summary>Investitionsmaßnahmen (', z)
        self.assertIn("<th scope=\"row\">Viktoriabrücke BN</th>", z)
        self.assertIn('<td data-l="Ansatz 2025">12.300.000 €<br><small>Einzahlungen 8.000.000 €</small></td>', z)
        self.assertIn("PB12.pdf#page=15", z)
        self.assertIn("Auerberger-Mitte BN <small>(Bezeichnung abgeleitet)</small>", self.html)

    def test_alle_uebernommenen_einmal(self):
        self.assertEqual(self.html.count('<details class="hh-mn">'), len(self.d["massnahmen"]))
        self.assertEqual(sum(map(len, self.d["massnahmen"].values())), 315)
        self.assertNotRegex(self.html, r"Leibrente|Intendantenvertrag")

    def test_uebersicht_und_grenzen(self):
        teil = self.html.split('<h3 id="massnahmen">')[1].split("</details>")[0]
        self.assertEqual(teil.count('<tr><th scope="row">'), 10)
        self.assertIn("nennt 315 Investitionsmaßnahmen", teil)
        self.assertIn("je Maßnahme mit Ansatz 2025 oder 2026", self.html)
        self.assertIn("28 von 28 verglichenen gleich", self.html)
