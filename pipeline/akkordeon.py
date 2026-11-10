"""Eingeklappte Akkordeons für Metaangaben auf den statischen Seiten: Quellen, Lizenzen, Regeln, Methode, Grenzen.

Entscheidung des Auftraggebers 10.11.2026: Metaangaben sind weniger wichtig als der Inhalt und stehen daher
eingeklappt; kurze Markierungen „abgeleitet“ direkt an einzelnen Werten bleiben sichtbar (Projektauftrag 5.4).
Gestaltung wie die Akkordeons der Haushaltsseite (`hh-mehr`, site/page.css).
"""


def mehr(titel, inhalt, einzug="    ", klasse="hh-mehr meta-acc"):
    """<details> mit Überschrift titel (HTML) und Inhalt (HTML, ein oder mehrere Absätze)."""
    return (f'{einzug}<details class="{klasse}">\n{einzug}  <summary>{titel}</summary>\n'
            f'{einzug}  {inhalt}\n{einzug}</details>\n')


def absatz(text):
    return f"<p>{text}</p>"
