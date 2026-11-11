"""IndexNow: meldet neue, geänderte und entfernte Seiten von bonn.ratsatlas.de an Suchmaschinen (Bing, über Bing auch
DuckDuckGo und Ecosia; nicht Google). Entscheidungen des Auftraggebers 11.11.2026: eigener Job nach dem Schreiben des
Branch deploy (GitHub Pages wartet nicht darauf), auch der tägliche Lauf meldet, einmalig alle Seiten auf Knopfdruck.

Gemeldet werden nur Adressen aus den Sitemaps (sitemap-seiten.xml, sitemap-vorgaenge.xml): geänderte und neue
HTML-Dateien aus dem Unterschied zwischen dem neuen Stand von deploy und dem vorigen, entfernte, wenn sie in den
Sitemaps des vorigen Standes standen. Die Ausgaben sind stabil (keine Erzeugungszeitpunkte), der Unterschied zeigt also
nur Inhaltsänderungen. Gemeldet wird erst, wenn die Hauptadresse den neuen Stand zeigt (generated_at in index.json wie
im Branch), höchstens 10 Minuten Warten. Fehler bei IndexNow sind Warnungen; der Lauf scheitert nicht daran.

Umgebung: DEPLOY_DIR (Klon von deploy mit mindestens zwei Ständen, Vorgabe _deploy), INDEXNOW_ALLE=true (alle Adressen
der Sitemaps), INDEXNOW_TROCKEN=true (nur anzeigen)."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config

SCHLUESSEL = "e94784e5ae0daf9c2731db3a9f693ece"   # Datei site/<SCHLUESSEL>.txt mit demselben Inhalt
ENDPUNKT = "https://api.indexnow.org/indexnow"
PAKET = 10_000          # höchstens 10.000 Adressen je Anfrage (IndexNow)
SITEMAPS = ("sitemap-seiten.xml", "sitemap-vorgaenge.xml")
INDEX = "data/export/bonn/index.json"
WARTEN = 600            # Sekunden bis zur Übernahme durch die Hauptadresse
TAKT = 20


def adresse(datei, site_url):
    """HTML-Datei im Branch deploy → öffentliche Adresse (index.html → Verzeichnis)."""
    if datei == "index.html":
        return site_url
    if datei.endswith("/index.html"):
        return site_url + datei[:-len("index.html")]
    return site_url + datei


def sitemap_adressen(texte):
    """Alle <loc> aus den Texten der Sitemaps."""
    return {m for t in texte for m in re.findall(r"<loc>([^<]+)</loc>", t or "")}


def auswahl(aenderungen, neu, alt, site_url):
    """aenderungen: [(Status, Datei)] aus git diff --name-status. Neue und geänderte Seiten zählen, wenn sie in den
    neuen Sitemaps stehen, entfernte, wenn sie in den alten standen. Sortiert, ohne Doppelte."""
    out = set()
    for status, datei in aenderungen:
        if not datei.endswith(".html"):
            continue
        url = adresse(datei, site_url)
        if status.startswith("D"):
            if url in alt:
                out.add(url)
        elif url in neu:
            out.add(url)
    return sorted(out)


def pakete(urls, groesse=PAKET):
    return [urls[i:i + groesse] for i in range(0, len(urls), groesse)]


def _git(ordner, *args):
    return subprocess.run(["git", "-C", str(ordner), *args], check=True, capture_output=True, text=True).stdout


def _aenderungen(ordner):
    zeilen = _git(ordner, "diff", "--no-renames", "--name-status", "HEAD~1", "HEAD").splitlines()
    return [tuple(z.split("\t", 1)) for z in zeilen if "\t" in z]


def _alte_sitemaps(ordner):
    texte = []
    for s in SITEMAPS:
        try:
            texte.append(_git(ordner, "show", f"HEAD~1:{s}"))
        except subprocess.CalledProcessError:
            texte.append("")
    return texte


def _generated_at(text):
    return json.loads(text)["meta"]["generated_at"]


def warte_auf_stand(ordner, site_url, warten=WARTEN, takt=TAKT):
    """True, sobald die Hauptadresse das generated_at des Branch zeigt."""
    soll = _generated_at((Path(ordner) / INDEX).read_text(encoding="utf-8"))
    ende = time.time() + warten
    while True:
        try:
            with urllib.request.urlopen(f"{site_url}{INDEX}?indexnow={int(time.time())}", timeout=30) as r:
                ist = _generated_at(r.read().decode("utf-8"))
            if ist == soll:
                return True
        except (OSError, ValueError, KeyError):
            ist = None
        if time.time() >= ende:
            print(f"::warning::IndexNow: {site_url} zeigt nach {warten // 60} Minuten den Stand {ist}, der Branch deploy "
                  f"{soll}; keine Meldung")
            return False
        time.sleep(takt)


def melden(urls, site_url):
    host = re.sub(r"^https?://", "", site_url).strip("/")
    for teil in pakete(urls):
        daten = json.dumps({"host": host, "key": SCHLUESSEL, "keyLocation": f"{site_url}{SCHLUESSEL}.txt",
                            "urlList": teil}).encode("utf-8")
        anfrage = urllib.request.Request(ENDPUNKT, data=daten, method="POST",
                                         headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as r:
                print(f"IndexNow: {r.status} – {len(teil)} Adresse(n) gemeldet")
        except urllib.error.HTTPError as e:
            print(f"::warning::IndexNow antwortete mit {e.code} für {len(teil)} Adresse(n): {e.read()[:200]!r}")
        except OSError as e:
            print(f"::warning::IndexNow nicht erreichbar: {e}")


def schritt():
    ordner = Path(os.environ.get("DEPLOY_DIR", "_deploy"))
    site_url = config.SITE_URL
    alle = os.environ.get("INDEXNOW_ALLE") == "true"
    trocken = os.environ.get("INDEXNOW_TROCKEN") == "true"
    neu = sitemap_adressen((ordner / s).read_text(encoding="utf-8") if (ordner / s).exists() else "" for s in SITEMAPS)
    if alle:
        urls = sorted(neu)
    else:
        try:
            urls = auswahl(_aenderungen(ordner), neu, sitemap_adressen(_alte_sitemaps(ordner)), site_url)
        except subprocess.CalledProcessError as e:
            print(f"::warning::IndexNow: kein vorheriger Stand im Branch deploy ({e.stderr.strip()}); keine Meldung")
            return
    print(f"IndexNow: {len(urls)} Adresse(n){' (alle aus den Sitemaps)' if alle else ''}")
    for u in urls[:20]:
        print("  " + u)
    if len(urls) > 20:
        print(f"  … und {len(urls) - 20} weitere")
    if not urls or trocken:
        return
    if warte_auf_stand(ordner, site_url):
        melden(urls, site_url)


if __name__ == "__main__":
    schritt()
    sys.exit(0)
