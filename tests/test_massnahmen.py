import csv
import json
import unittest
from collections import defaultdict

from pipeline import haushaltsplan as hp, massnahmen as mn

MITTE = {k: 200 + 45 * k for k in range(1, 13)}   # Mitte der Spaltennummer k


def kopf():
    ws = [(x - 3, 200, x + 3, 208, str(k)) for k, x in MITTE.items()]
    ws += [(MITTE[k] - 8, 180, MITTE[k] + 8, 188, str(j)) for k, j in zip((1, 2, 3, 4, 6, 8, 9, 10), range(2022, 2030))]
    ws.append((60, 150, 160, 158, "Investitionseinzelmaßnahmen"))
    return ws


def betrag(y, k, text, versatz=0):
    rechts = MITTE[k] + 20.5 + versatz
    return (rechts - 5 * len(text), y, rechts, y + 8, text)


def name(y, text):
    return [(30 + 40 * i, y, 30 + 40 * i + 35, y + 8, t) for i, t in enumerate(text.split())]


def zeile(y, nr, zeichen, werte, versatz=0):
    ws = [(30, y, 35, y + 8, str(nr))]
    if zeichen:
        ws.append((50, y, 54, y + 8, zeichen))
    return ws + [betrag(y, k, t, versatz) for k, t in werte.items()]


class Seite(unittest.TestCase):
    def test_bloecke_spalten_und_saldo(self):
        ws = kopf() + name(240, "Sportplatz Endenich BN") + zeile(260, 7, "-", {4: "250.000", 6: "1.000", 12: "251.000"}) \
            + zeile(280, 12, "=", {4: "-250.000", 6: "-1.000", 12: "-251.000"}) \
            + name(300, "Kläranlage Beuel") + zeile(320, 1, "", {6: "50.000", 12: "50.000"}, versatz=3) \
            + zeile(340, 8, "-", {6: "230.000", 12: "230.000"}, versatz=3) \
            + zeile(360, 12, "=", {6: "-180.000", 12: "-180.000"}, versatz=3)
        b = mn.seite_lesen(ws, "PB99.pdf", 1)
        self.assertEqual([x["bezeichnung"] for x in b], ["Sportplatz Endenich BN", "Kläranlage Beuel"])
        self.assertEqual(b[0]["zeilen"][7], {4: 250000, 6: 1000, 12: 251000})
        self.assertEqual(b[1]["zeilen"][12], {6: -180000, 12: -180000})

    def test_gesperrte_ziffern(self):
        ws = kopf() + name(240, "Wege BN") + zeile(260, 7, "-", {12: "1.000"}) + [
            (MITTE[6] + 20.5 - 18, 260, MITTE[6] + 20.5 - 10, 268, "1.0"),
            (MITTE[6] + 20.5 - 9, 260, MITTE[6] + 20.5, 268, "00")]
        self.assertEqual(mn.seite_lesen(ws, "PB99.pdf", 1)[0]["zeilen"][7], {6: 1000, 12: 1000})

    def test_ohne_spalte_12_bricht_ab(self):
        ws = kopf() + name(240, "Wege BN") + zeile(260, 7, "-", {6: "1.000"})
        with self.assertRaisesRegex(ValueError, "Verschiebung"):
            mn.seite_lesen(ws, "PB99.pdf", 1)

    def test_bezeichnung_ohne_zeilen_bricht_ab(self):
        ws = kopf() + name(240, "Effertzstr. BN") + name(250, "Endenicher Allee BN") + zeile(270, 7, "-", {11: "5", 12: "5"})
        with self.assertRaisesRegex(ValueError, "ohne Zeilen"):
            mn.seite_lesen(ws, "PB99.pdf", 1)

    def test_block_ohne_bezeichnung_bricht_ab(self):
        ws = kopf() + name(240, "Markt BN") + zeile(260, 7, "-", {11: "5", 12: "5"}) \
            + zeile(280, 12, "=", {11: "-5", 12: "-5"}) + zeile(300, 7, "-", {4: "9", 12: "9"})
        with self.assertRaisesRegex(ValueError, "ohne Bezeichnung"):
            mn.seite_lesen(ws, "PB99.pdf", 1)

    def test_jahre_im_kopf_muessen_passen(self):
        ws = [w for w in kopf() if w[4] != "2029"] + name(240, "Wege BN") + zeile(260, 7, "-", {4: "1", 12: "1"})
        with self.assertRaisesRegex(ValueError, "Jahre im Kopf"):
            mn.seite_lesen(ws, "PB99.pdf", 1)


def massnahme(bez, zeilen, pg="1.99.01"):
    return {"produktbereich": "99", "produktgruppe": pg, "pg_name": "Test", "datei": "PB99.pdf", "seite": 1,
            "position": 1, "bezeichnung": bez, "zeilen": zeilen, "vermerk": "", "spalten_unsicher": False}


class Pruefen(unittest.TestCase):
    def test_summen(self):
        m = [massnahme("A", {7: {4: 100, 6: 50, 12: 150}, 12: {4: -100, 6: -50, 12: -150}})]
        a = {("1.99.01", 8, 4): 100, ("1.99.01", 8, 6): 50}
        self.assertEqual(mn.pruefen(m, a)["produktgruppen_teil_a"][1], 0)

    def test_spalte_12_bricht_ab(self):
        m = [massnahme("A", {7: {4: 100, 12: 90}, 12: {4: -100, 12: -90}})]
        with self.assertRaisesRegex(ValueError, "Spalte 12"):
            mn.pruefen(m, {("1.99.01", 8, 4): 100})

    def test_teil_a_bricht_ab(self):
        m = [massnahme("A", {7: {4: 100, 12: 100}, 12: {4: -100, 12: -100}})]
        with self.assertRaisesRegex(ValueError, "Teil A"):
            mn.pruefen(m, {("1.99.01", 8, 4): 120})

    def test_nur_mit_ansatz_und_ohne_einzelpersonen(self):
        m = [massnahme("A", {7: {4: 100, 12: 100}}), massnahme("B", {7: {11: 5, 12: 5}}),
             massnahme("Leibrenten", {6: {6: 7, 12: 7}})]
        rows, weg = mn.zeilen_tsv(m)
        self.assertEqual({r["bezeichnung"] for r in rows}, {"A"})
        self.assertEqual(weg, 1)
        self.assertEqual({r["spalte"] for r in rows}, {4, 6, 12})


class Dateien(unittest.TestCase):
    def setUp(self):
        with open(mn.TSV, encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f, delimiter="\t"))

    def test_freigegeben(self):
        self.assertTrue(mn.FREIGEGEBEN)   # Prüfbogen im Gespräch freigegeben am 10.11.2026

    def test_regeln(self):
        self.assertTrue(all(r["spalte"] in ("4", "6", "12") and r["ausgabe"] == mn.AUSGABE for r in self.rows))
        self.assertFalse(any(mn.NUR_SUMME.search(r["bezeichnung"]) for r in self.rows))
        ansatz = defaultdict(int)
        for r in self.rows:
            if r["spalte"] in ("4", "6"):
                ansatz[(r["produktgruppe"], r["seite"], r["position"])] += abs(int(r["betrag"]))
        self.assertTrue(ansatz and all(ansatz.values()))
        self.assertEqual(len(ansatz), json.loads(hp.STAND.read_text(encoding="utf-8"))["massnahmen"]["uebernommen"])

    def test_ansatz_gleich_teil_a(self):
        """Maßnahmen ohne Ansatz fehlen in der Datei; die Ansätze je Produktgruppe treffen daher Teil A genau."""
        summe = defaultdict(int)
        for r in self.rows:
            if r["spalte"] in ("4", "6") and int(r["zeile"]) in mn.B_ZU_A:
                summe[(r["produktgruppe"], mn.B_ZU_A[int(r["zeile"])], int(r["spalte"]))] += int(r["betrag"])
        a = {k: v for k, v in mn._teil_a().items() if k[2] in (4, 6) and k[1] in mn.B_ZU_A.values()}
        for k in set(summe) | set(a):
            self.assertLessEqual(abs(summe.get(k, 0) - a.get(k, 0)), mn.TOLERANZ, k)


if __name__ == "__main__":
    unittest.main()
