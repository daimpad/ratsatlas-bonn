"""Strukturdaten (pipeline/strukturdaten.py): Regeln des Datenvertrags an erfundenen Daten und Prüfung der Dateien im
Repository (data/strukturdaten/)."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import config, strukturdaten as sd

BEZIRKE = [("110", "110 Zentrum", "Stadtbezirk Bonn"), ("129", "129 Kottenforst", "Stadtbezirk Bad Godesberg"),
           ("495", "495 Lengsdorf", "Stadtbezirk Hardtberg")]


def _atlas(tmp):
    roh = Path(tmp)
    themen = [{"themeId": "t0", "themeName": "Bevölkerung", "fileName": "./Statistische_Bezirke-t0.js?r=X"},
              {"themeId": "t1", "themeName": "Haushalte", "fileName": "./Statistische_Bezirke-t1.js?r=Y"}]
    (roh / "data.js").write_text("﻿" + json.dumps({"version": "1.3", "geographies": [{
        "id": "Statistische_Bezirke", "features": [{"id": i, "name": n, "filters": [{"name": b}]} for i, n, b in BEZIRKE],
        "themes": themen}]}), encoding="utf-8")
    vgl = [10, 20, 0, 5, 35]
    (roh / "Statistische_Bezirke-t0.js").write_text(json.dumps({"indicators": [
        {"id": "i0", "name": "Einwohner", "date": "2024", "values": [10, "NaN", 25], "comparisonValues": vgl,
         "properties": [{"name": "metatext", "value": "<b>Gemeldete</b> Bevölkerung"}]},
        {"id": "i36", "name": "Bedarfsgemeinschaften nach SGB II", "date": "2024", "values": ["NaN", "NaN", 4.5],
         "comparisonValues": [1, 2, 3, 4, 10],
         "properties": [{"name": "metatext", "value": "Daten der Bundesagentur (* = absolute Fallzahl unter 10)"}]},
        {"id": "i45", "name": "Wohnungsgrößen", "date": "1 - Raum", "values": [5.0, "NaN", 3.2],
         "comparisonValues": [1, 1, 1, 1, 1], "properties": []},
        {"id": "i21", "name": "Häufigster Zuwanderungshintergrund", "date": "2024", "type": "categoric",
         "values": ["Syrien", "NaN", "Polen"], "comparisonValues": ["a", "b", "c", "d", "e"], "properties": []},
    ]}), encoding="utf-8")
    (roh / "Statistische_Bezirke-t1.js").write_text(json.dumps({"indicators": [
        {"id": "i24", "name": "Zahl der Haushalte", "date": "2017", "values": [5, "NaN", 62116],
         "comparisonValues": [1, 2, 3, 4, 170], "properties": []},
    ]}), encoding="utf-8")
    return roh


class Atlas(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        ind, werte, plaus = sd.atlas(_atlas(self._tmp.name), "2026-11-10")
        self.ind = {i["indikator_id"]: i for i in ind}
        self.werte = {(w["raumebene"], w["raum_id"], w["indikator_id"], w["jahr"]): w for w in werte}
        self.plaus = plaus

    def tearDown(self):
        self._tmp.cleanup()

    def test_werte_unveraendert_mit_quellobjekt(self):
        w = self.werte[("statistischer_bezirk", "110", "bonn-sda-i0", "2024")]
        self.assertEqual((w["wert"], w["status"]), ("10", "ok"))
        self.assertTrue(w["quellobjekt"].endswith("Statistische_Bezirke-t0.js#i0/2024"))
        self.assertEqual(self.werte[("gesamtstadt", "bonn", "bonn-sda-i0", "2024")]["wert"], "35")
        self.assertEqual(self.werte[("stadtbezirk", "4", "bonn-sda-i0", "2024")]["wert"], "5")
        self.assertEqual(self.ind["bonn-sda-i0"]["metatext"], "Gemeldete Bevölkerung")

    def test_nan_regeln(self):
        # nahezu unbewohnter Bezirk: fehlt; Daten der Bundesagentur in bewohntem Bezirk: geheim
        self.assertEqual(self.werte[("statistischer_bezirk", "129", "bonn-sda-i0", "2024")]["status"], "fehlt")
        self.assertEqual(self.werte[("statistischer_bezirk", "129", "bonn-sda-i36", "2024")]["status"], "fehlt")
        w = self.werte[("statistischer_bezirk", "110", "bonn-sda-i36", "2024")]
        self.assertEqual((w["status"], w["wert"]), ("geheim", ""))
        self.assertIn("Fallzahl unter 10", self.ind["bonn-sda-i36"]["geheimhaltung"])

    def test_haushalte_2017_nicht_uebernommen(self):
        w = self.werte[("statistischer_bezirk", "495", "bonn-sda-i24", "2017")]
        self.assertEqual((w["status"], w["wert"]), ("fehlt", ""))
        self.assertEqual(self.werte[("gesamtstadt", "bonn", "bonn-sda-i24", "2017")]["status"], "fehlt")
        self.assertIn(("bonn-sda-i24", "2017", "nicht übernommen"), [(p["indikator_id"], p["jahr"], p["befund"]) for p in self.plaus])

    def test_verteilung_und_kategorie(self):
        self.assertIn("bonn-sda-i45-1-raum", self.ind)
        self.assertEqual(self.ind["bonn-sda-i45-1-raum"]["typ"], "anteil")
        self.assertEqual(self.werte[("statistischer_bezirk", "110", "bonn-sda-i45-1-raum", "2025")]["wert"], "5")
        self.assertEqual(self.ind["bonn-sda-i21"]["typ"], "kategorie")
        self.assertEqual(self.werte[("statistischer_bezirk", "495", "bonn-sda-i21", "2024")]["wert"], "Polen")

    def test_typ_aus_metatext_nicht_aus_namen(self):
        self.assertEqual(sd.TYP["i39"], ("quote", "je 1.000 Einwohner"))
        self.assertEqual(sd.BRUCH["i19"], ("i18", "i0", 100))
        self.assertNotIn("i38", sd.BRUCH)   # in fünf Jahren mit anderer Zahl der Haushalte berechnet

    def test_summenpruefung(self):
        # i0: Summe 35 = ganz Bonn 35, kein Hinweis; i36: Summe 4,5 ≠ 10, Hinweis
        befunde = {(p["indikator_id"], p["befund"]) for p in self.plaus}
        self.assertNotIn(("bonn-sda-i0", "Summe weicht ab"), befunde)
        self.assertIn(("bonn-sda-i36", "Summe weicht ab"), befunde)


class Geometrie(unittest.TestCase):
    def test_atlas_geometrie_in_wgs84(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "g.js"
            p.write_text(json.dumps({"boundingBox": "780718 6555338 803539 6582724", "pixelWidth": 100, "pixelHeight": 100,
                                     "features": [{"d": "110", "p": [[0, 100, 100, 0, 0, -100]]}]}))
            g = sd._atlas_geometrie(p)["110"]
        ring = g["coordinates"][0][0]
        self.assertEqual(ring[0], ring[-1])
        lon, lat = ring[0]
        self.assertAlmostEqual(lon, 7.0134, places=3)    # linke Kante, oben
        self.assertAlmostEqual(lat, 50.7814, places=3)   # oberer Rand der Box (y = 6.582.724 m)

    def test_stadtbezirke_nummern_wie_im_atlas(self):
        g = sd.stadtbezirke(config.STADTBEZIRKE)
        self.assertEqual([f["properties"]["raum_id"] for f in g["features"]], ["1", "2", "3", "4"])
        self.assertEqual(g["features"][2]["properties"]["name"], "Beuel")


def _streifen(ids, lon0=7.0, lon1=7.23, lat0=50.62, lat1=50.79):
    """Erfundene Bezirke als senkrechte Streifen über dem Stadtgebiet (decken es ganz ab)."""
    schritt = (lon1 - lon0) / len(ids)
    return [_quadrat(lon0 + i * schritt, lat0, lon0 + (i + 1) * schritt, lat1) for i in range(len(ids))]


class StadtGeometrie(unittest.TestCase):
    """Geometrie der Stadt (OD=4859): Feldnamen unbekannt, daher strenge Prüfung statt Raten."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.atlas = json.loads((_atlas(self._tmp.name) / "data.js").read_text(encoding="utf-8-sig"))
        self.datei = Path(self._tmp.name) / "stadt.geojson"

    def tearDown(self):
        self._tmp.cleanup()

    def _pruefe(self, feats):
        self.datei.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
        return sd.stadt_geometrie(self.datei, self.atlas)

    def test_nummer_als_zahl_oder_text_unter_beliebigem_feldnamen(self):
        flaechen = _streifen(["110", "129", "495"])
        geo = self._pruefe([{"properties": {"STAT_BEZ": int(i), "NAME": "x"}, "geometry": g}
                            for i, g in zip(("110", "129", "495"), flaechen)])
        self.assertEqual(sorted(geo), ["110", "129", "495"])
        geo = self._pruefe([{"properties": {"name": "x", "nr": i}, "geometry": g}
                            for i, g in zip(("110", "129", "495"), flaechen)])
        self.assertEqual(geo["129"], flaechen[1])

    def test_abweichungen_fuehren_zum_abbruch(self):
        flaechen = _streifen(["110", "129", "495"])
        faelle = {
            "2 statt 3 Flächen": [{"properties": {"nr": i}, "geometry": g} for i, g in zip(("110", "129"), flaechen)],
            "kein Feld": [{"properties": {"nr": i}, "geometry": g} for i, g in zip(("110", "129", "496"), flaechen)],
            "nicht in WGS84": [{"properties": {"nr": i}, "geometry": _quadrat(365000, 5620000, 366000, 5621000)}
                               for i in ("110", "129", "495")],
            "decken nur": [{"properties": {"nr": i}, "geometry": _quadrat(7.0, 50.62, 7.01, 50.63)}
                           for i in ("110", "129", "495")],
        }
        for meldung, feats in faelle.items():
            with self.subTest(meldung):
                with self.assertRaisesRegex(sd.GeometrieFehler, meldung):
                    self._pruefe(feats)

    def test_freigabe_noch_offen(self):
        # Entscheidung 10.11.2026: erst Vergleich, Übernahme erst nach Freigabe
        self.assertFalse(sd.GEOMETRIE_FREIGEGEBEN)


class Wanderung(unittest.TestCase):
    """Lieferung der Statistikstelle (Format laut strukturdaten/wanderung/LIEFERVORLAGE.md); Zahlen erfunden."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        roh = _atlas(self._tmp.name)
        self.meta = json.loads((roh / "data.js").read_text(encoding="utf-8-sig"))
        _, self.werte_atlas, _ = sd.atlas(roh, "2026-11-10")   # Einwohner 2024: 110 → 10, 129 → NaN, 495 → 25
        self.datei = Path(self._tmp.name) / "wanderung.tsv"

    def tearDown(self):
        self._tmp.cleanup()

    def _lies(self, text, trenner="\t"):
        self.datei.write_text(text.replace("\t", trenner), encoding="utf-8")
        return sd.wanderung(self.datei, self.meta, self.werte_atlas, "2026-11-10", {"lieferdatum": "2026-12-01"})

    KOPF = "raumebene\traum_id\tjahr\tzuzuege_aussen\tfortzuege_aussen\tzuzuege_innen\tfortzuege_innen\n"

    def test_werte_saldo_und_geheimhaltung(self):
        ind, werte, plaus = self._lies(self.KOPF + "statistischer_bezirk\t110\t2024\t5\t2\t3\t1\n"
                                       "statistischer_bezirk\t495\t2024\t1.200\t4\t*\t3\n"
                                       "gesamtstadt\tbonn\t2024\t1205\t6\t3\t4\n")
        w = {(r["raum_id"], r["indikator_id"]): r for r in werte}
        self.assertEqual((w[("110", "bonn-wan-zuzuege_aussen")]["wert"], w[("110", "bonn-wan-zuzuege_aussen")]["status"]),
                         ("5", "ok"))
        self.assertEqual(w[("495", "bonn-wan-zuzuege_aussen")]["wert"], "1200")          # Tausenderpunkt
        self.assertEqual((w[("110", "bonn-wan-saldo")]["wert"], w[("110", "bonn-wan-saldo")]["status"]), ("5", "abgeleitet"))
        self.assertEqual(w[("110", "bonn-wan-saldo_je_1000")]["wert"], "500")            # 5 / 10 Einwohner × 1.000
        self.assertEqual((w[("495", "bonn-wan-zuzuege_innen")]["status"], w[("495", "bonn-wan-saldo")]["status"]),
                         ("geheim", "fehlt"))
        self.assertTrue(w[("110", "bonn-wan-zuzuege_aussen")]["quellobjekt"].endswith("#Zeile 2"))
        i = {r["indikator_id"]: r for r in ind}
        self.assertEqual(i["bonn-wan-saldo_je_1000"]["typ"], "quote")
        self.assertEqual(i["bonn-wan-saldo"]["abrufdatum"], "2026-12-01")
        self.assertEqual(i["bonn-wan-zuzuege_aussen"]["raumebenen"], "gesamtstadt;statistischer_bezirk")
        self.assertEqual(plaus, [])   # innen nicht vollständig (geheim) → keine Ausgleichsprüfung; Summen stimmen

    def test_plausibilitaet_und_csv_mit_semikolon(self):
        _, _, plaus = self._lies(self.KOPF + "statistischer_bezirk\t110\t2024\t5\t2\t3\t1\n"
                                 "statistischer_bezirk\t495\t2024\t7\t4\t2\t3\n"
                                 "gesamtstadt\tbonn\t2024\t13\t6\t5\t4\n", ";")
        gruende = [p["grund"] for p in plaus]
        self.assertIn("Zuzüge innerhalb Bonns 5, Fortzüge innerhalb Bonns 4: sollten gleich sein", gruende)
        self.assertIn("Summe der Bezirke 12, ganz Bonn laut Lieferung 13", gruende)

    def test_fehler_brechen_ab(self):
        for zeile, meldung in (("statistischer_bezirk\t999\t2024\t1\t1\t1\t1", "unbekannt"),
                               ("statistischer_bezirk\t110\t2024\t-1\t1\t1\t1", "keine ganze Zahl"),
                               ("statistischer_bezirk\t110\tJahr\t1\t1\t1\t1", "unbekannt")):
            with self.subTest(meldung), self.assertRaisesRegex(SystemExit, meldung):
                self._lies(self.KOPF + zeile + "\n")
        with self.assertRaisesRegex(SystemExit, "Spalten fehlen: fortzuege_innen"):
            self._lies("raumebene\traum_id\tjahr\tzuzuege_aussen\tfortzuege_aussen\tzuzuege_innen\n")

    def test_ortsteil_ohne_summe_der_umzuege_innerhalb_bonns(self):
        ind, werte, _ = self._lies(self.KOPF + "statistischer_bezirk\t110\t2024\t5\t2\t3\t1\n"
                                   "statistischer_bezirk\t495\t2024\t7\t4\t1\t3\n")
        ind_alle = ind + [{"indikator_id": "bonn-sda-i0", "typ": "anzahl"}]
        out = {r["indikator_id"]: r for r in sd.ortsteilwerte(self.werte_atlas + werte, ind_alle, {"a": ["110", "495"]})
               if r["jahr"] == "2024"}
        self.assertEqual(out["bonn-wan-zuzuege_aussen"]["wert"], "12")
        self.assertNotIn("bonn-wan-zuzuege_innen", out)                 # zwischen 110 und 495 doppelt gezählt
        self.assertEqual((out["bonn-wan-saldo"]["wert"], out["bonn-wan-saldo"]["status"]), ("6", "abgeleitet"))
        self.assertEqual(out["bonn-wan-saldo_je_1000"]["wert"], "171.4")  # 6 / 35 Einwohner × 1.000

    def test_vorlage_wird_gelesen(self):
        vorlage = Path(__file__).resolve().parent.parent / "strukturdaten" / "wanderung" / "vorlage_wanderung.tsv"
        spalten, zeilen = sd._lies_lieferung(vorlage)
        self.assertEqual(set(spalten), {"raumebene", "raum_id", "jahr", *sd.WANDERUNG_SPALTEN})
        self.assertEqual(len(zeilen), 4)


class Wegweiser(unittest.TestCase):
    def test_reihen_je_kommune_und_jahr(self):
        with tempfile.TemporaryDirectory() as tmp:
            roh = Path(tmp)
            (roh / "indikatoren.json").write_text(json.dumps([
                {"friendlyUrl": fu, "name": fu, "unit": "%", "years": [2022, 2023], "source": "IT.NRW",
                 "explanation": "Erklärung", "calculation": "a / b"} for fu in sd.WW_INDIKATOREN]))
            for fu in sd.WW_INDIKATOREN:
                (roh / f"{fu}.json").write_text(json.dumps({"years": [2022, 2023], "data": {
                    "regions": [{"friendlyUrl": k} for k in sd.WW_KOMMUNEN],
                    "indicators": [{"regionYearValues": [[1.5, 2.0], [None, 3], [4, 5]]}]}}))
            ind, gesamt = sd.wegweiser(roh, "2026-11-10")
        self.assertEqual(len(ind), len(sd.WW_INDIKATOREN))
        self.assertEqual(ind[0]["lizenz"], "CC0 1.0")
        reihe = [(g["kommune"], g["jahr"], g["wert"]) for g in gesamt if g["wegweiser_friendly_url"] == "altenquotient"]
        self.assertEqual(reihe, [("bonn", "2022", "1.5"), ("bonn", "2023", "2"), ("koeln", "2023", "3"),
                                 ("wuppertal", "2022", "4"), ("wuppertal", "2023", "5")])


class DateienImRepository(unittest.TestCase):
    def test_vertrag_eingehalten(self):
        if not (sd.OUT / "meta.json").exists():
            self.skipTest("data/strukturdaten/ fehlt")
        self.assertEqual(sd.pruefen(sd.OUT), [])
        meta = json.loads((sd.OUT / "meta.json").read_text(encoding="utf-8"))
        self.assertTrue(meta["veroeffentlichen"])
        self.assertEqual(meta["vertrag_version"], sd.VERTRAG)

    def test_verifikation_ohne_abweichung(self):
        """Phase 4: Stichprobe gegen zweite Veröffentlichungen der Statistikstelle und den CSV-Export des Wegweisers."""
        path = sd.OUT / sd.VERIFIKATION
        if not path.exists():
            self.skipTest("audit_verifikation.tsv fehlt")
        with open(path, encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f, delimiter="\t"))
        self.assertGreaterEqual(len(zeilen), 20)
        self.assertEqual([z["nr"] for z in zeilen if not z["ergebnis"].startswith("gleich")], [])
        # gerundete Gleichheit nur mit Begründung
        self.assertTrue(all(z["bemerkung"] for z in zeilen if z["ergebnis"] == "gleich (gerundet)"))
        # die drei mit dem Nachbarbezirk zusammengefassten Bezirke sind belegt
        belegt = {z["raum_id"] for z in zeilen if "enthalten" in z["bemerkung"]}
        self.assertEqual(belegt, set(sd.ZUSAMMENGEFASST.values()))
        meta = json.loads((sd.OUT / "meta.json").read_text(encoding="utf-8"))
        self.assertTrue(any("127, 381 und 388 enthalten" in h for h in meta["hinweise"]))


if __name__ == "__main__":
    unittest.main()


def _quadrat(x0, y0, x1, y1):
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


class Raumabgleich(unittest.TestCase):
    """Zwei Ortsteile A (links) und B (rechts); Bezirke 1 und 2 in A, Bezirk 3 über beiden mit je 4 Einwohnern."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        ot = {"features": [
            {"properties": {"ortsteil_bez": "A-Dorf", "bezirk_bez": "Bonn"}, "geometry": _quadrat(0, 0, 2, 2)},
            {"properties": {"ortsteil_bez": "Bü", "bezirk_bez": "Beuel"}, "geometry": _quadrat(2, 0, 4, 2)}]}
        bz = {"features": [
            {"properties": {"raum_id": "1", "name": "Eins"}, "geometry": _quadrat(0, 0, 1, 2)},
            {"properties": {"raum_id": "2", "name": "Zwei"}, "geometry": _quadrat(1, 0, 2, 1)},
            {"properties": {"raum_id": "3", "name": "Drei"}, "geometry": _quadrat(1, 1, 4, 2)}]}
        zensus = Path(self._tmp.name) / "z.tsv"
        zellen = [(0.5, 1, 100), (1.5, 0.5, 100), (1.5, 1.5, 4), (3, 1.5, 4)]
        zensus.write_text("gitter_id\tlon\tlat\teinwohner\n" + "".join(f"x\t{x}\t{y}\t{e}\n" for x, y, e in zellen))
        self.zu, self.audit, self.sauber, self.namen = sd.raumabgleich(bz, ot, zensus)

    def tearDown(self):
        self._tmp.cleanup()

    def test_sauber_nur_mit_ganzen_bezirken(self):
        # A: 200 von 204 Einwohnern in Bezirken, die ganz in A liegen (98 %); B: Bezirk 3 geteilt
        self.assertEqual(self.sauber, {"a-dorf": ["1", "2"]})
        self.assertEqual(self.namen["bue"], "Bü")

    def test_geteilter_bezirk_gemeldet_nicht_zugeordnet(self):
        drei = {r["ziel"]: r for r in self.audit if r["einheit"] == "3"}
        self.assertEqual({r["pruefstatus"] for r in drei.values()}, {"geteilt, nicht zugeordnet"})
        self.assertEqual(drei["Bü"]["einwohneranteil"], "0.5000")
        eins = [r for r in self.zu if r["von_id"] == "1"]
        self.assertEqual((eins[0]["nach_id"], eins[0]["konfidenz"], eins[0]["einwohneranteil"]), ("a-dorf", "hoch", "1.0000"))

    def test_ortsteilwerte(self):
        ind = [{"indikator_id": "bonn-sda-i0", "typ": "anzahl"}, {"indikator_id": "bonn-sda-i22", "typ": "anzahl"},
               {"indikator_id": "bonn-sda-i23", "typ": "anteil"}, {"indikator_id": "bonn-sda-i9", "typ": "mittelwert"}]
        w = lambda iid, rid, wert, status="ok": {"raumebene": "statistischer_bezirk", "raum_id": rid,
                                                  "indikator_id": iid, "jahr": "2025", "wert": wert, "status": status}
        werte = [w("bonn-sda-i0", "1", "100"), w("bonn-sda-i0", "2", "300"), w("bonn-sda-i22", "1", "10"),
                 w("bonn-sda-i22", "2", "50"), w("bonn-sda-i23", "1", "10"), w("bonn-sda-i23", "2", "16.7"),
                 w("bonn-sda-i9", "1", "40"), w("bonn-sda-i9", "2", "44"), w("bonn-sda-i9", "3", "38")]
        out = {(r["raum_id"], r["indikator_id"]): r for r in sd.ortsteilwerte(werte, ind, {"a": ["1", "2"], "b": ["3"]})}
        self.assertEqual((out[("a", "bonn-sda-i0")]["wert"], out[("a", "bonn-sda-i0")]["status"]), ("400", "abgeleitet"))
        self.assertEqual(out[("a", "bonn-sda-i23")]["wert"], "15")        # 60 / 400 × 100, nicht Mittel der Anteile
        self.assertNotIn(("a", "bonn-sda-i9"), out)                       # Mittelwert ohne Zähler und Nenner
        self.assertEqual(out[("b", "bonn-sda-i9")]["wert"], "38")         # ein Bezirk: Wert übernommen
        self.assertIn("statistischer_bezirk 1+2 → ortsteil a", out[("a", "bonn-sda-i0")]["quellobjekt"])

    def test_vergleich_alter_und_neuer_geometrie(self):
        bz = lambda drei, zwei: {"features": [
            {"properties": {"raum_id": "1", "name": "Eins"}, "geometry": _quadrat(0, 0, 1, 2)},
            {"properties": {"raum_id": "2", "name": "Zwei"}, "geometry": zwei},
            {"properties": {"raum_id": "3", "name": "Drei"}, "geometry": drei}]}
        alt = bz(_quadrat(1, 1, 4, 2), _quadrat(1, 0, 2, 1))
        neu = bz(_quadrat(2, 1, 4, 2), _quadrat(1, 0, 2, 2))   # Bezirk 3 nur noch in B
        ind = [{"indikator_id": "bonn-sda-i0", "typ": "anzahl"}]
        werte = [{"raumebene": "statistischer_bezirk", "raum_id": r, "indikator_id": "bonn-sda-i0", "jahr": "2025",
                  "wert": v, "status": "ok"} for r, v in (("1", "100"), ("2", "104"), ("3", "4"))]
        ot = {"features": [
            {"properties": {"ortsteil_bez": "A-Dorf", "bezirk_bez": "Bonn"}, "geometry": _quadrat(0, 0, 2, 2)},
            {"properties": {"ortsteil_bez": "Bü", "bezirk_bez": "Beuel"}, "geometry": _quadrat(2, 0, 4, 2)}]}
        zeilen, summe = sd.geometrie_vergleich(alt, neu, werte, ind, ot, Path(self._tmp.name) / "z.tsv")
        z = {(r["raum_id"], r["merkmal"]): r for r in zeilen}
        self.assertEqual((z[("1", "ueberdeckung")]["neu"], z[("1", "ueberdeckung")]["befund"]), ("1.000", "gleich"))
        self.assertEqual((z[("3", "ueberdeckung")]["neu"], z[("3", "ueberdeckung")]["befund"]), ("0.667", "abweichend"))
        self.assertEqual((z[("3", "ortsteil")]["alt"], z[("3", "ortsteil")]["neu"]), ("geteilt oder ohne Einwohner", "bue"))
        self.assertEqual((z[("bue", "bezirke")]["alt"], z[("bue", "bezirke")]["neu"]), ("nicht sauber", "3"))
        self.assertEqual(z[("a-dorf", "werte_geaendert")]["neu"], "0")
        self.assertEqual(summe, {"saubere_ortsteile": {"alt": 1, "neu": 2}, "bezirke_ueberdeckung_unter_95": 2,
                                 "bezirke_anderer_ortsteil": 1, "werte_je_ortsteil_geaendert": 1})

    def test_summe_mit_geheimem_teil_fehlt(self):
        ind = [{"indikator_id": "bonn-sda-i36", "typ": "anzahl"}]
        werte = [{"raumebene": "statistischer_bezirk", "raum_id": r, "indikator_id": "bonn-sda-i36", "jahr": "2013",
                  "wert": v, "status": s} for r, v, s in (("1", "", "geheim"), ("2", "7", "ok"))]
        r = sd.ortsteilwerte(werte, ind, {"a": ["1", "2"]})[0]
        self.assertEqual((r["wert"], r["status"]), ("", "fehlt"))


class Seite(unittest.TestCase):
    def test_kompakte_datei_aus_den_dateien_im_repository(self):
        if not (sd.OUT / "meta.json").exists():
            self.skipTest("data/strukturdaten/ fehlt")
        with tempfile.TemporaryDirectory() as tmp:
            sd.seite(sd.OUT, Path(tmp))
            d = json.loads((Path(tmp) / sd.SEITE).read_text(encoding="utf-8"))
        self.assertEqual(d["meta"]["farbe"], list(sd.FARBE))
        self.assertEqual(set(d["ind"]), set(sd.STECKBRIEF))
        self.assertEqual(len(d["bezirke"]), 65)
        self.assertEqual(len(d["geo"]["features"]), 65)
        i23 = d["werte"]["i23"]
        self.assertEqual(len(i23["g"]), len(d["ind"]["i23"]["jahre"]))
        self.assertIn("endenich", i23["o"])                      # sauber zusammengesetzt, aus Zähler und Nenner
        self.assertTrue(d["ortsteile"]["Endenich"]["sauber"])
        self.assertFalse(d["ortsteile"]["Beuel-Mitte"]["sauber"])
        self.assertEqual({w["friendly_url"] for w in d["wegweiser"]}, set(sd.WW_INDIKATOREN))
        # Relative Kennzahlen für die Farbe, keine Anzahlen
        self.assertTrue(all(d["ind"][k]["typ"] != "anzahl" for k in sd.FARBE))
