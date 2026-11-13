"""Hauptleiste (Entscheidung 13.11.2026): das Menü „Themen“ nennt genau die veröffentlichten Themenseiten."""
import re
import unittest
from pathlib import Path

from pipeline.themenseiten import ALLE

INDEX = Path(__file__).resolve().parent.parent / "site" / "index.html"


class Navigation(unittest.TestCase):
    def setUp(self):
        html = INDEX.read_text(encoding="utf-8")
        m = re.search(r'<section class="mega glass" id="mega-themen".*?</section>', html, re.S)
        self.assertIsNotNone(m)
        self.menu = m.group(0)
        self.html = html

    def test_themenseiten_vollstaendig_und_in_reihenfolge(self):
        links = re.findall(r'<li><a href="(thema/[^"]+)">.*?</svg>([^<]+)</a></li>', self.menu)
        self.assertEqual(links, [(t.pfad, t.titel) for t in ALLE])

    def test_vier_menues(self):
        self.assertEqual(re.findall(r'class="menu-btn" data-mega="([^"]+)"', self.html),
                         ["mega-themen", "mega-entscheiden", "mega-mitmachen", "mega-ueber"])
        for alt in ("mega-auswertung", "mega-daten", "mega-verstehen", 'data-panel="panel-detail"', 'data-panel="panel-prozesse"'):
            self.assertNotIn(alt, self.html)


if __name__ == "__main__":
    unittest.main()
