import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import config, kurzfassung

TEXT = ("Die Verwaltung schlägt vor, den Spielplatz an der Endenicher Straße neu zu gestalten. "
        "Dazu sollen neue Geräte aufgestellt und die Wege erneuert werden. Die Kosten trägt der städtische Haushalt.")


class KurzfassungTest(unittest.TestCase):
    def setUp(self):
        # Regelbetrieb: der Stand des Modells ist freigegeben (die Stichprobenphase prüft ModellstandTest)
        p = mock.patch.object(kurzfassung, "MODELLSTAND_FREIGEGEBEN", (1, kurzfassung.MODELLSTAND))
        p.start()
        self.addCleanup(p.stop)

    def test_wortliche_uebernahme_wird_erkannt(self):
        self.assertIsNotNone(kurzfassung.uebernahme("Dazu sollen neue Geräte aufgestellt und die Wege erneuert werden.", TEXT))
        self.assertIsNone(kurzfassung.uebernahme("Der Spielplatz bekommt neue Geräte und bessere Wege.", TEXT))

    def test_fraktion_und_gremium_nur_mit_beleg(self):
        text = "Die Verwaltung wird gebeten, den Spielplatz an der Endenicher Straße zu erneuern."
        kurz = "Die Grünen möchten einen neuen Spielplatz in Endenich. Darüber entscheidet bald der Rat."
        self.assertEqual(kurzfassung.fremder_akteur(kurz, text), "Grüne")
        self.assertEqual(kurzfassung.fremder_akteur(kurz, "Antrag der Fraktion BÜNDNIS 90/DIE GRÜNEN " + text), "Rat")
        self.assertIsNone(kurzfassung.fremder_akteur(kurz, "Antrag von Bündnis 90/Die Grünen an den Rat " + text))
        self.assertIsNone(kurzfassung.fremder_akteur("Der Beirat empfiehlt den Spielplatz.", text))
        self.assertEqual(kurzfassung.pruefe(kurz, text, "Antrag der Grünen"), "nicht in Titel oder Text: Rat")

    def test_lange_uebernahme_um_einen_gremiennamen(self):
        # Code-Prüfung 24.10.2026: sechs Wörter davor und danach blieben unbemerkt, weil jedes Fenster den Namen berührte
        text = ("Die Verwaltung wird gebeten, dem Ausschuss für Planung, Verkehr und Denkmalschutz bis Ende des Jahres "
                "zu berichten. Weitere Sätze folgen hier.")
        gremium = ["Ausschuss für Planung, Verkehr und Denkmalschutz"]
        kurz = "Die Verwaltung wird gebeten, dem Ausschuss für Planung, Verkehr und Denkmalschutz bis Ende des Jahres zu berichten."
        self.assertIsNotNone(kurzfassung.uebernahme(kurz, text, erlaubt=gremium))
        kurz = "Bis Ende des Jahres soll die Verwaltung dem Ausschuss für Planung, Verkehr und Denkmalschutz berichten."
        self.assertIsNone(kurzfassung.uebernahme(kurz, text, erlaubt=gremium))

    def test_titel_und_gremien_sind_keine_uebernahme(self):
        text = "Der Ausschuss für Planung, Verkehr und Denkmalschutz berät die Sanierung der Brücke an der Kölnstraße."
        kurz = "Der Ausschuss für Planung, Verkehr und Denkmalschutz soll über eine neue Brücke beraten."
        self.assertIsNotNone(kurzfassung.uebernahme(kurz, text))
        self.assertIsNone(kurzfassung.uebernahme(kurz, text, erlaubt=["Ausschuss für Planung, Verkehr und Denkmalschutz"]))
        titel = "Sanierung der Brücke an der Kölnstraße in der Nordstadt"
        kurz = "Die Verwaltung plant die Sanierung der Brücke an der Kölnstraße in der Nordstadt bis 2027."
        self.assertIsNone(kurzfassung.uebernahme(kurz, text + " " + titel, erlaubt=[titel]))

    def test_zahl_aus_dem_titel(self):
        text = "Der Bericht für alle vier Quartale liegt bei. Die Auslastung ist gestiegen."
        kurz = "Die Stabsstelle legt den Controllingbericht für das Jahr 2023 mit allen vier Quartalen vor."
        self.assertEqual(kurzfassung.pruefe(kurz, text), "Zahl nicht im Text: 2023")
        self.assertIsNone(kurzfassung.pruefe(kurz, text, "Controllingbericht 2023 der Beethovenhalle"))

    def test_entwurf_wird_nicht_aufbewahrt(self):
        # Prüfung November 2026, Nr. 25: verworfene Entwürfe standen im öffentlichen Branch kurzfassungen
        self.assertEqual(kurzfassung._ergebnis("Gut.", None), {"kurzfassung": "Gut.", "verworfen": None, "entwurf": None})
        self.assertEqual(kurzfassung._ergebnis("Mit 99 Bäumen.", "Zahl nicht im Text: 99"),
                         {"kurzfassung": None, "verworfen": "Zahl nicht im Text: 99", "entwurf": None})

    def test_hausnummer_als_wort_und_flurstueck(self):
        # Prüfung November 2026, Nr. 1: „zwischen den Hausnummern 51 und 61“ blieb unerkannt (57 Kurzfassungen)
        for t in ["Der Gehweg an der Meckenheimer Straße zwischen den Hausnummern 51 und 61 soll breiter werden.",
                  "Vor Haus-Nr. 12 soll ein Baum gefällt werden.", "Die Markierung vor den Häusern Nr. 73 - 89 entfällt.",
                  "Es geht um das Grundstück Gemarkung Beuel, Flur 3, Flurstück 1234."]:
            self.assertTrue(kurzfassung.hausnummer(t), t)
            self.assertEqual(kurzfassung.pruefe(t, TEXT), "Hausnummer genannt")
        self.assertFalse(kurzfassung.hausnummer("Die Verwaltung nennt keine Hausnummern und keine Häuser."))

    def test_pruefe(self):
        gut = "Der Spielplatz in Endenich soll neue Geräte und bessere Wege bekommen. Bezahlt wird das aus dem Haushalt der Stadt."
        self.assertIsNone(kurzfassung.pruefe(gut, TEXT))
        self.assertEqual(kurzfassung.pruefe("Zu kurz.", TEXT), "zu kurz")
        self.assertEqual(kurzfassung.pruefe("Ein Anwohner der Endenicher Straße 12 möchte einen neuen Spielplatz.", TEXT),
                         "Hausnummer genannt")
        self.assertTrue(kurzfassung.pruefe("Die Verwaltung schlägt vor, den Spielplatz an der Endenicher Straße neu zu gestalten.", TEXT)
                        .startswith("wörtliche Übernahme"))

    def test_hausnummern_in_allen_schreibweisen(self):
        # Code-Prüfung 23.10.2026: Buchstabenzusätze, „Str“ ohne Punkt und Straßen ohne Endung fehlten
        for t in ["an der Hauptstraße 12a", "Endenicher Allee 11a", "Bornheimer Str 5", "Am Burggraben 3",
                  "am Markt 2", "Kölnstraße Nr. 7"]:
            self.assertTrue(kurzfassung.hausnummer(t), t)
        for t in ["2 neue Bänke am Markt", "Bonner Wochenmarkt 25 % weniger", "am Holzlarer Weg, 500 Euro",
                  "Wohnungsmarkt 2025", "Kölnstraße 30 Prozent"]:
            self.assertFalse(kurzfassung.hausnummer(t), t)
        # auch ein zu kurzer Entwurf wird mit Hausnummer nicht aufbewahrt
        self.assertEqual(kurzfassung.pruefe("Bänke an der Hauptstraße 12a.", TEXT), "Hausnummer genannt")

    def test_markdown_wird_entfernt(self):
        self.assertEqual(kurzfassung.glaetten("Baum in der Straße *Am Herrengarten*, **gefällt**."),
                         "Baum in der Straße Am Herrengarten, gefällt.")
        self.assertEqual(kurzfassung.glaetten("3 * 4 Bäume"), "3 * 4 Bäume")

    def test_kostensatz_und_fremde_zahlen(self):
        text = "Die Verwaltung gewährt einen Zuschuss von 20.000 EUR für 2023 und 1.661.000 EUR für 2024."
        kurz = "Die Verwaltung schlägt einen Zuschuss von 20.000 Euro vor. Die Kosten trägt die Stadt."
        self.assertEqual(kurzfassung.ohne_kostensatz(kurz, text), "Die Verwaltung schlägt einen Zuschuss von 20.000 Euro vor.")
        self.assertEqual(kurzfassung.ohne_kostensatz(kurz, text + " Die Kosten trägt der Antragsteller."), kurz)
        self.assertIsNone(kurzfassung.fremde_zahl("Zuschuss von 1.661.000 Euro für 2024, Teil 2.", text))
        self.assertEqual(kurzfassung.fremde_zahl("insgesamt rund 4,1 Millionen Euro", text), "4,1")
        self.assertIsNone(kurzfassung.fremde_zahl("Der Vertrag endet 2024.", "Er läuft zum 31.12.2024 aus."))

    def test_ueberschrift_wird_entfernt(self):
        for kopf in ("Stellungnahme der Verwaltung", "Stadt Bonn – Mitteilung", "Beschlussvorlage der Verwaltung:",
                     "Absender: Mehrere Fraktionen (interfraktioneller Antrag)\nArt der Vorlage: Vorschlag"):
            self.assertEqual(kurzfassung.glaetten(f"{kopf}\n\nDie Verwaltung schlägt vor, den Baum zu fällen. Ersatz folgt."),
                             "Die Verwaltung schlägt vor, den Baum zu fällen. Ersatz folgt.")
        self.assertEqual(kurzfassung.glaetten("Kurz und ohne Punkt"), "Kurz und ohne Punkt")   # nur eine Zeile: bleibt

    def test_ohne_schluessel_nichts(self):
        with mock.patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory() as d:
            kurzfassung.erzeugen(d, anfrage=lambda *a: self.fail("keine Anfrage ohne Schlüssel"))
            self.assertFalse((Path(d) / "kurzfassungen.jsonl").exists())

    def test_gegenlesen_berichtigt_und_faellt_zurueck(self):
        with tempfile.TemporaryDirectory() as d:
            texte, papers = Path(d) / "texte.jsonl", Path(d) / "papers.jsonl"
            texte.write_text("\n".join(json.dumps({"uri": f"f{i}", "sha": f"s{i}", "text": TEXT}) for i in range(2)))
            papers.write_text("\n".join(json.dumps({"reference": f"26000{i}", "name": "Spielplatz", "paperType": "Antrag",
                                                    "mainFile": {"id": f"f{i}"}}) for i in range(2)))
            erste = "Der Rat hat beschlossen, den Spielplatz in Endenich mit neuen Geräten auszustatten."
            neu = iter(["Die Verwaltung schlägt vor, den Spielplatz in Endenich mit neuen Geräten auszustatten.", "OK"])
            anfrage = lambda titel, text, key: (erste, {})
            gegenlesen = lambda titel, text, kurz, key: (next(neu), {})
            with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "test"}), \
                    mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers):
                kurzfassung.erzeugen(Path(d) / "kurz", anfrage=anfrage, gegenlesen=gegenlesen)
            rows = sorted(kurzfassung.laden(Path(d) / "kurz").values(), key=lambda r: r["drucksache"])
            self.assertTrue(rows[0]["kurzfassung"].startswith("Die Verwaltung schlägt vor"))
            self.assertTrue(rows[0]["beim_gegenlesen_geaendert"])
            self.assertIsNone(rows[1]["kurzfassung"])   # „OK“ ist zu kurz: erste Fassung bleibt und wird geprüft
            self.assertEqual(rows[1]["verworfen"], "nicht in Titel oder Text: Rat")
            self.assertFalse(rows[1]["beim_gegenlesen_geaendert"])

    def test_gescheiterte_anfrage_haelt_den_lauf_nicht_an(self):
        # Code-Prüfung 23.10.2026: ein Fehler beendete bisher den ganzen Lauf, ohne Zwischenstand
        with tempfile.TemporaryDirectory() as d:
            texte, papers = Path(d) / "texte.jsonl", Path(d) / "papers.jsonl"
            texte.write_text("\n".join(json.dumps({"uri": f"f{i}", "sha": f"s{i}", "text": TEXT}) for i in range(2)))
            papers.write_text("\n".join(json.dumps({"reference": f"26000{i}", "name": f"Spielplatz Nr{i}",
                                                    "paperType": "Antrag", "mainFile": {"id": f"f{i}"}}) for i in range(2)))
            gut = "Der Spielplatz in Endenich soll neue Geräte und bessere Wege bekommen, bezahlt von der Stadt."
            calls = []
            def anfrage(titel, text, key):
                calls.append(1)
                if "Nr0" in titel:   # diese Anfrage scheitert immer
                    raise TimeoutError("Anbieter antwortet nicht")
                return gut, {}
            out = Path(d) / "kurz"
            with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "test"}), \
                    mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers):
                for _ in range(4):
                    kurzfassung.erzeugen(out, anfrage=anfrage)
            rows = {r["drucksache"]: r for r in kurzfassung.laden(out).values()}
            self.assertEqual(rows["260001"]["kurzfassung"], gut)          # zweiter Eintrag trotz Fehler davor erzeugt
            self.assertEqual(rows["260000"]["fehler"], "Anfrage gescheitert: TimeoutError")
            self.assertEqual(rows["260000"]["versuche"], kurzfassung.MAX_VERSUCHE)   # danach nicht mehr angefragt
            self.assertEqual(len(calls), 1 + kurzfassung.MAX_VERSUCHE)

    def test_antwort_als_liste_von_teilen(self):
        # 21./22.11.2026: Der Anbieter liefert `content` als Liste von Teilen. Gelesen wird nur der Textteil, nie der
        # Denkteil; ohne Textteil gilt die Anfrage als gescheitert, die Meldung nennt Form und Modell, nie den Text.
        from pipeline import sprachmodell
        teile = [{"type": "thinking", "thinking": [{"type": "text", "text": "GEHEIMER GEDANKE"}]},
                 {"type": "text", "text": " Die Antwort. "}]
        antwort = lambda content, ende="stop": {"model": "modell-x", "choices": [{"finish_reason": ende,
                                                                                 "message": {"content": content}}]}
        self.assertEqual(sprachmodell.antworttext(antwort(" Text \n")), "Text")
        self.assertEqual(sprachmodell.antworttext(antwort(teile)), "Die Antwort.")
        with self.assertRaises(sprachmodell.AntwortFormat) as f:
            sprachmodell.antworttext(antwort(teile[:1]))
        self.assertIn("Liste mit Teilen thinking", str(f.exception))
        self.assertIn("modell-x", str(f.exception))
        self.assertNotIn("GEHEIM", str(f.exception))
        for content in (teile[:1], teile, "Ein abgeschnittener Sa"):   # an der Längengrenze: nie ein vollständiger Text
            with self.assertRaises(sprachmodell.AntwortFormat) as f:
                sprachmodell.antworttext(antwort(content, "length"))
            self.assertIn("Längengrenze", str(f.exception))
            self.assertNotIn("GEHEIM", str(f.exception))
        for leer in ({}, {"choices": []}, antwort(None), antwort(""), antwort([])):
            self.assertRaises(sprachmodell.AntwortFormat, sprachmodell.antworttext, leer)

    def test_anfrage_mit_denkaufwand_und_rueckfall(self):
        # Denkschritte zählen zur Längengrenze: höhere Grenze, kleiner Denkaufwand; nimmt der Anbieter die Angabe
        # nicht an (HTTP 400 oder 422), wird ohne sie angefragt und der Lauf merkt sich das
        import io
        import urllib.error
        gesendet = []
        def urlopen(req, timeout=0):
            body = json.loads(req.data)
            gesendet.append(body)
            if "reasoning_effort" in body:
                raise urllib.error.HTTPError(req.full_url, 422, "Unprocessable Entity", {}, io.BytesIO(b""))
            return io.BytesIO(json.dumps({"choices": [{"message": {"content": "Kurz."}}], "usage": {"completion_tokens": 7}}).encode())
        with mock.patch.object(kurzfassung, "_ohne_denkaufwand", False), \
                mock.patch.object(kurzfassung.urllib.request, "urlopen", urlopen), mock.patch("builtins.print"):
            self.assertEqual(kurzfassung._anfrage("Titel", "Text", "k"), ("Kurz.", {"completion_tokens": 7}))
            self.assertEqual(kurzfassung._anfrage("Titel", "Text", "k")[0], "Kurz.")
        self.assertEqual([b.get("reasoning_effort") for b in gesendet], [kurzfassung.DENKAUFWAND, None, None])
        self.assertEqual({b["max_tokens"] for b in gesendet}, {kurzfassung.MAX_TOKENS})

    def test_kontoausfall_beendet_den_lauf_ohne_dokumente_zu_sperren(self):
        # Code-Prüfung 24.10.2026: 401 oder eine Serie von Fehlern zählte als Fehler jedes Dokuments; nach drei Tagen
        # Ausfall wurden die Dokumente nie wieder angefragt
        import urllib.error
        with tempfile.TemporaryDirectory() as d:
            n = kurzfassung.SERIE + 3
            texte, papers = Path(d) / "texte.jsonl", Path(d) / "papers.jsonl"
            texte.write_text("\n".join(json.dumps({"uri": f"f{i}", "sha": f"s{i}", "text": TEXT}) for i in range(n)))
            papers.write_text("\n".join(json.dumps({"reference": f"2600{i:02d}", "name": f"Spielplatz Nr{i}",
                                                    "paperType": "Antrag", "mainFile": {"id": f"f{i}"}}) for i in range(n)))
            gut = "Der Spielplatz in Endenich soll neue Geräte und bessere Wege bekommen, bezahlt von der Stadt."
            calls, fehler = [], [urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)]
            def anfrage(titel, text, key):
                calls.append(1)
                if fehler[0]:
                    raise fehler[0]
                return gut, {}
            out = Path(d) / "kurz"
            with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "test"}), \
                    mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers):
                for _ in range(3):
                    # Prüfung November 2026, Nr. 3: ein Lauf ohne Ergebnis endet mit Fehler, nicht stillschweigend
                    with self.assertRaises(SystemExit) as ende:
                        kurzfassung.erzeugen(out, anfrage=anfrage)
                    self.assertIn("HTTP 401", str(ende.exception))
                self.assertEqual(len(calls), 3)                      # je Lauf eine Anfrage, dann Ende
                self.assertEqual(kurzfassung.laden(out), {})         # kein Dokument als gescheitert vermerkt
                zeilen = (out / "laeufe.tsv").read_text().splitlines()
                self.assertEqual(zeilen[-1].split("\t")[3:], ["1", "0", "0", "1"])   # 1 gesendet, 0 Tokens, 1 Fehler
                fehler[0] = TimeoutError("Netz")                     # Serie gewöhnlicher Fehler
                calls.clear()
                with self.assertRaises(SystemExit):
                    kurzfassung.erzeugen(out, anfrage=anfrage)
                self.assertEqual(len(calls), kurzfassung.SERIE)
                self.assertEqual(kurzfassung.laden(out), {})
                fehler[0] = None                                     # Schlüssel wieder gültig: alle werden angefragt
                kurzfassung.erzeugen(out, anfrage=anfrage)
            self.assertEqual(sum(1 for r in kurzfassung.laden(out).values() if r["kurzfassung"] == gut), n)

    def test_abbruch_nach_ergebnissen_ist_nur_ein_hinweis(self):
        # Kontingent mitten im Lauf erschöpft (429): Bestand bleibt, der Schritt endet ohne Fehler
        import urllib.error
        with tempfile.TemporaryDirectory() as d:
            texte, papers = Path(d) / "texte.jsonl", Path(d) / "papers.jsonl"
            texte.write_text("\n".join(json.dumps({"uri": f"f{i}", "sha": f"s{i}", "text": TEXT}) for i in range(4)))
            papers.write_text("\n".join(json.dumps({"reference": f"26000{i}", "name": f"Spielplatz Nr{i}",
                                                    "paperType": "Antrag", "mainFile": {"id": f"f{i}"}}) for i in range(4)))
            gut = "Der Spielplatz in Endenich soll neue Geräte und bessere Wege bekommen, bezahlt von der Stadt."
            calls = []
            def anfrage(titel, text, key):
                calls.append(1)
                if len(calls) > 2:
                    raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
                return gut, {"prompt_tokens": 10, "completion_tokens": 5}
            out = Path(d) / "kurz"
            with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "test"}), \
                    mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers):
                kurzfassung.erzeugen(out, anfrage=anfrage)
            self.assertEqual(sum(1 for r in kurzfassung.laden(out).values() if r["kurzfassung"] == gut), 2)
            self.assertEqual((out / "laeufe.tsv").read_text().splitlines()[-1].split("\t")[3:], ["3", "20", "10", "1"])

    def test_erzeugen_nur_neue_und_verwirft_auszuege(self):
        with tempfile.TemporaryDirectory() as d:
            texte, papers = Path(d) / "texte.jsonl", Path(d) / "papers.jsonl"
            texte.write_text("\n".join(json.dumps({"uri": f"f{i}", "sha": f"s{i}", "papers": [], "text": TEXT}) for i in range(3)))
            papers.write_text("\n".join(json.dumps({"reference": f"26000{i}", "name": "Spielplatz", "paperType": t,
                                                    "mainFile": {"id": f"f{i}"}})
                                        for i, t in enumerate(["Beschlussvorlage", "Antrag", "Bürgerantrag § 24 GO"])))
            antworten = iter(["Der Spielplatz in Endenich soll neue Geräte und bessere Wege bekommen, bezahlt von der Stadt.",
                              "Dazu sollen neue Geräte aufgestellt und die Wege erneuert werden, sagt der Antrag."])
            calls = []
            def anfrage(titel, text, key):
                calls.append(titel)
                return next(antworten), {"prompt_tokens": 100, "completion_tokens": 30}
            out = Path(d) / "kurz"
            with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "test"}), \
                    mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers):
                kurzfassung.erzeugen(out, anfrage=anfrage)
                kurzfassung.erzeugen(out, anfrage=anfrage)  # zweiter Lauf: nichts Neues
            rows = kurzfassung.laden(out)
            self.assertEqual(len(calls), 2)  # Bürgerantrag ausgenommen, zweiter Lauf ohne Anfragen
            self.assertEqual(sorted(r["verworfen"] or "ok" for r in rows.values()),
                             ["ok", f"wörtliche Übernahme von mehr als {kurzfassung.UEBERNAHME_WOERTER} Wörtern"])
            with mock.patch.object(kurzfassung, "FREIGEGEBEN", False):
                self.assertEqual(kurzfassung.fuer_seite(out), {})  # ohne Freigabe nichts auf der Seite
            with mock.patch.object(kurzfassung, "FREIGEGEBEN", True):
                self.assertEqual(len(kurzfassung.fuer_seite(out)), 1)  # nur die gültige der aktuellen Fassung
            self.assertEqual(len((out / "laeufe.tsv").read_text().splitlines()), 2)  # Kopf und ein Lauf mit Anfragen
            # ältere Fassung wird neu erzeugt
            rows = kurzfassung.laden(out)
            for r in rows.values():
                r.pop("fassung")
            (out / "kurzfassungen.jsonl").write_text("\n".join(json.dumps(r) for r in rows.values()) + "\n")
            antworten = iter(["Die Verwaltung schlägt vor, den Spielplatz mit neuen Geräten und Wegen auszustatten."] * 2)
            with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "test"}), \
                    mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers):
                kurzfassung.erzeugen(out, anfrage=anfrage)
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(r["fassung"] == kurzfassung.FASSUNG for r in kurzfassung.laden(out).values()))



class ModellstandTest(unittest.TestCase):
    """Stichprobenphase (Entscheidung des Auftraggebers 22.11.2026): Kurzfassungen eines noch nicht freigegebenen
    Modellstands entstehen nur für die Stichprobe und erscheinen nicht auf der Seite."""

    def _lauf(self, d, n, anfrage, bestand=(), env=None):
        texte, papers = Path(d) / "texte.jsonl", Path(d) / "papers.jsonl"
        texte.write_text("\n".join(json.dumps({"uri": f"f{i}", "sha": f"s{i}", "text": TEXT}) for i in range(n)))
        papers.write_text("\n".join(json.dumps({"reference": f"26{i:04d}", "name": f"Spielplatz Nr{i}",
                                                "paperType": "Antrag", "mainFile": {"id": f"f{i}"}}) for i in range(n)))
        out = Path(d) / "kurz"
        if bestand:
            out.mkdir(exist_ok=True)
            (out / "kurzfassungen.jsonl").write_text("\n".join(json.dumps(r) for r in bestand) + "\n")
        umgebung = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"} | {"MISTRAL_API_KEY": "test"} | (env or {})
        with mock.patch.dict(os.environ, umgebung, clear=True), mock.patch.object(kurzfassung.time, "sleep"), \
                mock.patch.object(config, "TEXTE", texte), mock.patch.object(config, "PAPERS", papers), \
                mock.patch.object(kurzfassung, "MAX_JE_LAUF", 500), mock.patch("builtins.print") as druck:
            kurzfassung.erzeugen(out, anfrage=anfrage)
        return out, " ".join(str(c.args[0]) for c in druck.call_args_list if c.args)

    GUT = "Der Spielplatz in Endenich soll neue Geräte und bessere Wege bekommen, bezahlt von der Stadt."

    def test_nur_die_stichprobe_entsteht_und_erscheint_nicht(self):
        self.assertNotIn(kurzfassung.MODELLSTAND, kurzfassung.MODELLSTAND_FREIGEGEBEN)   # Freigabe ist eine Entscheidung
        calls = []
        def anfrage(titel, text, key):
            calls.append(titel)
            return self.GUT, {"completion_tokens": 900}
        alt = {"sha": "alt", "datei": "weg", "drucksache": "250001", "kurzfassung": self.GUT, "verworfen": None,
               "entwurf": None, "modell": "mistral-large-latest", "fassung": kurzfassung.FASSUNG, "erzeugt": "2026-11-01"}
        with tempfile.TemporaryDirectory() as d:
            out, _ = self._lauf(d, 100, anfrage, [alt])
            erste = len(calls)
            self.assertEqual(erste, 42)   # 30 für die Stichprobe und ein Zuschlag für Verworfene, nicht alle 100
            rows = kurzfassung.laden(out)
            self.assertEqual({r.get("modellstand") for r in rows.values() if r["sha"] != "alt"}, {kurzfassung.MODELLSTAND})
            self.assertEqual(set(kurzfassung.fuer_seite(out)), {"250001"})   # nur der Bestand des geprüften Modells
            probe = out / f"stichprobe_kurzfassungen_modell{kurzfassung.MODELLSTAND}.tsv"
            self.assertEqual(len(probe.read_text(encoding="utf-8").splitlines()), 31)
            _, text = self._lauf(d, 100, anfrage, list(rows.values()))
            self.assertEqual(len(calls), erste)   # Stichprobe liegt vor: keine weiteren Anfragen
            self.assertIn("keine weiteren Anfragen bis zur Prüfung", text)
            with mock.patch.object(kurzfassung, "MODELLSTAND_FREIGEGEBEN", (1, kurzfassung.MODELLSTAND)):
                self.assertEqual(len(kurzfassung.fuer_seite(out)), 1 + erste)   # nach der Freigabe erscheinen sie

    def test_lauf_ohne_antwort_ist_nur_ein_hinweis(self):
        from pipeline import sprachmodell
        def anfrage(titel, text, key):
            raise sprachmodell.AntwortFormat("Antwort ohne Text (content: Liste mit Teilen thinking)")
        with tempfile.TemporaryDirectory() as d:
            out, text = self._lauf(d, 20, anfrage)   # kein SystemExit
            self.assertIn("::warning::Kurzfassungen: Lauf mit mistral-large-latest ohne Ergebnis beendet", text)
            self.assertIn("ANTHROPIC_API_KEY fehlt", text)   # ohne Schlüssel kein Ausweichweg
            self.assertIn("Liste mit Teilen thinking", text)
            self.assertEqual(kurzfassung.laden(out), {})   # die Serie sperrt kein Dokument
            with mock.patch.object(kurzfassung, "MODELLSTAND_FREIGEGEBEN", (1, kurzfassung.MODELLSTAND)):
                with self.assertRaises(SystemExit) as e:   # im Regelbetrieb fällt derselbe Ausfall als Fehler auf
                    self._lauf(d, 20, anfrage)
            self.assertIn("ohne Text", str(e.exception))

    def test_claude_springt_ein_wenn_mistral_nicht_antwortet(self):
        # Entscheidungen des Auftraggebers 22.11.2026: Claude Sonnet 5.5 nur, wenn ein Lauf mit Mistral keine Antwort
        # liefert; auch dessen Kurzfassungen (Modellstand 3) erscheinen erst nach Prüfung der Stichprobe
        from pipeline import sprachmodell
        def mistral(titel, text, key):
            raise sprachmodell.AntwortFormat("Antwort ohne Text (content: Liste mit Teilen thinking)")
        claude = []
        def anfrage_claude(titel, text, key):
            claude.append(key)
            return self.GUT, {"prompt_tokens": 4000, "completion_tokens": 700}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(kurzfassung, "_anfrage_claude", anfrage_claude):
            out, text = self._lauf(d, 100, mistral, env={"ANTHROPIC_API_KEY": "sk-test"})
            self.assertEqual(len(claude), 42)
            self.assertEqual(set(claude), {"sk-test"})
            rows = list(kurzfassung.laden(out).values())
            self.assertEqual({(r["modell"], r["modellstand"]) for r in rows}, {("claude-sonnet-5-5", 3)})
            self.assertEqual(kurzfassung.fuer_seite(out), {})   # nicht freigegeben: nichts auf der Seite
            self.assertTrue((out / "stichprobe_kurzfassungen_modell3.tsv").exists())
            self.assertFalse((out / "stichprobe_kurzfassungen_modell2.tsv").exists())
            self.assertIn("Ausweichweg mit claude-sonnet-5-5", text)
            self.assertIn("je Antwort im Mittel 700, höchstens 700 Ausgabe-Tokens bei einer Grenze von 16000", text)
            protokoll = (out / "laeufe.tsv").read_text(encoding="utf-8")
            self.assertIn("claude-sonnet-5-5", protokoll)
            # nächster Lauf: Mistral wird wieder versucht, Claude nicht mehr (Stichprobe liegt vor)
            _, text = self._lauf(d, 100, mistral, rows, env={"ANTHROPIC_API_KEY": "sk-test"})
            self.assertEqual(len(claude), 42)
            self.assertIn("Stichprobe zum Modellstand 3 (claude-sonnet-5-5) liegt vor", text)

    def test_claude_bleibt_unbenutzt_wenn_mistral_antwortet(self):
        def anfrage_claude(titel, text, key):
            raise AssertionError("Claude darf nicht angefragt werden")
        with tempfile.TemporaryDirectory() as d, mock.patch.object(kurzfassung, "_anfrage_claude", anfrage_claude):
            out, _ = self._lauf(d, 50, lambda t, x, k: (self.GUT, {"completion_tokens": 900}),
                                env={"ANTHROPIC_API_KEY": "sk-test"})
            self.assertEqual({r["modellstand"] for r in kurzfassung.laden(out).values()}, {2})

    def test_anfrage_an_claude(self):
        # Über das SDK: nur Textteile zählen, Denkschritte nie; abgelehnt, leer oder abgeschnitten gilt als gescheitert;
        # keine Angabe zur Temperatur (wird von den aktuellen Modellen abgelehnt)
        from types import SimpleNamespace as N
        from pipeline import sprachmodell
        antworten, gesendet = [], []
        class Messages:
            def create(self, **kw):
                gesendet.append(kw)
                return antworten.pop(0)
        usage = N(input_tokens=4100, output_tokens=650)
        teile = [N(type="thinking", thinking="GEHEIMER GEDANKE"), N(type="text", text=" Die Kurzfassung. ")]
        antworten += [N(content=teile, stop_reason="end_turn", model="claude-sonnet-5-5", usage=usage),
                      N(content=teile, stop_reason="refusal", model="claude-sonnet-5-5", usage=usage),
                      N(content=teile, stop_reason="max_tokens", model="claude-sonnet-5-5", usage=usage),
                      N(content=teile[:1], stop_reason="end_turn", model="claude-sonnet-5-5", usage=usage)]
        with mock.patch.object(kurzfassung, "_claude", N(messages=Messages())):
            self.assertEqual(kurzfassung._anfrage_claude("Titel", "Text", "k"),
                             ("Die Kurzfassung.", {"prompt_tokens": 4100, "completion_tokens": 650}))
            for _ in range(3):
                with self.assertRaises(sprachmodell.AntwortFormat) as f:
                    kurzfassung._anfrage_claude("Titel", "Text", "k")
                self.assertNotIn("GEHEIM", str(f.exception))
        kw = gesendet[0]
        self.assertEqual((kw["model"], kw["max_tokens"], kw["output_config"]),
                         ("claude-sonnet-5-5", kurzfassung.MAX_TOKENS, {"effort": "medium"}))
        self.assertEqual(kw["system"], kurzfassung.ANWEISUNG)
        self.assertNotIn("temperature", kw)
        self.assertEqual(kurzfassung._status(N(status_code=401)), 401)   # Fehler des SDK: Kontofehler beenden den Lauf
        self.assertIsNone(kurzfassung._status(TimeoutError()))

    def test_zu_lange_antwort_wird_verworfen(self):
        lang = " ".join(["Der Spielplatz in Endenich bekommt neue Geräte."] * 20)
        with tempfile.TemporaryDirectory() as d:
            out, _ = self._lauf(d, 1, lambda t, x, k: (lang, {}))
            self.assertEqual(next(iter(kurzfassung.laden(out).values()))["verworfen"],
                             f"zu lang (mehr als {kurzfassung.MAX_WOERTER} Wörter)")


if __name__ == "__main__":
    unittest.main()
