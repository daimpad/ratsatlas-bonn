import tempfile
import unittest
import zipfile
from pathlib import Path

from pipeline import verify


class Datenpaket(unittest.TestCase):
    def test_inhalt_mit_plaenen_baustellen_und_berichten(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "archiv"
            archive.mkdir()
            (archive / "protokoll.tsv").write_text("datum\tbaustelle_id\tereignis\n", encoding="utf-8")
            (archive / "STAND.json").write_text("{}", encoding="utf-8")
            target = Path(tmp) / "paket.zip"
            verify.package(target, archive)
            names = set(zipfile.ZipFile(target).namelist())
        for name in ("LIESMICH.txt", "LICENSE-DATA.md", "geo/bebauungsplaene_bonn.geojson", "audit_bebauungsplaene.tsv",
                     "baustellen_kandidaten.tsv", "baustellen/stichprobe_kandidaten.tsv", "baustellen/vorpruefung_kandidaten.tsv",
                     "baustellen_archiv/protokoll.tsv", "baustellen_archiv/STAND.json", "berichte/PHASE0.md", "berichte/PHASE3.md",
                     "soll/verfahren.json", "soll/ergaenzungen.json", "soll/QUELLE.md", "soll/LICENSE-bonn-entscheidet",
                     "soll/stichprobe_soll.tsv", "soll/vorpruefung_soll.tsv", "berichte/soll/PHASE3.md",
                     "soll/pruefung/belege_ergaenzungen.tsv", "strukturdaten/indikatoren.tsv", "strukturdaten/werte.tsv",
                     "strukturdaten/raum/statistischer_bezirk.geojson", "strukturdaten/audit_verifikation.tsv",
                     "berichte/strukturdaten/PHASE0.md", "berichte/strukturdaten/PHASE4.md"):
            self.assertIn("allris-bonn/" + name, names)
        self.assertFalse(any("/feeds/" in n or "/chat/" in n for n in names))
        self.assertFalse(any(n.endswith(".zip") for n in names))

    def test_lizenzen_je_datei_genannt(self):
        text = (Path(__file__).resolve().parent.parent / "data" / "LICENSE-DATA.md").read_text(encoding="utf-8")
        for name in ("bebauungsplaene_bonn.geojson", "bebauungsplaene_protokoll.tsv", "plaene.json", "audit_bebauungsplaene.tsv",
                     "baustellen.json", "baustellen_kandidaten.tsv", "export/baustellen/", "baustellen_archiv/",
                     "soll/verfahren.json", "audit_soll.tsv", "export/soll/"):
            self.assertIn(name, text)

    def test_liesmich_nennt_grenzen(self):
        self.assertIn("kein Beleg für die Umsetzung", verify.PACKAGE_README)
        self.assertIn("baustellen_kandidaten.tsv", verify.PACKAGE_README)


if __name__ == "__main__":
    unittest.main()
