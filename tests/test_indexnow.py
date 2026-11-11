"""IndexNow (pipeline/indexnow.py): Zuordnung von Dateien zu Adressen, Auswahl über die Sitemaps, Pakete, Schlüssel."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from pipeline import config, indexnow as ix

URL = "https://bonn.ratsatlas.de/"


def sitemap(*locs):
    return "<urlset>" + "".join(f"<url><loc>{u}</loc></url>" for u in locs) + "</urlset>"


class Adressen(unittest.TestCase):
    def test_adresse(self):
        self.assertEqual(ix.adresse("index.html", URL), URL)
        self.assertEqual(ix.adresse("vorgang/230577/index.html", URL), URL + "vorgang/230577/")
        self.assertEqual(ix.adresse("datenschutz.html", URL), URL + "datenschutz.html")

    def test_auswahl_nur_aus_den_sitemaps(self):
        neu = ix.sitemap_adressen([sitemap(URL, URL + "thema/", URL + "vorgang/1/")])
        alt = ix.sitemap_adressen([sitemap(URL, URL + "vorgang/2/")])
        aenderungen = [("M", "index.html"), ("A", "vorgang/1/index.html"), ("D", "vorgang/2/index.html"),
                       ("D", "vorgang/3/index.html"),          # stand nicht in der alten Sitemap
                       ("M", "404.html"), ("M", "thema/kultur-und-haushalt/index.html"),   # Fehler- und Umleitungsseite
                       ("M", "data/export/bonn/index.json"), ("M", "sitemap-seiten.xml")]
        self.assertEqual(ix.auswahl(aenderungen, neu, alt, URL), [URL, URL + "vorgang/1/", URL + "vorgang/2/"])

    def test_pakete(self):
        urls = [f"{URL}vorgang/{i}/" for i in range(25_001)]
        self.assertEqual([len(p) for p in ix.pakete(urls)], [10_000, 10_000, 5_001])
        self.assertEqual(ix.pakete([]), [])

    def test_schluesseldatei(self):
        datei = config.ROOT / "site" / f"{ix.SCHLUESSEL}.txt"
        self.assertRegex(ix.SCHLUESSEL, r"^[0-9a-f]{32}$")
        self.assertEqual(datei.read_text(encoding="utf-8").strip(), ix.SCHLUESSEL)


class AusGit(unittest.TestCase):
    """Unterschied zweier Stände eines kleinen Branch deploy, ohne Netz (trocken)."""

    def test_aenderungen_und_alte_sitemaps(self):
        with tempfile.TemporaryDirectory() as d:
            o = Path(d)
            git = lambda *a: subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)  # noqa: E731
            git("init", "-q")
            git("config", "user.email", "test@example.org")
            git("config", "user.name", "Test")
            (o / "vorgang/2").mkdir(parents=True)
            (o / "vorgang/2/index.html").write_text("alt")
            (o / "index.html").write_text("eins")
            (o / "sitemap-seiten.xml").write_text(sitemap(URL))
            (o / "sitemap-vorgaenge.xml").write_text(sitemap(URL + "vorgang/2/"))
            git("add", "-A")
            git("commit", "-qm", "a")
            (o / "vorgang/2/index.html").unlink()
            (o / "vorgang/1").mkdir()
            (o / "vorgang/1/index.html").write_text("neu")
            (o / "sitemap-vorgaenge.xml").write_text(sitemap(URL + "vorgang/1/"))
            git("add", "-A")
            git("commit", "-qm", "b")
            neu = ix.sitemap_adressen((o / s).read_text() for s in ix.SITEMAPS)
            alt = ix.sitemap_adressen(ix._alte_sitemaps(o))
            self.assertEqual(ix.auswahl(ix._aenderungen(o), neu, alt, URL), [URL + "vorgang/1/", URL + "vorgang/2/"])


if __name__ == "__main__":
    unittest.main()
