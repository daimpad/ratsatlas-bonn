"""Seite teilen/: Bilder zum Ratsatlas Bonn für Beiträge, Präsentationen und die Presse (Entscheidungen des
Auftraggebers 10.11.2026: Mischung aus Grafiken und Bildschirmfotos, Formate für soziale Medien, Präsentation,
Web und Druck, Grafiken zusätzlich als SVG, CC BY 4.0, verlinkt im Menü „Daten“ und im Fuß).

Die Bilder liegen fertig in site/teilen/bilder/ (pipeline/teilen.py, auf Knopfdruck); diese Seite entsteht im Schritt
`seo` aus site/teilen/bilder.json. Fehlt die Datei, entfällt die Seite.
"""
import json
from html import escape

from . import akkordeon, config

PFAD = "teilen/"
MANIFEST = config.ROOT / "site" / "teilen" / "bilder.json"
LIZENZ = "https://creativecommons.org/licenses/by/4.0/deed.de"
NAMEN = {"jpg": "JPG", "webp": "WebP", "png": "PNG", "svg": "SVG", "druck": "Druck"}


def _groesse(b):
    return f"{b / 1e6:.1f} MB".replace(".", ",") if b >= 1e6 else f"{round(b / 1e3)} KB"


def _datum(iso):
    j, m, t = iso.split("-")
    return f"{t}.{m}.{j}"


def _karte(m, formate, druck_breite, root):
    b = f"{root}teilen/bilder/"
    vor = m["dateien"]["vorschau"]
    zeilen = []
    for fmt, f in formate.items():
        dateien = m["dateien"][fmt]
        links = " ".join(
            f'<a class="tl-datei" href="{b}{escape(d["datei"])}" download>{NAMEN[k]}'
            + (f" <small>{druck_breite} px</small>" if k == "druck" else "")
            + f'<span class="tl-groesse">{_groesse(d["bytes"])}</span></a>'
            for k, d in sorted(dateien.items(), key=lambda kv: list(NAMEN).index(kv[0])))
        zeilen.append(f'<tr><th scope="row">{escape(f["name"])}<small>{f["w"]} × {f["h"]} px · {escape(f["zweck"])}</small>'
                      f'</th><td>{links}</td></tr>')
    osm = ' Mit Karte: zusätzlich „© OpenStreetMap-Mitwirkende“.' if m["osm"] else ""
    return f"""    <article class="tl-motiv" id="{escape(m["key"])}">
      <a class="tl-bild" href="{b}{escape(vor["jpg"]["datei"])}"><picture><source srcset="{b}{escape(vor["webp"]["datei"])}" type="image/webp"><img src="{b}{escape(vor["jpg"]["datei"])}" width="1200" height="630" loading="lazy" alt="{escape(m["titel"])}: {escape(m["text"])}"></picture></a>
      <div class="tl-text">
        <h2>{escape(m["titel"])}</h2>
        <p>{escape(m["text"])}</p>
        <details class="tl-formate">
          <summary>Formate und Dateien</summary>
          <table class="tl-tabelle"><tbody>{"".join(zeilen)}</tbody></table>
          <p class="meta">Nennung: „Ratsatlas Bonn (bonn.ratsatlas.de)“, CC BY 4.0.{osm}</p>
        </details>
      </div>
    </article>"""


def body(root):
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    karten = "\n".join(_karte(x, m["formate"], m["druck_breite"], root) for x in m["motive"])
    formate = ", ".join(f'{f["name"]} ({f["w"]} × {f["h"]})' for f in m["formate"].values())
    return f"""    <div class="tl-kopf">
      <h1>Teilen</h1>
      <p class="lead">Bilder zum Ratsatlas Bonn für Beiträge, Präsentationen und die Presse. Frei nutzbar mit Nennung „Ratsatlas Bonn“ (<a href="{LIZENZ}">CC BY 4.0</a>).</p>
    </div>
    <div class="tl-raster">
{karten}
    </div>
{akkordeon.mehr("Nutzung, Formate und Quellen", f'<p>Die Bilder stehen unter der Lizenz <a href="{LIZENZ}">CC BY 4.0</a>. Bitte nennen Sie „Ratsatlas Bonn (bonn.ratsatlas.de)“; bei Motiven mit Karte oder Orten zusätzlich „© OpenStreetMap-Mitwirkende“ (ODbL). Die Logos dürfen nicht verändert werden.</p><p>Formate: {formate}; Breitbild, Quadrat und Hochformat auch in {m["druck_breite"]} px Breite für den Druck. JPG und WebP für alle Motive, SVG für die Grafiken, PNG für die Wortmarke.</p><p>Grafiken aus den Daten des Ratsatlas: Orte der Vorlagen (verortet aus OParl-API der Stadt Bonn, Geodaten der Stadt Bonn und OpenStreetMap), Haushaltspläne der Stadt Bonn, Prozesslinie der Drucksache 252458. Bildschirmfotos der Seite. Stand der Bilder: {_datum(m["stand"])}.</p>')}"""


def write(site, site_url, page):
    """Schreibt teilen/index.html, wenn die Bilder vorliegen; gibt den Pfad für die Sitemap zurück."""
    if not MANIFEST.exists():
        return []
    out = site / PFAD / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(site_url, PFAD, "Teilen – Bilder zum Ratsatlas Bonn",
                        "Bilder zum Ratsatlas Bonn in verschiedenen Formaten für soziale Medien, Präsentationen, "
                        "Websites und Druck; frei nutzbar unter CC BY 4.0.", body("../"), "../"), encoding="utf-8")
    return [PFAD]
