"""Strukturdaten nach dem Datenvertrag „Strukturdaten v1“ (Entwurf, gemeinsam mit Köln und Wuppertal).

Phase 1 (strukturdaten/phase0/BERICHT_strukturdaten_phase0.md, Entscheidungen des Auftraggebers 10.11.2026):
- Strukturdatenatlas der Statistikstelle Bonn: 65 statistische Bezirke, Vergleichswerte der 4 Stadtbezirke und ganz
  Bonn; Werte unverändert, NaN als `geheim` (Daten der Bundesagentur in bewohnten Bezirken) oder `fehlt`; Haushalte
  2017 nicht übernommen (Quellfehler, audit_plausibilitaet.tsv). Freigabe der Stadt Bonn ohne Pflicht zur
  Namensnennung (Mitteilung des Auftraggebers 10.11.2026).
- Wegweiser Kommune (Bertelsmann Stiftung, CC0): Vergleichswerte Bonn, Köln, Wuppertal; nur Friendly-URLs; ändert
  sich die Version der Schnittstelle (`info.version`), bricht der Lauf ab.
- Geometrie der statistischen Bezirke von stadtplan.bonn.de (CC0); antwortet der Server nicht, die Kartengeometrie
  des Atlas (Stand 2016), in meta.json gekennzeichnet.

Schritt `strukturdaten` (auf Knopfdruck, lokal; der Atlas ändert sich etwa einmal im Jahr, live.yml meldet einen
neuen Stand): Abruf nach STRUKTURDATEN_DL (Vorgabe _strukturdaten_dl/), Aufbereitung nach data/strukturdaten/,
Prüfung. Keine Erzeugungszeitpunkte in den Datendateien außer dem Abrufdatum.
"""
import csv
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from . import config

VERTRAG = "1.1-entwurf"   # 1.1: Spalte einwohneranteil in zuordnung.tsv (Entscheidung des Auftraggebers 10.11.2026)
OUT = config.ROOT / "data" / "strukturdaten"
DL = Path(os.environ.get("STRUKTURDATEN_DL", config.ROOT / "_strukturdaten_dl"))

ATLAS = "https://www2.bonn.de/statistik/Strukturdatenatlas/"
ATLAS_DATEIEN = ["data.js", "_STA_2016.shp1.js", *[f"Statistische_Bezirke-t{i}.js" for i in range(9)]]
GEOMETRIE_URL = "https://stadtplan.bonn.de/geojson?OD=4859"
WW = "https://www.wegweiser-kommune.de/data-api/rest/"
WW_OPENAPI = "https://www.wegweiser-kommune.de/openapi?format=JSON"
WW_KOMMUNEN = ("bonn", "koeln", "wuppertal")
# Auswahl aus dem Bericht der Phase 0, Abschnitt 5 (Friendly-URLs aus rest/indicator/list geprüft)
WW_INDIKATOREN = ("bevoelkerung", "bevoelkerungsentwicklung-ueber-die-letzten-5-jahre", "durchschnittsalter",
                  "altenquotient", "jugendquotient", "auslaenderanteil", "sgb-ii-quote", "kinderarmut",
                  "einpersonen-haushalte", "haushalte-mit-kindern", "arbeitslose-an-den-svb", "wanderungssaldo")

LIZENZ_BONN = "CC0 1.0 bzw. dl-de/zero-2.0 (Freigabe der Stadt Bonn, Mitteilung des Auftraggebers 10.11.2026)"
LIZENZ_BONN_URL = ""   # genaue Bezeichnung aus der schriftlichen Antwort der Stadt offen (CLAUDE.md, Kontextdaten)
NENNUNG_BONN = "Bundesstadt Bonn, Statistikstelle – Strukturdatenatlas"
LIZENZ_GEO = "CC0 1.0 (Stadt Bonn, Datensatz „Statistische Bezirke“)"
LIZENZ_WW = "CC0 1.0"
LIZENZ_WW_URL = "https://creativecommons.org/publicdomain/zero/1.0/deed.de"
NENNUNG_WW = "Bertelsmann Stiftung, wegweiser-kommune.de"

STATUS = ("ok", "geheim", "fehlt", "abgeleitet")
TYPEN = ("anzahl", "anteil", "quote", "dichte", "mittelwert", "kategorie")
# nahezu unbewohnt (Zensus 2022: 23, 24, 69 Einwohner); die Statistikstelle weist sie mit dem Nachbarbezirk aus
# (Jahresübersicht „Bevölkerung in Bonn“: „127 Röttgen u. Kottenforst (129)“, „381 Geislar u. Siegaue (380)“,
# „388 Holtorf u. Ennert (389)“; geprüft in Phase 4). NaN dort als `fehlt` mit Hinweis (Entscheidung 10.11.2026)
ZUSAMMENGEFASST = {"129": "127", "380": "381", "389": "388"}
UNBEWOHNT = set(ZUSAMMENGEFASST)
# Quellfehler: Werte nicht übernehmen (Indikator, Jahr) → Grund
AUSGESCHLOSSEN = {("i24", "2017"): "Summe der Bezirke 239.986, ganz Bonn 170.072; elf Bezirke mit vielfachen Werten "
                                   "(z. B. 495 Lengsdorf 62.116 statt rund 2.600); Rückmeldung an die Statistikstelle"}
STADTBEZIRKE = {"1": "Bonn", "2": "Bad Godesberg", "3": "Beuel", "4": "Hardtberg"}   # comparisonFeatures 1–4
GESAMTSTADT_ID = "5"   # comparisonFeatures 5 „Bundesstadt Bonn“

# Typ und Einheit aus den Metatexten (Name allein täuscht, z. B. „Personen in Bedarfsgemeinschaften“ je 1.000 Einwohner);
# übrige Indikatoren: Anteil in %
TYP = {"i0": ("anzahl", "Personen"), "i1": ("dichte", "Einwohner je km²"), "i9": ("mittelwert", "Jahre"),
       "i10": ("quote", "ab 65-Jährige je 100 Personen von 20 bis 64 Jahren"),
       "i11": ("quote", "unter 20-Jährige je 100 Personen von 20 bis 64 Jahren"),
       "i18": ("anzahl", "Personen"), "i20": ("anzahl", "Staatsangehörigkeiten (nicht summierbar)"), "i21": ("kategorie", "Staat"),
       "i22": ("anzahl", "Personen"), "i24": ("anzahl", "Haushalte"), "i25": ("mittelwert", "Personen je Haushalt"),
       "i29": ("quote", "%"), "i30": ("quote", "je 1.000 Erwerbsfähige"), "i33": ("anzahl", "Personen"),
       "i34": ("quote", "je 1.000 Erwerbsfähige"), "i35": ("quote", "je 1.000 erwerbsfähige Ausländer"),
       "i36": ("anzahl", "Bedarfsgemeinschaften"), "i37": ("mittelwert", "Personen je Bedarfsgemeinschaft"),
       "i38": ("quote", "je 1.000 Haushalte"), "i39": ("quote", "je 1.000 Einwohner"), "i40": ("quote", "je 1.000 Kinder"),
       "i41": ("quote", "je 1.000 Erwerbsfähige"), "i42": ("anzahl", "Gebäude"), "i43": ("anzahl", "Wohnungen"),
       "i46": ("anzahl", "Räume"), "i48": ("anzahl", "Gebäude"), "i49": ("anzahl", "Wohnungen"),
       "i50": ("anzahl", "Räume"), "i51": ("anzahl", "m²"), "i52": ("anzahl", "Vorhaben"),
       "i53": ("anzahl", "Wohnungen (Zugangssaldo)"), "i54": ("anzahl", "Gebäude"), "i55": ("anzahl", "Gebäude"),
       "i56": ("anzahl", "Wohnungen"), "i57": ("quote", "je 100 Wohnungen")}
# Anzahlen, die sich nicht über Gebiete summieren lassen (verschiedene Staatsangehörigkeiten); Einheit sagt es
NICHT_SUMMIERBAR = {"i20"}
# Verteilungen: Kategorien stehen in der Quelle im Feld des Jahres, Stichtag 31.12.2025 → je Kategorie ein Anteil
VERTEILUNG = {"i44", "i45", "i47"}
VERTEILUNG_JAHR = "2025"
# Zähler, Nenner und Faktor, wo beide im Atlas stehen und sich der Wert der Quelle daraus nachrechnen lässt (geprüft
# 10.11.2026 an allen Bezirken und Jahren, Abweichung ≤ 0,05). Nicht aufgenommen: Bedarfsgemeinschaften je 1.000
# Haushalte (i38), in 2012, 2013, 2017, 2021 und 2023 mit anderer Zahl der Haushalte berechnet
BRUCH = {"i19": ("i18", "i0", 100), "i23": ("i22", "i0", 100), "i57": ("i56", "i43", 100)}
# Raumabgleich (Phase 2): ein Bezirk liegt in einem Ortsteil, wenn dort mindestens 97 % seiner Einwohner wohnen; ein
# Ortsteil ist sauber zusammengesetzt, wenn mindestens 95 % seiner Einwohner in solchen Bezirken wohnen
BEZIRK_IN_ORTSTEIL = 0.97
ORTSTEIL_SAUBER = 0.95
ZUORDNUNG_FELDER = ["von_ebene", "von_id", "nach_ebene", "nach_id", "flaechenanteil", "einwohneranteil", "methode",
                    "konfidenz"]
RAUM_AUDIT_FELDER = ["einheit", "name", "ziel", "flaechenanteil", "einwohneranteil", "methode", "konfidenz", "pruefstatus"]
METHODE = ("Verschneidung der Flächen; Einwohner aus dem Zensus 2022 (100-m-Zellen, Mittelpunkt im Gebiet); "
           "Geometrie der Bezirke siehe meta.json")

INDIKATOR_FELDER = ["indikator_id", "name", "thema", "einheit", "typ", "zaehler_id", "nenner_id", "raumebenen", "jahre",
                    "quelle", "datenhalter", "lizenz", "lizenz_url", "namensnennung", "metatext", "geheimhaltung",
                    "quell_url", "abrufdatum"]
WERT_FELDER = ["raumebene", "raum_id", "indikator_id", "jahr", "wert", "status", "quellobjekt"]
GESAMT_FELDER = ["kommune", "wegweiser_friendly_url", "indikator_id", "jahr", "wert", "abrufdatum"]
AUDIT_FELDER = ["quelle", "url", "zeitstempel", "http_status", "zeilen", "pruefsumme"]


def _slug(s):
    s = s.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>|>/b>", "", html or "")).strip()


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _tsv(path, felder, zeilen):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felder, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)


# --- Abruf -------------------------------------------------------------------------------------------------------

def _hole(url, ziel, audit, quelle, timeout=120):
    """Lädt url nach ziel; protokolliert Status, Zeilen und Prüfsumme. Gibt (ok, Last-Modified) zurück."""
    zeit = datetime.now(timezone.utc).isoformat(timespec="seconds")
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            daten, status, lm = r.read(), r.status, r.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        audit.append({"quelle": quelle, "url": url, "zeitstempel": zeit, "http_status": e.code, "zeilen": "", "pruefsumme": ""})
        return False, None
    except (urllib.error.URLError, TimeoutError) as e:
        audit.append({"quelle": quelle, "url": url, "zeitstempel": zeit, "http_status": f"Fehler: {e}"[:80],
                      "zeilen": "", "pruefsumme": ""})
        return False, None
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(daten)
    audit.append({"quelle": quelle, "url": url, "zeitstempel": zeit, "http_status": status,
                  "zeilen": _zeilen(daten), "pruefsumme": "sha256:" + hashlib.sha256(daten).hexdigest()})
    return True, lm


def _zeilen(daten):
    """Zahl der Datensätze: Werte (Atlas), Raumeinheiten, Indikatoren oder Kommunen × Jahre (Wegweiser)."""
    try:
        d = json.loads(daten.decode("utf-8-sig"))
    except ValueError:
        return daten.count(b"\n") + 1
    if isinstance(d, list):
        return len(d)
    if "indicators" in d and "data" not in d:
        return sum(len(i.get("values", [])) for i in d["indicators"])
    if "geographies" in d:
        return len(d["geographies"][0]["features"])
    if "features" in d:
        return len(d["features"])
    if "data" in d:
        return sum(1 for i in d["data"]["indicators"] for r in i["regionYearValues"] for v in r if v is not None)
    if "paths" in d:
        return len(d["paths"])
    return 1


def abrufen(dl=DL, out=OUT):
    """Atlas, Geometrie und Wegweiser nach dl; gibt den Abrufstand zurück (für meta.json)."""
    audit, stand = [], {"abrufdatum": datetime.now(timezone.utc).date().isoformat()}
    for name in ATLAS_DATEIEN:
        ok, lm = _hole(ATLAS + name, dl / "atlas" / name, audit, "Strukturdatenatlas")
        if not ok:
            raise SystemExit(f"Strukturdatenatlas: {name} nicht abrufbar, Lauf abgebrochen (audit_abruf.tsv)")
        if name == "data.js" and lm:
            stand["atlas_last_modified"] = parsedate_to_datetime(lm).date().isoformat()
    ok, _ = _hole(GEOMETRIE_URL, dl / "statistische_bezirke.geojson", audit, "Statistische Bezirke (Geometrie)")
    stand["geometrie"] = "stadtplan" if ok and _gueltige_geometrie(dl / "statistische_bezirke.geojson") else "atlas"
    # Wegweiser: Version der Schnittstelle prüfen, dann je Indikator alle Jahre für die drei Kommunen
    ok, _ = _hole(WW_OPENAPI, dl / "wegweiser" / "openapi.json", audit, "Wegweiser Kommune (OpenAPI)")
    if not ok:
        raise SystemExit("Wegweiser Kommune: OpenAPI nicht abrufbar")
    version = _json(dl / "wegweiser" / "openapi.json")["info"]["version"]
    alt = _json(out / "meta.json").get("wegweiser_version") if (out / "meta.json").exists() else None
    if alt and alt != version and os.environ.get("STRUKTURDATEN_NEUE_VERSION") != "1":
        raise SystemExit(f"Wegweiser Kommune: Schnittstelle in Version {version} statt {alt}; Lauf abgebrochen. Nach "
                         "Prüfung mit STRUKTURDATEN_NEUE_VERSION=1 erneut starten.")
    stand["wegweiser_version"] = version
    _hole(WW + "indicator/list?max=1000", dl / "wegweiser" / "indikatoren.json", audit, "Wegweiser Kommune (Indikatoren)")
    liste = {i["friendlyUrl"]: i for i in _json(dl / "wegweiser" / "indikatoren.json")}
    for fu in WW_INDIKATOREN:
        if fu not in liste:
            raise SystemExit(f"Wegweiser Kommune: Indikator „{fu}“ fehlt in der Liste")
        jahre = liste[fu]["years"]
        url = f"{WW}statistics/data/{fu}+{'+'.join(WW_KOMMUNEN)}+{jahre[0]}-{jahre[-1]}"
        ok, _ = _hole(url, dl / "wegweiser" / f"{fu}.json", audit, "Wegweiser Kommune (Daten)")
        if not ok:
            raise SystemExit(f"Wegweiser Kommune: Daten für „{fu}“ nicht abrufbar")
    _tsv(out / "audit_abruf.tsv", AUDIT_FELDER, audit)
    return stand


def _gueltige_geometrie(path):
    try:
        return len(_json(path).get("features", [])) == 65
    except (ValueError, OSError):
        return False


# --- Aufbereitung: Atlas ----------------------------------------------------------------------------------------

def _status_nan(iid, raum_id, metatext):
    if raum_id in UNBEWOHNT:
        return "fehlt"
    bundesagentur = "Bundesagentur" in metatext or "Fallzahl unter 10" in metatext
    return "geheim" if bundesagentur else "fehlt"


def _wert(x):
    if isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x)):
        return ("%s" % x).rstrip("0").rstrip(".") if isinstance(x, float) else str(x)
    return str(x)


def atlas(roh, abrufdatum):
    """Indikatoren und Werte des Atlas nach dem Vertrag; gibt (indikatoren, werte, plausibilitaet) zurück."""
    meta = _json(roh / "data.js")["geographies"][0]
    bezirke = [f["id"] for f in meta["features"]]
    indikatoren, werte, plaus, gesehen = {}, [], [], {}
    for thema in meta["themes"]:
        datei = Path(thema["fileName"].split("?")[0]).name
        quelle_url = ATLAS + datei
        for ind in _json(roh / datei)["indicators"]:
            iid, metatext = ind["id"], _text(next((p["value"] for p in ind.get("properties", []) if p["name"] == "metatext"), ""))
            if metatext:
                gesehen[iid] = metatext
            metatext = metatext or gesehen.get(iid, "")
            if iid in VERTEILUNG:
                vid, jahr, name = f"bonn-sda-{iid}-{_slug(ind['date'])}", VERTEILUNG_JAHR, f"{ind['name']} {ind['date']}"
                typ, einheit = "anteil", "%"
            else:
                vid, jahr, name = f"bonn-sda-{iid}", ind["date"], ind["name"]
                typ, einheit = TYP.get(iid, ("anteil", "%"))
            ba = "Bundesagentur" in metatext or "Fallzahl unter 10" in metatext
            eintrag = indikatoren.setdefault(vid, {
                "indikator_id": vid, "name": name, "thema": thema["themeName"], "einheit": einheit, "typ": typ,
                "zaehler_id": f"bonn-sda-{BRUCH[iid][0]}" if iid in BRUCH else "",
                "nenner_id": f"bonn-sda-{BRUCH[iid][1]}" if iid in BRUCH else "",
                "raumebenen": "statistischer_bezirk;stadtbezirk;gesamtstadt", "jahre": [],
                "quelle": "Strukturdatenatlas der Bundesstadt Bonn",
                "datenhalter": ("Bundesagentur für Arbeit; Berechnung Statistikstelle der Bundesstadt Bonn" if ba
                                else "Bundesstadt Bonn, Statistikstelle"),
                "lizenz": LIZENZ_BONN, "lizenz_url": LIZENZ_BONN_URL, "namensnennung": NENNUNG_BONN,
                "metatext": metatext,
                "geheimhaltung": "absolute Fallzahl unter 10 wird nicht ausgewiesen (Bundesagentur für Arbeit)" if ba else "",
                "quell_url": quelle_url, "abrufdatum": abrufdatum})
            if jahr not in eintrag["jahre"]:
                eintrag["jahre"].append(jahr)
            quellobjekt = f"{quelle_url}#{iid}/{ind['date']}"
            aus = AUSGESCHLOSSEN.get((iid, jahr))
            zeilen = [("statistischer_bezirk", rid, v) for rid, v in zip(bezirke, ind["values"])]
            vgl = ind.get("comparisonValues") or []
            zeilen += [("stadtbezirk", sid, vgl[int(sid) - 1]) for sid in STADTBEZIRKE if len(vgl) >= int(sid)]
            if len(vgl) >= 5:
                zeilen.append(("gesamtstadt", "bonn", vgl[4]))
            for ebene, rid, v in zeilen:
                if aus:
                    status, w = "fehlt", ""
                elif v == "NaN" or v is None:
                    status = "fehlt" if ebene != "statistischer_bezirk" else _status_nan(iid, rid, metatext)
                    w = ""
                else:
                    status, w = "ok", _wert(v)
                werte.append({"raumebene": ebene, "raum_id": rid, "indikator_id": vid, "jahr": jahr, "wert": w,
                              "status": status, "quellobjekt": quellobjekt})
            if aus:
                plaus.append({"indikator_id": vid, "jahr": jahr, "befund": "nicht übernommen", "grund": aus})
    for e in indikatoren.values():
        e["jahre"] = ";".join(e["jahre"])
    plaus += summenpruefung(indikatoren.values(), werte)
    return list(indikatoren.values()), werte, plaus


def summenpruefung(indikatoren, werte):
    """Anzahlen: Summe der Bezirke gegen ganz Bonn (Abweichung > 0,1 % als Hinweis; Fälle ohne Bezirkszuordnung)."""
    anzahl = {i["indikator_id"] for i in indikatoren if i["typ"] == "anzahl"
              and i["indikator_id"].removeprefix("bonn-sda-") not in NICHT_SUMMIERBAR}
    summen, gesamt = {}, {}
    for w in werte:
        if w["indikator_id"] not in anzahl or w["status"] != "ok":
            continue
        k = (w["indikator_id"], w["jahr"])
        if w["raumebene"] == "statistischer_bezirk":
            summen[k] = summen.get(k, 0) + float(w["wert"])
        elif w["raumebene"] == "gesamtstadt":
            gesamt[k] = float(w["wert"])
    out = []
    for k, g in sorted(gesamt.items()):
        s = summen.get(k, 0)
        if g and abs(s - g) > max(2, 0.001 * g):
            out.append({"indikator_id": k[0], "jahr": k[1], "befund": "Summe weicht ab",
                        "grund": f"Summe der Bezirke {s:,.0f}, ganz Bonn {g:,.0f} ({(s - g) / g:+.1%}); unverändert "
                                 "übernommen".replace(",", ".")})
    return out


# --- Geometrie --------------------------------------------------------------------------------------------------

def _atlas_geometrie(path):
    """Kartengeometrie des Atlas (Pixelraster in Web Mercator, Deltas) → WGS84."""
    d = _json(path)
    x0, y0, x1, y1 = map(float, d["boundingBox"].split())
    w, h = d["pixelWidth"], d["pixelHeight"]

    def ll(px, py):
        mx, my = x0 + px / w * (x1 - x0), y0 + py / h * (y1 - y0)
        lon = mx / 6378137 * 180 / math.pi
        lat = math.degrees(2 * math.atan(math.exp(my / 6378137)) - math.pi / 2)
        return [round(lon, 6), round(lat, 6)]
    out = {}
    for f in d["features"]:
        ringe = []
        for p in f["p"]:
            x, y = p[0], p[1]
            pts = [ll(x, y)]
            for i in range(2, len(p), 2):
                x, y = x + p[i], y + p[i + 1]
                pts.append(ll(x, y))
            if pts[0] != pts[-1]:
                pts.append(pts[0])
            ringe.append([pts])
        out[f["d"]] = {"type": "MultiPolygon", "coordinates": ringe}
    return out


def geometrie(roh_atlas, stadtplan, quelle):
    """raum/statistischer_bezirk.geojson nach dem Vertrag; quelle: „stadtplan“ oder „atlas“."""
    meta = _json(roh_atlas / "data.js")["geographies"][0]
    eltern = {name: sid for sid, name in STADTBEZIRKE.items()}
    if quelle == "stadtplan":
        geo = {}
        for f in _json(stadtplan)["features"]:
            p = f["properties"]
            rid = str(next(v for k, v in p.items() if re.fullmatch(r"(stat(istischer)?_?bezirk|bezirk_?nr|id|nr)", k, re.I)))
            geo[rid.zfill(3)] = f["geometry"]
        herkunft, lizenz = GEOMETRIE_URL, LIZENZ_GEO
    else:
        geo = _atlas_geometrie(roh_atlas / "_STA_2016.shp1.js")
        herkunft, lizenz = ATLAS + "_STA_2016.shp1.js", LIZENZ_BONN + "; Kartengeometrie des Atlas, Stand 2016"
    feats = []
    for f in meta["features"]:
        bezirk = f["filters"][0]["name"].removeprefix("Stadtbezirk ")
        feats.append({"type": "Feature", "geometry": geo[f["id"]], "properties": {
            "raum_id": f["id"], "name": f["name"].split(" ", 1)[1], "raumebene": "statistischer_bezirk",
            "eltern_id": eltern[bezirk], "quelle": herkunft, "lizenz": lizenz}})
    return {"type": "FeatureCollection", "features": feats}


def stadtbezirke(path=config.STADTBEZIRKE):
    """raum/stadtbezirk.geojson aus den Flächen der Stadtbezirke (CC0, bereits im Repository); Nummern wie im Atlas."""
    feats = []
    for f in sorted(_json(path)["features"], key=lambda f: f["properties"]["bezirk"]):
        sid = str(f["properties"]["bezirk"])
        if STADTBEZIRKE.get(sid) != f["properties"]["bezirk_bez"]:
            raise SystemExit(f"Stadtbezirk {sid}: Name passt nicht zum Atlas")
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "raum_id": sid, "name": STADTBEZIRKE[sid], "raumebene": "stadtbezirk", "eltern_id": "bonn",
            "quelle": "https://opendata.bonn.de/dataset/flächen-der-stadtbezirke", "lizenz": "CC0 1.0 (Stadt Bonn)"}})
    return {"type": "FeatureCollection", "features": feats}


# --- Aufbereitung: Wegweiser ------------------------------------------------------------------------------------

def _typ_ww(einheit):
    e = einheit.lower()
    if e in ("anzahl", "einwohner:innen"):
        return "anzahl"
    if e == "jahre":
        return "mittelwert"
    if e == "%":
        return "anteil"
    return "quote"


def wegweiser(roh, abrufdatum):
    liste = {i["friendlyUrl"]: i for i in _json(roh / "indikatoren.json")}
    indikatoren, gesamt = [], []
    for fu in WW_INDIKATOREN:
        info, daten = liste[fu], _json(roh / f"{fu}.json")["data"]
        ind = daten["indicators"][0]
        iid = f"wk-{fu}"
        indikatoren.append({
            "indikator_id": iid, "name": info["name"], "thema": "Vergleich der Kommunen", "einheit": info.get("unit") or "",
            "typ": _typ_ww(info.get("unit") or ""), "zaehler_id": "", "nenner_id": "", "raumebenen": "gemeinde",
            "jahre": ";".join(str(j) for j in info["years"]), "quelle": "Wegweiser Kommune (Bertelsmann Stiftung)",
            "datenhalter": info.get("source") or "", "lizenz": LIZENZ_WW, "lizenz_url": LIZENZ_WW_URL,
            "namensnennung": NENNUNG_WW,
            "metatext": " ".join(x for x in (info.get("explanation"), "Berechnung: " + info["calculation"]
                                             if info.get("calculation") else "") if x),
            "geheimhaltung": "", "quell_url": f"https://www.wegweiser-kommune.de/statistik/{fu}+bonn+koeln+wuppertal",
            "abrufdatum": abrufdatum})
        jahre = _json(roh / f"{fu}.json")["years"]
        for region, reihe in zip(daten["regions"], ind["regionYearValues"]):
            for jahr, wert in zip(jahre, reihe):
                if wert is None:
                    continue
                gesamt.append({"kommune": region["friendlyUrl"], "wegweiser_friendly_url": fu, "indikator_id": iid,
                               "jahr": str(jahr), "wert": _wert(wert), "abrufdatum": abrufdatum})
    return indikatoren, gesamt


# --- Raumabgleich (Phase 2) -------------------------------------------------------------------------------------

ZENSUS = config.ROOT / "data" / "kontext" / "zensus_bonn.tsv"


def raumabgleich(bezirke_geo, ortsteile_geo=None, zensus=ZENSUS):
    """Statistischer Bezirk → Ortsteil nach Fläche und Einwohnern (Zensus-Zellen, Mittelpunkt im Gebiet).

    Gibt (zuordnung, audit, saubere Ortsteile {slug: [Bezirke]}, Namen der Ortsteile) zurück. Geteilte Bezirke werden
    gemeldet, nicht stillschweigend zugeordnet (Prompt Strukturdaten, Phase 2)."""
    from shapely import make_valid
    from shapely.geometry import Point, shape
    ortsteile_geo = ortsteile_geo or _json(config.ORTSTEILE)
    O = [(_slug(f["properties"]["ortsteil_bez"]), f["properties"]["ortsteil_bez"], make_valid(shape(f["geometry"])))
         for f in ortsteile_geo["features"]]
    B = [(f["properties"]["raum_id"], f["properties"]["name"], make_valid(shape(f["geometry"])))
         for f in bezirke_geo["features"]]
    ew, ew_b, ew_o = {}, {}, {}
    with open(zensus, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            e = float(r["einwohner"] or 0)
            if not e:
                continue
            pt = Point(float(r["lon"]), float(r["lat"]))
            b = next((i for i, _, g in B if g.contains(pt)), None)
            o = next((i for i, _, g in O if g.contains(pt)), None)
            if b and o:
                ew[(b, o)] = ew.get((b, o), 0) + e
                ew_b[b] = ew_b.get(b, 0) + e
            if o:
                ew_o[o] = ew_o.get(o, 0) + e
    zuordnung, audit, haupt = [], [], {}
    for bid, bname, g in B:
        teile = []
        for oid, oname, og in O:
            fa = g.intersection(og).area / g.area
            ea = ew.get((bid, oid), 0) / ew_b[bid] if ew_b.get(bid) else 0.0
            if fa >= 0.001 or ea > 0:
                teile.append((oid, oname, fa, ea))
        teile.sort(key=lambda t: (-t[3], -t[2]))
        liegt = bool(ew_b.get(bid)) and teile[0][3] >= BEZIRK_IN_ORTSTEIL
        if liegt:
            haupt[bid] = teile[0][0]
        for oid, oname, fa, ea in teile:
            konf = "hoch" if ea >= BEZIRK_IN_ORTSTEIL else ("mittel" if ea >= 0.5 else "niedrig")
            zuordnung.append({"von_ebene": "statistischer_bezirk", "von_id": bid, "nach_ebene": "ortsteil", "nach_id": oid,
                              "flaechenanteil": f"{fa:.4f}", "einwohneranteil": f"{ea:.4f}", "methode": METHODE,
                              "konfidenz": konf})
            status = ("ohne Einwohner im Zensus" if not ew_b.get(bid) else
                      "liegt im Ortsteil" if liegt and oid == teile[0][0] else
                      "Randanteil, nicht zugeordnet" if liegt else "geteilt, nicht zugeordnet")
            audit.append({"einheit": bid, "name": bname, "ziel": oname, "flaechenanteil": f"{fa:.4f}",
                          "einwohneranteil": f"{ea:.4f}", "methode": METHODE, "konfidenz": konf, "pruefstatus": status})
    sauber = {}
    for oid, oname, _ in O:
        mitglieder = sorted(b for b, o in haupt.items() if o == oid)
        drin = sum(ew.get((b, oid), 0) for b in mitglieder)
        if mitglieder and ew_o.get(oid) and drin / ew_o[oid] >= ORTSTEIL_SAUBER:
            sauber[oid] = mitglieder
    return zuordnung, audit, sauber, {oid: oname for oid, oname, _ in O}


def ortsteilwerte(werte, indikatoren, sauber, unbewohnt=UNBEWOHNT):
    """Werte je sauber zusammengesetztem Ortsteil (Status `abgeleitet`): ein Bezirk → Wert übernommen; mehrere Bezirke →
    Anzahlen summiert, Anteile aus Zähler und Nenner (BRUCH); übrige Kennzahlen nicht gebildet. Nahezu unbewohnte
    Bezirke ohne Werte zählen in Summen nicht mit."""
    typ = {i["indikator_id"]: i["typ"] for i in indikatoren}
    bez = {}
    for w in werte:
        if w["raumebene"] == "statistischer_bezirk":
            bez[(w["indikator_id"], w["jahr"], w["raum_id"])] = w
    reihen = sorted({(w["indikator_id"], w["jahr"]) for w in bez.values()})
    out = []
    for oid, mitglieder in sorted(sauber.items()):
        quelle = f"zuordnung.tsv: statistischer_bezirk {'+'.join(mitglieder)} → ortsteil {oid}"
        for iid, jahr in reihen:
            teile = [bez.get((iid, jahr, b)) for b in mitglieder]
            if any(t is None for t in teile):
                continue
            q = iid.removeprefix("bonn-sda-")
            zeile = {"raumebene": "ortsteil", "raum_id": oid, "indikator_id": iid, "jahr": jahr, "quellobjekt": quelle}
            if len(teile) == 1:
                t = teile[0]
                out.append({**zeile, "wert": t["wert"], "status": "abgeleitet" if t["status"] == "ok" else t["status"]})
                continue
            gezaehlt = [t for t in teile if not (t["raum_id"] in unbewohnt and t["status"] == "fehlt")]
            if typ.get(iid) == "anzahl" and q not in NICHT_SUMMIERBAR:
                if all(t["status"] == "ok" for t in gezaehlt):
                    out.append({**zeile, "wert": _wert(round(sum(float(t["wert"]) for t in gezaehlt), 3)),
                                "status": "abgeleitet"})
                else:
                    out.append({**zeile, "wert": "", "status": "fehlt"})
            elif q in BRUCH:
                z, n, faktor = BRUCH[q]
                zs = [bez.get((f"bonn-sda-{z}", jahr, b)) for b in mitglieder]
                ns = [bez.get((f"bonn-sda-{n}", jahr, b)) for b in mitglieder]
                paare = [(a, b) for a, b in zip(zs, ns) if a and b and not (a["raum_id"] in unbewohnt and a["status"] == "fehlt")]
                if paare and all(a["status"] == "ok" and b["status"] == "ok" for a, b in paare) and \
                        sum(float(b["wert"]) for _, b in paare):
                    wert = sum(float(a["wert"]) for a, _ in paare) / sum(float(b["wert"]) for _, b in paare) * faktor
                    out.append({**zeile, "wert": _wert(round(wert, 1)), "status": "abgeleitet"})
                else:
                    out.append({**zeile, "wert": "", "status": "fehlt"})
    return out


def ortsteile_geo(path=None):
    """raum/ortsteil.geojson (Flächen der Stadt Bonn, CC0); eltern_id = Stadtbezirk wie im Atlas."""
    eltern = {name: sid for sid, name in STADTBEZIRKE.items()}
    feats = []
    for f in _json(path or config.ORTSTEILE)["features"]:
        p = f["properties"]
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "raum_id": _slug(p["ortsteil_bez"]), "name": p["ortsteil_bez"], "raumebene": "ortsteil",
            "eltern_id": eltern.get(p["bezirk_bez"], ""),
            "quelle": "https://opendata.bonn.de/dataset/flächen-der-ortsteile", "lizenz": "CC0 1.0 (Stadt Bonn)"}})
    feats.sort(key=lambda f: f["properties"]["raum_id"])
    return {"type": "FeatureCollection", "features": feats}


# --- Prüfung ----------------------------------------------------------------------------------------------------

def pruefen(out=OUT):
    """Prüft die Dateien des Vertrags; gibt eine Liste von Fehlern zurück (leer = in Ordnung)."""
    fehler = []
    def lies(name):
        with open(out / name, encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    ind = {r["indikator_id"]: r for r in lies("indikatoren.tsv")}
    for r in ind.values():
        if r["typ"] not in TYPEN:
            fehler.append(f"{r['indikator_id']}: Typ „{r['typ']}“")
        for k in ("name", "einheit", "quelle", "lizenz", "quell_url", "abrufdatum"):
            if not r[k]:
                fehler.append(f"{r['indikator_id']}: Feld {k} leer")
    for r in lies("werte.tsv"):
        if r["status"] not in STATUS:
            fehler.append(f"{r['indikator_id']} {r['raum_id']} {r['jahr']}: Status „{r['status']}“")
        if r["indikator_id"] not in ind:
            fehler.append(f"{r['indikator_id']}: nicht in indikatoren.tsv")
        if not r["quellobjekt"]:
            fehler.append(f"{r['indikator_id']} {r['raum_id']} {r['jahr']}: ohne Quellobjekt")
        if (r["status"] in ("geheim", "fehlt")) != (r["wert"] == ""):
            fehler.append(f"{r['indikator_id']} {r['raum_id']} {r['jahr']}: Wert und Status passen nicht")
    for r in lies("gesamtstadt.tsv"):
        if r["indikator_id"] not in ind or not r["wegweiser_friendly_url"]:
            fehler.append(f"gesamtstadt: {r['indikator_id']}")
    for r in lies("zuordnung.tsv"):
        if r["konfidenz"] not in ("hoch", "mittel", "niedrig") or not (0 <= float(r["einwohneranteil"]) <= 1):
            fehler.append(f"zuordnung {r['von_id']} → {r['nach_id']}")
    for f in [*_json(out / "raum" / "statistischer_bezirk.geojson")["features"],
              *_json(out / "raum" / "ortsteil.geojson")["features"],
              *_json(out / "raum" / "stadtbezirk.geojson")["features"]]:
        if set(f["properties"]) != {"raum_id", "name", "raumebene", "eltern_id", "quelle", "lizenz"}:
            fehler.append(f"Geometrie {f['properties'].get('raum_id')}: Properties")
    meta = _json(out / "meta.json")
    for k in ("vertrag_version", "datenstand", "abrufdatum", "veroeffentlichen", "lizenzstatus", "quellen"):
        if k not in meta:
            fehler.append(f"meta.json: {k} fehlt")
    return fehler


# --- Schritt ----------------------------------------------------------------------------------------------------

def aufbereiten(dl=DL, out=OUT, stand=None):
    stand = stand or (_json(out / "meta.json") if (out / "meta.json").exists() else {})
    abrufdatum = stand.get("abrufdatum", "")
    ind, werte, plaus = atlas(dl / "atlas", abrufdatum)
    ind_ww, gesamt = wegweiser(dl / "wegweiser", abrufdatum)
    geo = geometrie(dl / "atlas", dl / "statistische_bezirke.geojson", stand.get("geometrie", "atlas"))
    zuordnung, audit_raum, sauber, namen = raumabgleich(geo)
    werte_ot = ortsteilwerte(werte, ind, sauber)
    ot_ind = {w["indikator_id"] for w in werte_ot}
    for i in ind:
        if i["indikator_id"] in ot_ind:
            i["raumebenen"] = "statistischer_bezirk;ortsteil;stadtbezirk;gesamtstadt"
    _tsv(out / "indikatoren.tsv", INDIKATOR_FELDER, ind + ind_ww)
    _tsv(out / "werte.tsv", WERT_FELDER, werte + werte_ot)
    _tsv(out / "zuordnung.tsv", ZUORDNUNG_FELDER, zuordnung)
    _tsv(out / "audit_raumabgleich.tsv", RAUM_AUDIT_FELDER, audit_raum)
    _tsv(out / "gesamtstadt.tsv", GESAMT_FELDER, gesamt)
    _tsv(out / "audit_plausibilitaet.tsv", ["indikator_id", "jahr", "befund", "grund"], plaus)
    (out / "raum").mkdir(parents=True, exist_ok=True)
    (out / "raum" / "statistischer_bezirk.geojson").write_text(
        json.dumps(geo, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (out / "raum" / "ortsteil.geojson").write_text(
        json.dumps(ortsteile_geo(), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (out / "raum" / "stadtbezirk.geojson").write_text(
        json.dumps(stadtbezirke(), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    meta = {
        "vertrag_version": VERTRAG,
        "datenstand": stand.get("atlas_last_modified", ""),
        "abrufdatum": abrufdatum,
        "veroeffentlichen": True,
        "lizenzstatus": "freigegeben: " + LIZENZ_BONN,
        "geometrie": ("stadtplan.bonn.de (aktuell)" if stand.get("geometrie") == "stadtplan" else
                      "Kartengeometrie des Strukturdatenatlas, Stand 2016 (stadtplan.bonn.de beim Abruf nicht erreichbar)"),
        "wegweiser_version": stand.get("wegweiser_version", ""),
        "quellen": [
            {"name": "Strukturdatenatlas der Bundesstadt Bonn", "url": ATLAS, "lizenz": LIZENZ_BONN,
             "namensnennung": NENNUNG_BONN},
            {"name": "Statistische Bezirke (Geometrie)", "url": "https://opendata.bonn.de/dataset/statistische-bezirke",
             "lizenz": LIZENZ_GEO},
            {"name": "Wegweiser Kommune (Bertelsmann Stiftung)", "url": "https://www.wegweiser-kommune.de/open-data",
             "lizenz": LIZENZ_WW, "namensnennung": NENNUNG_WW},
        ],
        "hinweise": [
            "Werte unverändert aus der Quelle; keine Schätzung. „geheim“: in der Quelle nicht ausgewiesen, nach dem Metatext "
            "wegen Fallzahl unter 10 (Daten der Bundesagentur für Arbeit). „fehlt“: in der Quelle ohne Wert.",
            "Bezirke 129 Kottenforst, 380 Siegaue, 389 Ennert: nahezu unbewohnt, in der Quelle ohne eigene Werte; "
            "ihre Einwohner sind in den Werten der Bezirke 127, 381 und 388 enthalten (so ausgewiesen in der "
            "Jahresübersicht „Bevölkerung in Bonn“ der Statistikstelle).",
            f"Werte je Ortsteil (Status „abgeleitet“) nur für {len(sauber)} von {len(namen)} Ortsteilen, deren Einwohner zu "
            f"mindestens {ORTSTEIL_SAUBER:.0%} in Bezirken wohnen, die zu mindestens {BEZIRK_IN_ORTSTEIL:.0%} im Ortsteil liegen "
            "(zuordnung.tsv); ein Bezirk: Wert übernommen; mehrere: Anzahlen summiert, Anteile nur aus Zähler und Nenner. "
            "Grundlage: Geometrie siehe oben, Einwohner Zensus 2022; wird mit der aktuellen Geometrie der Stadt neu berechnet.",
            "Gesamtstädtische Werte aus dem Wegweiser und kleinräumige Werte der Statistikstelle unterscheiden sich in "
            "Definition und Stichtag (z. B. Einwohner: amtliche Fortschreibung bzw. Melderegister); nicht vermischen.",
        ],
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    fehler = pruefen(out)
    if fehler:
        raise SystemExit("Strukturdaten: " + "; ".join(fehler[:10]))
    n_ind = len(ind) + len(ind_ww)
    print(f"Strukturdaten: {n_ind} Indikatoren, {len(werte)} Werte, {len(gesamt)} Vergleichswerte, "
          f"{len(geo['features'])} Bezirke ({meta['geometrie']}), {len(plaus)} Plausibilitätshinweise; Raumabgleich: "
          f"{len(sauber)} von {len(namen)} Ortsteilen sauber, {len(werte_ot)} Werte je Ortsteil → {out}")


def schritt():
    stand = abrufen()
    aufbereiten(stand=stand)


# --- Seite (Phase 3) --------------------------------------------------------------------------------------------

# Flächenfarbe: ausgewählte relative Kennzahlen (Entscheidung des Auftraggebers 10.11.2026); im Steckbrief dazu die
# Grundzahlen. Übrige Kennzahlen bleiben in data/strukturdaten/ und im Datenpaket.
FARBE = ("i1", "i9", "i11", "i10", "i12", "i17", "i23", "i26", "i27", "i28", "i29", "i41")
STECKBRIEF = ("i0", "i24", "i43", *FARBE)
SEITE = "strukturdaten.json"


def _num(w):
    if w["status"] == "geheim":
        return "g"
    if w["status"] == "fehlt" or w["wert"] == "":
        return None
    try:
        return float(w["wert"]) if "." in w["wert"] else int(w["wert"])
    except ValueError:
        return w["wert"]


def seite(src=OUT, out=None):
    """export/bonn/strukturdaten.json: kompakte Fassung für die Seite (Flächen der Bezirke, Steckbrief, Vergleich)."""
    from . import flaechen
    out = out or config.EXPORT / "bonn"
    if not (src / "meta.json").exists():
        print("Strukturdaten: data/strukturdaten/ fehlt, keine Datei für die Seite")
        return

    def lies(name):
        with open(src / name, encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))
    meta = _json(src / "meta.json")
    alle = {r["indikator_id"]: r for r in lies("indikatoren.tsv")}
    ids = {f"bonn-sda-{i}": i for i in STECKBRIEF}
    ind = {}
    for vid, kurz in ids.items():
        r = alle[vid]
        ind[kurz] = {"name": r["name"], "thema": r["thema"], "einheit": r["einheit"], "typ": r["typ"],
                     "metatext": r["metatext"], "geheimhaltung": r["geheimhaltung"],
                     "jahre": [j for j in r["jahre"].split(";") if j]}
    ebene = {"statistischer_bezirk": "b", "ortsteil": "o", "stadtbezirk": "s", "gesamtstadt": "g"}
    werte = {k: {"b": {}, "o": {}, "s": {}, "g": {}} for k in ind}
    for w in lies("werte.tsv"):
        kurz = ids.get(w["indikator_id"])
        if not kurz:
            continue
        jahre = ind[kurz]["jahre"]
        reihe = werte[kurz][ebene[w["raumebene"]]].setdefault(w["raum_id"], [None] * len(jahre))
        reihe[jahre.index(w["jahr"])] = _num(w)
    for k in werte:   # ganz Bonn als Liste, nicht als Abbildung
        werte[k]["g"] = werte[k]["g"].get("bonn", [])
    geo = _json(src / "raum" / "statistischer_bezirk.geojson")
    zu = lies("zuordnung.tsv")
    haupt = {}
    for r in zu:
        if float(r["einwohneranteil"]) > float(haupt.get(r["von_id"], {}).get("einwohneranteil", -1)):
            haupt[r["von_id"]] = r
    namen_ot = {f["properties"]["raum_id"]: f["properties"]["name"] for f in _json(src / "raum" / "ortsteil.geojson")["features"]}
    sauber = {r["raum_id"] for r in lies("werte.tsv") if r["raumebene"] == "ortsteil"}
    bezirke = [{"id": f["properties"]["raum_id"], "name": f["properties"]["name"],
                "stadtbezirk": STADTBEZIRKE[f["properties"]["eltern_id"]],
                "ortsteil": namen_ot.get(haupt.get(f["properties"]["raum_id"], {}).get("nach_id"), ""),
                "anteil": round(float(haupt.get(f["properties"]["raum_id"], {}).get("einwohneranteil", 0)), 3)}
               for f in geo["features"]]
    ortsteile = {}
    for slug, name in namen_ot.items():
        teile = sorted(((r["von_id"], round(float(r["einwohneranteil"]), 3)) for r in zu
                        if r["nach_id"] == slug and float(r["einwohneranteil"]) >= 0.01), key=lambda t: -t[1])
        ortsteile[name] = {"slug": slug, "sauber": slug in sauber, "bezirke": teile}
    flaechen_geo = flaechen.simplify({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": f["properties"]["raum_id"]}, "geometry": f["geometry"]}
        for f in geo["features"]]}, toleranz=0.00005)
    ww = []
    gesamt = lies("gesamtstadt.tsv")
    for r in alle.values():
        if not r["indikator_id"].startswith("wk-"):
            continue
        reihen = {}
        for g in gesamt:
            if g["indikator_id"] == r["indikator_id"]:
                reihen.setdefault(g["jahr"], {})[g["kommune"]] = float(g["wert"])
        jahr = max((j for j, v in reihen.items() if len(v) == len(WW_KOMMUNEN)), default=None)
        if jahr:
            ww.append({"name": r["name"], "einheit": r["einheit"], "jahr": jahr, "werte": reihen[jahr],
                       "friendly_url": r["indikator_id"][3:], "datenhalter": r["datenhalter"]})
    daten = {
        "meta": {"datenstand": meta["datenstand"], "abrufdatum": meta["abrufdatum"], "geometrie": meta["geometrie"],
                 "lizenz": LIZENZ_BONN, "namensnennung": NENNUNG_BONN, "url": ATLAS,
                 "wegweiser": {"lizenz": LIZENZ_WW, "namensnennung": NENNUNG_WW,
                               "url": "https://www.wegweiser-kommune.de/open-data", "abrufdatum": meta["abrufdatum"]},
                 "farbe": list(FARBE), "steckbrief": list(STECKBRIEF), "zusammengefasst": dict(sorted(ZUSAMMENGEFASST.items()))},
        "ind": ind, "werte": werte, "bezirke": bezirke, "ortsteile": ortsteile, "geo": flaechen_geo, "wegweiser": ww,
    }
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    (out / SEITE).write_text(text, encoding="utf-8")
    print(f"Strukturdaten für die Seite: {len(ind)} Kennzahlen, {len(bezirke)} Bezirke, {len(ww)} Vergleiche, "
          f"{len(text) // 1024} KB → {out / SEITE}")


# --- Verifikation (Phase 4) -------------------------------------------------------------------------------------

# Stichprobe von 20 Werten gegen zweite Veröffentlichungen der Statistikstelle (PDF, ausgelesen mit pdftotext) und
# einen zweiten Abrufweg des Wegweisers (CSV-Export); einmalig, lokal (Schritt `strukturdaten-verifikation`)
VERIFIKATION = "audit_verifikation.tsv"
SEED = 20261110
# Zeile im Bezirksblatt „Soziodemographische Indikatoren“ (Stichtag 31.12.2025) → Kennzahl, Spalte (Wert oder Anteil)
BLATT = {"i0": ("1. Bevölkerung", "wert"), "i1": ("2. Bevölkerungsdichte", "wert"), "i9": ("12. Durchschnittsalter", "wert"),
         "i10": ("19. Altenquotient", "wert"), "i11": ("20. Jugendquotient", "wert"), "i12": ("13.   unter 6 Jahre", "anteil"),
         "i17": ("18.   75 Jahre und älter", "anteil"), "i24": ("30. Haushalte", "wert"),
         "i26": ("31. Ein-Personen-Haushalte", "anteil"), "i29": ("45. Arbeitslose ", "anteil"),
         "i43": ("36. Wohnungsbestand", "wert")}
# Spalten der Jahresübersicht „Bevölkerung in Bonn“ (2020, 2024): Index der Zahl in der Zeile eines Bezirks
JAHRESBLATT = {"i0": 0, "i1": 1, "i24": 12, "i25": 14}


def _zahl(t):
    t = t.strip("()").replace(".", "").replace(",", ".").replace(" ", "")
    return float(t)


def _pdftext(pfad):
    import subprocess
    return subprocess.run(["pdftotext", "-layout", str(pfad), "-"], capture_output=True, text=True, check=True).stdout


def blattwerte(text, kennzahl):
    """Wert, Stadtbezirk und Stadt Bonn einer Zeile des Bezirksblatts (Anteile in Klammern)."""
    label, spalte = BLATT[kennzahl]
    zeile = next(z for z in text.splitlines() if z.strip().startswith(label.strip()) and label in z)
    rest = re.split(r"\d{2}\.\d{2}\.\d{4}", zeile, maxsplit=1)[1]
    werte = re.findall(r"\(-?\d[\d.]*(?:,\d+)?\)|-?\d[\d.]*(?:,\d+)?", rest)
    zahlen = [w for w in werte if not w.startswith("(")]
    klammern = [w for w in werte if w.startswith("(")]
    if spalte == "anteil":
        return {"wert": _zahl(klammern[0]), "stadtbezirk": _zahl(klammern[2]) if len(klammern) > 3 else None,
                "stadt": _zahl(klammern[3]) if len(klammern) > 3 else None}
    return {"wert": _zahl(zahlen[0]), "stadtbezirk": _zahl(zahlen[2]), "stadt": _zahl(zahlen[3])}


def jahreswert(text, bezirk, kennzahl):
    zeile = next(z for z in text.splitlines() if re.match(rf"^{bezirk} ", z))
    rest = re.split(r"\s{2,}", zeile.strip(), maxsplit=1)[1]
    rest = re.sub(r"([+-])\s+(?=\d)", r"\1", rest)
    zahlen = re.findall(r"[+-]?\d[\d.]*(?:,\d+)?", rest)
    return _zahl(zahlen[JAHRESBLATT[kennzahl]])


def verifikation(src=OUT, dl=DL):
    import random
    rnd = random.Random(SEED)
    with open(src / "werte.tsv", encoding="utf-8") as f:
        W = {(r["raumebene"], r["raum_id"], r["indikator_id"], r["jahr"]): r for r in csv.DictReader(f, delimiter="\t")}
    with open(src / "gesamtstadt.tsv", encoding="utf-8") as f:
        G = {(r["kommune"], r["wegweiser_friendly_url"], r["jahr"]): r for r in csv.DictReader(f, delimiter="\t")}
    namen = {f["id"]: f["name"].split(" ", 1)[1] for f in _json(dl / "atlas" / "data.js")["geographies"][0]["features"]}
    audit, pdfs = [], {}

    def pdf(name):
        if name not in pdfs:
            ziel = dl / "verifikation" / name
            if not ziel.exists():
                ok, _ = _hole(ATLAS + urllib.request.quote(name), ziel, [], "Verifikation")
                if not ok:
                    raise SystemExit(f"Verifikation: {name} nicht abrufbar")
            pdfs[name] = _pdftext(ziel)
        return pdfs[name]

    def zeile(ebene, rid, iid, jahr, gegen, url, fundstelle, toleranz=0.051, stellen=None):
        """stellen: Nachkommastellen der Gegenquelle (die Jahresübersicht nennt die Dichte ganzzahlig)."""
        r = W.get((ebene, rid, f"bonn-sda-{iid}", jahr)) or {}
        ist = float(r["wert"]) if r.get("wert") else None
        gleich = ist is not None and gegen is not None and abs(ist - gegen) <= toleranz
        gerundet = (not gleich and ist is not None and gegen is not None and stellen is not None
                    and round(ist, stellen) == round(gegen, stellen))
        audit.append({"nr": len(audit) + 1, "raumebene": ebene, "raum_id": rid, "indikator_id": f"bonn-sda-{iid}",
                      "jahr": jahr, "wert_ratsatlas": r.get("wert", ""), "status_ratsatlas": r.get("status", ""),
                      "wert_gegenquelle": "" if gegen is None else _wert(round(gegen, 3)), "gegenquelle": url,
                      "fundstelle": fundstelle,
                      "ergebnis": "gleich" if gleich else "gleich (gerundet)" if gerundet else "abweichend",
                      "bemerkung": f"Gegenquelle mit {stellen} Nachkommastellen" if gerundet else ""})

    bewohnt = [b for b in namen if b not in UNBEWOHNT and b != "127"]
    # A: vier Bezirke × zwei Kennzahlen aus dem Bezirksblatt 2025
    for b in rnd.sample(bewohnt, 4):
        name = f"{b} {namen[b]}.pdf"
        for k in rnd.sample(sorted(BLATT), 2):
            zeile("statistischer_bezirk", b, k, "2025", blattwerte(pdf(name), k)["wert"], ATLAS + name,
                  f"Bezirksblatt, Zeile „{BLATT[k][0].strip()}“, Spalte {'Anteil' if BLATT[k][1] == 'anteil' else 'Wert'}")
    # B: Jahresübersicht 2020 und 2024, je drei Werte
    for jahr in ("2020", "2024"):
        name = f"100100001{jahr}1231.pdf"
        for b, k in [(rnd.choice(bewohnt), rnd.choice(sorted(JAHRESBLATT))) for _ in range(3)]:
            zeile("statistischer_bezirk", b, k, jahr, jahreswert(pdf(name), b, k), ATLAS + name,
                  f"Jahresübersicht „Bevölkerung in Bonn“ {jahr}, Zeile {b}, Spalte {JAHRESBLATT[k] + 1}",
                  stellen=0 if k == "i1" else None)
    # B2: zusammengefasste Bezirke – Zeile der Jahresübersicht 2024 nennt den kleinen Bezirk in Klammern
    name = "10010000120241231.pdf"
    text = pdf(name)
    for klein, gross in sorted(ZUSAMMENGEFASST.items()):
        z = next(z for z in text.splitlines() if re.match(rf"^{gross} ", z))
        gegen = jahreswert(text, gross, "i0") if f"({klein})" in z else None
        zeile("statistischer_bezirk", gross, "i0", "2024", gegen, ATLAS + name,
              f"Jahresübersicht „Bevölkerung in Bonn“ 2024, Zeile „{re.split(r'\s{2,}', z.strip())[0]}“", toleranz=0)
        audit[-1]["bemerkung"] = f"Bezirk {klein} ist in der Quelle in {gross} enthalten"
    # C: abgeleitete Werte für Endenich aus den Bezirksblättern 120 und 121
    t120, t121 = pdf("120 Neu-Endenich.pdf"), pdf("121 Alt-Endenich.pdf")
    ew = blattwerte(t120, "i0")["wert"] + blattwerte(t121, "i0")["wert"]

    def auslaender(t):
        z = next(z for z in t.splitlines() if "11. Ausländer" in z)
        return _zahl(re.findall(r"-?\d[\d.]*(?:,\d+)?", re.split(r"\d{2}\.\d{2}\.\d{4}", z, maxsplit=1)[1])[0])
    zeile("ortsteil", "endenich", "i0", "2025", ew, ATLAS + "120 Neu-Endenich.pdf",
          "Summe der Bezirksblätter 120 und 121, Zeile „1. Bevölkerung“", toleranz=0)
    zeile("ortsteil", "endenich", "i23", "2025", (auslaender(t120) + auslaender(t121)) / ew * 100,
          ATLAS + "121 Alt-Endenich.pdf", "Bezirksblätter 120 und 121, Ausländer (Zeile 11) je Bevölkerung × 100")
    # D: Vergleichswerte Stadtbezirk und ganz Bonn aus einem Bezirksblatt
    b = rnd.choice(bewohnt)
    name = f"{b} {namen[b]}.pdf"
    sid = {v: k for k, v in STADTBEZIRKE.items()}[next(f["filters"][0]["name"] for f in _json(dl / "atlas" / "data.js")["geographies"][0]["features"]
                               if f["id"] == b).removeprefix("Stadtbezirk ")]
    zeile("stadtbezirk", sid, "i0", "2025", blattwerte(pdf(name), "i0")["stadtbezirk"], ATLAS + name,
          "Bezirksblatt, Zeile „1. Bevölkerung“, Spalte Stadtbezirk", toleranz=0)
    zeile("gesamtstadt", "bonn", "i9", "2025", blattwerte(pdf(name), "i9")["stadt"], ATLAS + name,
          "Bezirksblatt, Zeile „12. Durchschnittsalter“, Spalte Stadt Bonn")
    # E: Wegweiser über den CSV-Export (zweiter Abrufweg)
    for fu, kommune, jahr in (("altenquotient", "bonn", "2023"), ("bevoelkerung", "koeln", "2023")):
        url = f"{WW}export/{fu}+{kommune}+{jahr}.csv?charset=UTF-8"
        ziel = dl / "verifikation" / f"{fu}_{kommune}_{jahr}.csv"
        _hole(url, ziel, [], "Verifikation")
        # eine Kommune, ein Jahr: der Export steht quer („Indikator;Wert“)
        z = next(l for l in ziel.read_text(encoding="utf-8").splitlines() if re.search(r";-?\d[\d.]*(?:,\d+)?$", l))
        gegen = _zahl(z.rsplit(";", 1)[1])
        r = G.get((kommune, fu, jahr), {})
        gleich = r and abs(float(r["wert"]) - gegen) <= 0.051
        audit.append({"nr": len(audit) + 1, "raumebene": "gemeinde", "raum_id": kommune, "indikator_id": f"wk-{fu}",
                      "jahr": jahr, "wert_ratsatlas": r.get("wert", ""), "status_ratsatlas": "ok" if r else "",
                      "wert_gegenquelle": _wert(gegen), "gegenquelle": url, "fundstelle": "CSV-Export des Wegweisers",
                      "ergebnis": "gleich" if gleich else "abweichend", "bemerkung": ""})
    felder = ["nr", "raumebene", "raum_id", "indikator_id", "jahr", "wert_ratsatlas", "status_ratsatlas",
              "wert_gegenquelle", "gegenquelle", "fundstelle", "ergebnis", "bemerkung"]
    _tsv(src / VERIFIKATION, felder, audit)
    n = sum(a["ergebnis"].startswith("gleich") for a in audit)
    print(f"Verifikation: {n} von {len(audit)} Werten gleich (davon "
          f"{sum(a['ergebnis'] == 'gleich (gerundet)' for a in audit)} gerundet) → {src / VERIFIKATION}")
    return audit
