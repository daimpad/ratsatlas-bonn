"""Einzelmaßnahmen aus Teilfinanzplan B der Haushaltspläne (Option 7, haushalt/phase0/EINZELMASSNAHMEN.md).

Entscheidungen des Auftraggebers 10.11.2026: Liste auf haushalt/ je Produktgruppe und auf den Themenseiten (ohne
Karte); nur Maßnahmen mit Ansatz 2025 oder 2026 (Haushaltsplan 2025/2026, ohne Vergleich mit 2023/2024); Spalten
Ansatz 2025, Ansatz 2026 und Gesamt; ohne Verpflichtungsermächtigungen und Planung; Posten zu Verträgen mit
Einzelpersonen („Leibrente“, „Intendantenvertrag“) nur in der Summe der Produktgruppe; Abkürzungen nur mit Fundstelle
erklären. Anzeige erst nach Prüfung des Prüfbogens (FREIGEGEBEN).

Schritt `haushalt-massnahmen` (einmalig, lokal, braucht pdftotext -bbox): liest aus den 17 PDF der Produktbereiche
(SHA-256 laut data/haushalt/STAND.json; lokal über HAUSHALT_PDF) jede Seite „Teil B: Investitionseinzelmaßnahmen“.
Ein Block je Maßnahme: Bezeichnung links bündig, darunter die gefüllten Zeilen mit Nummer, Rechenzeichen und Beträgen.
Die Spalte eines Betrags folgt aus der Mitte der Spaltennummer im Kopf und einer Verschiebung je Block (rechter Rand
der Spalte 12); gesperrte Ziffern werden zusammengefügt.

Geprüft wird über alle Maßnahmen, nicht nur die übernommenen:
- je Zeile: Spalte 12 = Spalten 4, 6, 8–11;
- je Maßnahme und Spalte: Zeile 12 = Einzahlungen (1–4) − Auszahlungen (6–10), ohne Zeile 12 beide gleich;
- je Produktgruppe, Zeile und Spalte 1–4 und 6: Summe der Maßnahmen = Teilfinanzplan A (investitionen.tsv) mit der
  Zuordnung der Zeilen B → A (1→1, 2→2, 3→4, 4→5, 6→7, 7→8, 8→9, 9→11, 10→12, 12→14 ohne Finanzanlagen).
Bricht ab, wenn etwas nicht aufgeht, außer an den Stellen in AUSNAHMEN (je mit Beleg).

Ergebnis: data/haushalt/massnahmen.tsv (je Maßnahme und Zeile die Spalten 4, 6 und 12) und ein Vermerk in STAND.json.
Die PDF kommen nicht ins Repository.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config, haushaltsplan as hp

AUSGABE = "2025/2026"
TSV = hp.ORDNER / "massnahmen.tsv"
KOPF = ["ausgabe", "produktbereich", "produktgruppe", "pg_name", "position", "bezeichnung", "zeile", "zeile_name",
        "spalte", "jahr", "art", "betrag", "datei", "seite", "vermerk"]
FREIGEGEBEN = True    # Prüfbogen im Gespräch freigegeben am 10.11.2026 (haushalt/PHASE7.md)
PRUEFBOGEN = config.EXPORT / "haushalt" / "pruefbogen_haushalt_massnahmen.tsv"
TOLERANZ = 2          # Euro (Rundung im PDF; Phase 0: Abweichungen von 1–2 € in 17 Zeilen)

ZEILEN = {1: "Einzahlungen aus Investitionszuwendungen", 2: "Einzahlungen aus der Veräußerung von Sachanlagen",
          3: "Einzahlungen aus Beiträgen u. ä. Entgelten", 4: "Sonstige Investitionseinzahlungen",
          6: "Auszahlungen für den Erwerb von Grundstücken und Gebäuden", 7: "Auszahlungen für Baumaßnahmen",
          8: "Auszahlungen für den Erwerb von beweglichem Anlagevermögen",
          9: "Auszahlungen von aktivierbaren Zuwendungen", 10: "Sonstige Investitionsauszahlungen",
          12: "Saldo der Investitionseinzelmaßnahme"}
EINZAHLUNG, AUSZAHLUNG = (1, 2, 3, 4), (6, 7, 8, 9, 10)
B_ZU_A = {1: 1, 2: 2, 3: 4, 4: 5, 6: 7, 7: 8, 8: 9, 9: 11, 10: 12}
# Spalten des Teils B im Haushaltsplan 2025/2026 (Kopf der Seiten, geprüft beim Lesen über die Jahreszahlen)
SPALTEN = {1: ("Ergebnis", 2022), 2: ("Ergebnis", 2023), 3: ("Ansatz", 2024), 4: ("Ansatz", 2025), 5: ("VE", 2025),
           6: ("Ansatz", 2026), 7: ("VE", 2026), 8: ("Planung", 2027), 9: ("Planung", 2028), 10: ("Planung", 2029),
           11: ("bisher bereitgestellt", None), 12: ("Gesamt", None)}
JAHRE_IM_KOPF = {"2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029"}
UEBERNOMMEN = (4, 6, 12)   # Ansatz 2025, Ansatz 2026, Gesamt (Entscheidung 10.11.2026)
MIT_ANSATZ = (4, 6)
# Posten zu Verträgen mit Einzelpersonen: nie einzeln, nur in der Summe der Produktgruppe (Entscheidung 10.11.2026)
NUR_SUMME = re.compile(r"Leibrente|Intendantenvertrag", re.I)

# Stellen, an denen das PDF selbst vom Aufbau abweicht (Phase 0, EINZELMASSNAHMEN.md Abschnitt 2):
# (Datei, Seite, Position des Blocks auf der Seite) → Regel
AUSNAHMEN = {
    # zwei Bezeichnungen übereinander über dem ersten Block, der zweite Block ohne Bezeichnung; Zuordnung über
    # 2023/2024 (pb12.pdf S. 18: „Mondorfer Str. BN“ mit Ansatz 2024 500.000 €), abgeleitet
    ("PB12.pdf", 18, 4): {"bezeichnung": "Auerberger-Mitte BN",
                          "vermerk": "Bezeichnung abgeleitet (im PDF über dem vorigen Block; Beleg Haushaltsplan "
                                     "2023/2024, pb12.pdf S. 18)"},
    # Saldozeile mit abgetrennten Rechenzeichen und Ziffern: Saldo aus den übrigen Zeilen nachgerechnet
    ("PB02.pdf", 42, 3): {"saldo_nachrechnen": True, "vermerk": "Saldo nachgerechnet (Saldozeile im PDF getrennt)"},
    # Block ohne Bezeichnung mit gesperrten Ziffern, nur Planungsjahre; Spalten unsicher, ohne Ansatz (nicht übernommen)
    ("PB12.pdf", 48, 3): {"ohne_bezeichnung": True, "spalten_unsicher": True,
                             "vermerk": "Block ohne Bezeichnung, Spalten unsicher (nur Planung, nicht übernommen)"},
}
# Bezeichnungen ohne eigenen Block (die nächste Bezeichnung folgt direkt); nur hier zulässig
OHNE_BLOCK = {("PB12.pdf", 13, "Effertzstr. BN"), ("PB12.pdf", 18, "Auerberger-Mitte BN")}

ZAHL = re.compile(r"-?\d{1,3}(?:\.\d{3})*")
STUECK = re.compile(r"-?[\d.]+")


def _zeilen(ws, tol=1.6):
    """Wörter nach der Oberkante zu Zeilen: [(y, [Wörter nach x])]."""
    out = []
    for w in sorted(ws, key=lambda w: (w[1], w[0])):
        if out and abs(out[-1][0] - w[1]) <= tol:
            out[-1][1].append(w)
        else:
            out.append([w[1], [w]])
    return [(y, sorted(z, key=lambda w: w[0])) for y, z in out]


def ist_teil_b(ws):
    return any(w[4] == "Investitionseinzelmaßnahmen" for w in ws)


def _kopf(ws, datei, seite):
    """y der Zeile mit den Spaltennummern 1–12 und die Mitte jeder Nummer; prüft die Jahre im Kopf."""
    for y, z in _zeilen([w for w in ws if w[1] < 260]):
        t = [w[4] for w in z]
        if t == [str(i) for i in range(1, 13)]:
            jahre = {w[4] for w in ws if w[1] < y and re.fullmatch(r"20\d\d", w[4])}
            if not JAHRE_IM_KOPF <= jahre:   # weitere Jahre stehen teils in der Bezeichnung der Produktgruppe
                raise ValueError(f"{datei} S. {seite}: Jahre im Kopf {sorted(jahre)} ohne {sorted(JAHRE_IM_KOPF - jahre)}")
            return y, {int(w[4]): (w[0] + w[2]) / 2 for w in z}
    raise ValueError(f"{datei} S. {seite}: Zeile mit den Spaltennummern 1–12 nicht gefunden")


def seite_lesen(ws, datei, seite):
    """Blöcke einer Seite des Teils B: [{"bezeichnung", "position", "zeilen": {Nr: {Spalte: Betrag}}, "vermerk"}].
    Wendet AUSNAHMEN an; bricht ab, wenn ein Block nicht eindeutig zu lesen ist."""
    y_kopf, mitten = _kopf(ws, datei, seite)
    rechts = {k: c + 20.5 for k, c in mitten.items()}   # rechter Rand eines Betrags (Phase 0: Abstand 20–21 pt)
    links = min(w[0] for w in ws if w[1] > y_kopf + 4)
    bloecke, offen, namen = [], None, []
    for y, z in _zeilen([w for w in ws if y_kopf + 4 < w[1] < 570]):
        erstes = z[0]
        if re.fullmatch(r"\d{1,2}", erstes[4]) and erstes[0] < links + 12 and erstes[2] < 80 \
                and int(erstes[4]) in ZEILEN:
            nr = int(erstes[4])
            if offen is None or namen or offen["zu"] or nr <= max(offen["roh"], default=0):
                if namen:   # Bezeichnungen ohne eigenen Block (nur die zulässigen) fallen weg
                    for n in namen[:-1]:
                        if (datei, seite, n) not in OHNE_BLOCK:
                            raise ValueError(f"{datei} S. {seite}: Bezeichnung „{n}“ ohne Zeilen")
                offen = {"bezeichnung": namen[-1] if namen else None, "roh": {}, "zu": False, "y": y}
                bloecke.append(offen)
                namen = []
            rest = z[1:]
            zeichen = rest[0][4] if rest and rest[0][4] in "+-=" else ""
            offen["roh"][nr] = {"zeichen": zeichen, "y": y,
                                "zahlen": [w for w in rest if STUECK.fullmatch(w[4]) and w[0] > 190]}
            offen["zu"] = nr == 12
            continue
        text = [w for w in z if w[0] < 200 and not STUECK.fullmatch(w[4])]
        zahlen = [w for w in z if w[0] > 190 and STUECK.fullmatch(w[4])]
        if text and text[0][0] < links + 12:   # Bezeichnung einer Maßnahme (links bündig, ohne Nummer)
            if offen is not None and not offen["zu"]:
                offen["zu"] = True   # Maßnahme ohne Zeile 12 (Einzahlungen = Auszahlungen)
            namen.append(" ".join(w[4] for w in z if w[0] < 200))
            if zahlen:
                raise ValueError(f"{datei} S. {seite}: Beträge in der Zeile einer Bezeichnung")
        elif zahlen:
            if offen is None:
                raise ValueError(f"{datei} S. {seite}: Beträge vor dem ersten Block")
            nr = min(offen["roh"], key=lambda n: abs(offen["roh"][n]["y"] - y))
            if abs(offen["roh"][nr]["y"] - y) > 9:
                raise ValueError(f"{datei} S. {seite}: Beträge ohne Zeile ({' '.join(w[4] for w in zahlen)})")
            offen["roh"][nr]["zahlen"] += zahlen
    if namen:
        for n in namen:
            if (datei, seite, n) not in OHNE_BLOCK:
                raise ValueError(f"{datei} S. {seite}: Bezeichnung „{n}“ am Seitenende ohne Zeilen")
    out = []
    for pos, b in enumerate(bloecke, 1):
        regel = AUSNAHMEN.get((datei, seite, pos), {})
        alle = [w for r in b["roh"].values() for w in r["zahlen"]]
        # Verschiebung je Block: der Betrag am weitesten rechts steht in Spalte 12 (Gesamt; die Saldozeile druckt alle
        # Spalten). Größer als 12 pt hieße: Spalte 12 fehlt oder der Block ist anders gesetzt (Phase 0: höchstens 9 pt)
        versatz = max(w[2] for w in alle) - rechts[12] if alle else 0
        if abs(versatz) > 12 and not regel.get("spalten_unsicher"):
            raise ValueError(f"{datei} S. {seite}, Block {pos}: Verschiebung {versatz:.1f} pt (Spalte 12 leer?)")
        zeilen, unsicher = {}, False
        for nr, r in b["roh"].items():
            stuecke = []
            for w in sorted(r["zahlen"], key=lambda w: w[0]):   # gesperrte Ziffern zusammenfügen
                if stuecke and w[0] - stuecke[-1][2] < 2.5:
                    s = stuecke[-1]
                    stuecke[-1] = (s[0], s[1], w[2], w[3], s[4] + w[4])
                else:
                    stuecke.append(w)
            werte = {}
            for w in stuecke:
                if not ZAHL.fullmatch(w[4]):
                    if nr == 12 and regel.get("saldo_nachrechnen"):
                        continue
                    raise ValueError(f"{datei} S. {seite}, Block {pos}, Zeile {nr}: Zahl „{w[4]}“ unlesbar")
                k = min(rechts, key=lambda k: abs(rechts[k] + versatz - w[2]))
                if abs(rechts[k] + versatz - w[2]) > 14:
                    unsicher = True
                if k in werte:
                    raise ValueError(f"{datei} S. {seite}, Block {pos}, Zeile {nr}: zwei Beträge in Spalte {k}")
                werte[k] = int(w[4].replace(".", ""))
            zeilen[nr] = werte
        if unsicher and not regel.get("spalten_unsicher"):
            raise ValueError(f"{datei} S. {seite}, Block {pos}: Spalte eines Betrags unsicher")
        if regel.get("saldo_nachrechnen"):
            zeilen[12] = {k: sum(zeilen.get(n, {}).get(k, 0) for n in EINZAHLUNG)
                          - sum(zeilen.get(n, {}).get(k, 0) for n in AUSZAHLUNG) for k in range(1, 13)}
        bezeichnung = regel.get("bezeichnung") or b["bezeichnung"]
        if bezeichnung is None and not regel.get("ohne_bezeichnung"):
            raise ValueError(f"{datei} S. {seite}, Block {pos}: ohne Bezeichnung")
        out.append({"bezeichnung": bezeichnung or "", "position": pos, "zeilen": zeilen,
                    "vermerk": regel.get("vermerk", ""), "spalten_unsicher": unsicher or bool(regel.get("spalten_unsicher"))})
    return out


def lesen(pdfs, st):
    """Alle Maßnahmen einer Ausgabe; pdfs {PB: Wortlisten je Seite}. [{PB, PG, PG-Name, Datei, Seite, …Block}]."""
    massnahmen = []
    for pb, seiten in sorted(pdfs.items()):
        datei = Path(st["dateien"][pb]["url"]).name
        for s, ws in enumerate(seiten, 1):
            if not ist_teil_b(ws):
                continue
            pb_, pg, name, _ = hp.kopf(ws)
            if pb_ != pb or not pg or not pg.startswith(f"1.{pb}."):
                raise ValueError(f"{datei} S. {s}: Kopf nennt {pb_} / {pg}")
            for m in seite_lesen(ws, datei, s):
                massnahmen.append({"produktbereich": pb, "produktgruppe": pg, "pg_name": name, "datei": datei,
                                   "seite": s, **m})
    return massnahmen


def pruefen(massnahmen, teil_a):
    """Prüfsummen (siehe Modulkopf); teil_a {(PG, Zeile A, Spalte): Betrag} aus investitionen.tsv. Gibt
    {Prüfung: (Zahl der Prüfungen, größte Abweichung)} zurück; bricht bei Abweichung über TOLERANZ ab."""
    out = {}
    n = groesste = 0
    for m in massnahmen:
        if m["spalten_unsicher"]:
            continue
        for nr, w in m["zeilen"].items():
            if 12 in w or any(k in w for k in (4, 6, 8, 9, 10, 11)):
                a = w.get(12, 0) - sum(w.get(k, 0) for k in (4, 6, 8, 9, 10, 11))
                if abs(a) > TOLERANZ:
                    raise ValueError(f"{m['datei']} S. {m['seite']} „{m['bezeichnung']}“ Zeile {nr}: Spalte 12 weicht "
                                     f"um {a} € ab")
                n, groesste = n + 1, max(groesste, abs(a))
    out["spalte_12_je_zeile"] = (n, groesste)
    n = groesste = 0
    for m in massnahmen:
        if m["spalten_unsicher"]:
            continue
        z = m["zeilen"]
        for k in range(1, 13):
            soll = sum(z.get(r, {}).get(k, 0) for r in EINZAHLUNG) - sum(z.get(r, {}).get(k, 0) for r in AUSZAHLUNG)
            a = z.get(12, {}).get(k, 0) - soll
            if abs(a) > TOLERANZ:
                raise ValueError(f"{m['datei']} S. {m['seite']} „{m['bezeichnung']}“ Spalte {k}: Saldo weicht um {a} € ab")
            n, groesste = n + 1, max(groesste, abs(a))
    out["saldo_je_massnahme"] = (n, groesste)
    summe = defaultdict(int)
    for m in massnahmen:
        for nr, w in m["zeilen"].items():
            if nr in B_ZU_A:
                for k in (1, 2, 3, 4, 6):
                    summe[(m["produktgruppe"], B_ZU_A[nr], k)] += w.get(k, 0)
    n = groesste = 0
    for key in set(summe) | {k for k in teil_a if k[1] in B_ZU_A.values()}:
        a = summe.get(key, 0) - teil_a.get(key, 0)
        if abs(a) > TOLERANZ:
            raise ValueError(f"Produktgruppe {key[0]}, Teil A Zeile {key[1]}, Spalte {key[2]}: Summe der Maßnahmen "
                             f"weicht um {a} € ab")
        n, groesste = n + 1, max(groesste, abs(a))
    out["produktgruppen_teil_a"] = (n, groesste)
    return out


def _teil_a():
    """{(PG, Zeile, Spalte): Betrag} der Ausgabe 2025/2026 aus investitionen.tsv (nur Produktgruppen)."""
    out = {}
    for r in hp.lesen(hp.INVESTITIONEN_TSV):
        if r["ausgabe"] == AUSGABE and r["ebene"] == "Produktgruppe":
            art, jahr = r["art"], int(r["jahr"])
            k = next((k for k, (a, j) in SPALTEN.items() if a == art and j == jahr), None)
            if k is not None:
                out[(r["produktgruppe"], int(r["zeile"]), k)] = int(r["betrag"])
    return out


def zeilen_tsv(massnahmen):
    """TSV-Zeilen der übernommenen Maßnahmen (Ansatz 2025 oder 2026 ungleich 0, ohne NUR_SUMME)."""
    rows, weg = [], 0
    for m in massnahmen:
        if not any(w.get(k, 0) for w in m["zeilen"].values() for k in MIT_ANSATZ):
            continue
        if NUR_SUMME.search(m["bezeichnung"]):
            weg += 1
            continue
        for nr in sorted(m["zeilen"]):
            for k in UEBERNOMMEN:
                art, jahr = SPALTEN[k]
                rows.append({"ausgabe": AUSGABE, "produktbereich": m["produktbereich"],
                             "produktgruppe": m["produktgruppe"], "pg_name": m["pg_name"], "position": m["position"],
                             "bezeichnung": m["bezeichnung"], "zeile": nr, "zeile_name": ZEILEN[nr], "spalte": k,
                             "jahr": jahr or "", "art": art, "betrag": m["zeilen"][nr].get(k, 0),
                             "datei": m["datei"], "seite": m["seite"], "vermerk": m["vermerk"]})
    return rows, weg


def ausschnitt():
    """Pipeline-Schritt `haushalt-massnahmen` (einmalig, lokal): data/haushalt/massnahmen.tsv und Vermerk in
    STAND.json. Übernimmt nur, wenn alle 17 PDF lesbar sind und alle Prüfsummen aufgehen."""
    stand = json.loads(hp.STAND.read_text(encoding="utf-8"))
    st = stand["ausgaben"][AUSGABE]
    pdfs = {pb: hp._seiten(hp._pdf(st["dateien"][pb]["url"], st["dateien"][pb]["sha256"]))
            for pb in (f"{i:02d}" for i in range(1, 18))}
    massnahmen = lesen(pdfs, st)
    pruefung = pruefen(massnahmen, _teil_a())
    rows, weg = zeilen_tsv(massnahmen)
    hp._schreiben(TSV, KOPF, rows)
    uebernommen = {(r["produktgruppe"], r["seite"], r["position"]) for r in rows}
    stand["massnahmen"] = {
        "abruf": datetime.now(timezone.utc).date().isoformat(), "ausgabe": AUSGABE,
        "dateien": {pb: {"url": st["dateien"][pb]["url"], "sha256": st["dateien"][pb]["sha256"]} for pb in pdfs},
        "gelesen": len(massnahmen), "uebernommen": len(uebernommen), "nur_in_der_summe": weg,
        "regel": "nur Maßnahmen mit Ansatz 2025 oder 2026; Spalten Ansatz 2025, Ansatz 2026, Gesamt; ohne VE und "
                 "Planung; Leibrenten und Intendantenvertrag nur in der Summe (Entscheidungen 10.11.2026)",
        "pruefsummen": {k: {"pruefungen": n, "groesste_abweichung_euro": a} for k, (n, a) in pruefung.items()},
        "toleranz_euro": TOLERANZ,
        "ausnahmen": [f"{d} S. {s}" + (f", Block {p}" if p else "") + f": {r['vermerk']}"
                      for (d, s, p), r in sorted(AUSNAHMEN.items(), key=lambda x: (x[0][0], x[0][1]))]
                     + [f"{d} S. {s}: Bezeichnung „{n}“ ohne eigene Zeilen" for d, s, n in sorted(OHNE_BLOCK)]}
    hp.STAND.write_text(json.dumps(stand, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Einzelmaßnahmen {AUSGABE}: {len(massnahmen)} gelesen, {len(uebernommen)} übernommen, {weg} nur in der "
          f"Summe; Prüfsummen " + ", ".join(f"{k} {n} bis {a} €" for k, (n, a) in pruefung.items()) + f" → {TSV}")


def _wie_im_pdf(b):
    return ("-" if b < 0 else "") + f"{abs(b):,}".replace(",", ".")


def zweiter_leseweg(layout, bezeichnung, nr, spalte):
    """Betrag aus dem Text mit Layout (pdftotext -layout) derselben Seite, unabhängig von den Wortkoordinaten: Zeile
    der Bezeichnung, darunter die Zeile mit der Nummer; die Spalte folgt aus dem Zeichen, an dem die Spaltennummer im
    Kopf endet (Beträge rechtsbündig). Gibt den Betrag, 0 für eine leere Zelle oder None (nicht gefunden) zurück."""
    zl = layout.split("\n")
    kopf = next((z for z in zl if re.fullmatch(r"\s*" + r"\s+".join(str(i) for i in range(1, 13)) + r"\s*", z)), None)
    if kopf is None:
        return None
    enden = {int(m.group()): m.end() for m in re.finditer(r"\d+", kopf)}
    start = next((i for i, z in enumerate(zl) if z.strip() == bezeichnung), None)
    if start is None:
        return None
    for i in range(start + 1, len(zl)):
        if i > start + 1 and zl[i].strip() and not zl[i].startswith(" ") and not re.match(r"\d", zl[i]):
            return None   # nächste Bezeichnung
        if re.match(rf"{nr}\s", zl[i]):
            werte = {}
            for z in zl[max(i - 1, 0):i + 2]:   # Beträge stehen teils eine Zeile höher oder tiefer
                for m in re.finditer(r"-?\d{1,3}(?:\.\d{3})+|-?\d+(?=\s|$)", z):
                    if m.start() < 40:
                        continue
                    # rechtsbündig: Ende des Betrags wenige Zeichen rechts vom Ende der Spaltennummer
                    nah = [k for k in enden if -2 <= m.end() - enden[k] < 12]
                    if not nah:
                        continue
                    k = min(nah, key=lambda k: m.end() - enden[k])
                    if z is zl[i] or k not in werte:
                        werte[k] = int(m.group().replace(".", ""))
            return werte.get(spalte, 0)
    return None


def pruefbogen(pdf_ordner=None):
    """Pipeline-Schritt `haushalt-pruefbogen-massnahmen` (einmalig): etwa 30 Zellen aus massnahmen.tsv zur Prüfung von
    Hand gegen das PDF, mit Link auf die Seite und dem Ergebnis eines zweiten Lesewegs (pdftotext -layout). Darunter
    die Sonderfälle (abgeleitete Bezeichnung, nachgerechneter Saldo, Einzahlungen, negative Werte, gekürzte und
    doppelte Bezeichnungen, größte und kleinste Ansätze) und eine Stichprobe über alle Produktbereiche mit Maßnahmen.
    Wird nicht überschrieben."""
    import csv
    import random
    import subprocess
    import tempfile
    if PRUEFBOGEN.exists():
        print(f"Prüfbogen besteht bereits: {PRUEFBOGEN}")
        return
    stand = json.loads(hp.STAND.read_text(encoding="utf-8"))
    rows = hp.lesen(TSV)
    zelle = {(r["produktgruppe"], int(r["seite"]), int(r["position"]), int(r["zeile"]), int(r["spalte"])): r
             for r in rows}
    b = lambda k: int(zelle[k]["betrag"])
    auswahl = defaultdict(list)
    def nimm(k, grund):
        auswahl[k].append(grund)
    ansatz = [k for k in zelle if k[4] in MIT_ANSATZ and k[3] != 12 and b(k) != 0]
    for k in sorted(ansatz, key=lambda k: -b(k) if k[3] in AUSZAHLUNG else 0)[:2]:
        nimm(k, "größter Auszahlungsansatz")
    nimm(min((k for k in ansatz if k[3] in AUSZAHLUNG), key=lambda k: (b(k), k)), "kleinster Auszahlungsansatz")
    nimm(max((k for k in zelle if k[4] == 12 and k[3] != 12), key=lambda k: (b(k), k)), "größte Gesamtsumme")
    for k in sorted(k for k in ansatz if k[3] in EINZAHLUNG)[:2]:
        nimm(k, "Einzahlung")
    neg = sorted(k for k in zelle if b(k) < 0 and k[3] != 12)
    if neg:
        nimm(neg[0], "negativer Wert")
    gesehen = set()
    for k in sorted(k for k in zelle if zelle[k]["vermerk"] and k[4] in MIT_ANSATZ and b(k) != 0):
        if k[:3] not in gesehen:   # je Maßnahme mit Ausnahme eine Zelle
            gesehen.add(k[:3])
            nimm(k, "Ausnahme: " + zelle[k]["vermerk"].split(" (")[0])
    saldo = sorted(k for k in zelle if k[3] == 12 and k[4] == 6 and b(k) != 0)
    nimm(saldo[len(saldo) // 2], "Saldo (Zeile 12)")
    lang = sorted(k for k in ansatz if len(zelle[k]["bezeichnung"]) == 40)
    if lang:
        nimm(lang[0], "Bezeichnung mit 40 Zeichen (im PDF gekürzt)")
    namen = defaultdict(set)
    for k, r in zelle.items():
        namen[r["bezeichnung"]].add(k[0])
    doppelt = sorted(k for k in ansatz if len(namen[zelle[k]["bezeichnung"]]) > 1)
    if doppelt:
        nimm(doppelt[0], "Bezeichnung in mehreren Produktgruppen")
    mehr = sorted(k for k in ansatz if len({x[3] for x in zelle if x[:3] == k[:3] and x[3] != 12}) >= 3)
    if mehr:
        nimm(mehr[0], "Maßnahme mit drei oder mehr Zeilen")
    leer = sorted(k for k in zelle if k[4] in MIT_ANSATZ and b(k) == 0 and k[3] != 12)
    if leer:
        nimm(leer[len(leer) // 2], "leere Zelle (0 €)")
    rnd = random.Random(20261110)
    pbs = sorted({zelle[k]["produktbereich"] for k in ansatz})
    for pb in pbs:
        kandidaten = sorted(k for k in ansatz if zelle[k]["produktbereich"] == pb and k not in auswahl)
        if kandidaten and len(auswahl) < 32:
            nimm(rnd.choice(kandidaten), f"Stichprobe PB {pb}")
    # zweiter Leseweg je Seite
    ordner = pdf_ordner or __import__("os").environ.get("HAUSHALT_PDF")
    st = stand["ausgaben"][AUSGABE]
    layouts = {}
    out = []
    for k, gruende in sorted(auswahl.items(), key=lambda x: (zelle[x[0]]["produktbereich"], x[0])):
        r = zelle[k]
        pb = r["produktbereich"]
        if (pb, k[1]) not in layouts:
            pdf = hp._pdf(st["dateien"][pb]["url"], st["dateien"][pb]["sha256"])
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "x.pdf"
                p.write_bytes(pdf)
                layouts[(pb, k[1])] = subprocess.run(["pdftotext", "-layout", "-f", str(k[1]), "-l", str(k[1]),
                                                      str(p), "-"], capture_output=True, check=True, text=True).stdout
        name = r["bezeichnung"]
        if r["vermerk"].startswith("Bezeichnung abgeleitet"):
            zweit = "nicht verglichen (Bezeichnung im PDF über dem vorigen Block)"
        else:
            w = zweiter_leseweg(layouts[(pb, k[1])], name, k[3], k[4])
            zweit = "nicht gefunden" if w is None else ("gleich" if w == b(k) else f"abweichend: {_wie_im_pdf(w)}")
        if k[3] == 12 and r["vermerk"].startswith("Saldo nachgerechnet"):
            zweit = "nicht verglichen (Saldo nachgerechnet)"
        out.append([r["produktbereich"], f"{r['produktgruppe']} {r['pg_name']}", name, f"{k[3]} {r['zeile_name']}",
                    k[4], r["art"], r["jahr"], _wie_im_pdf(b(k)), r["vermerk"],
                    f"{st['dateien'][pb]['url']}#page={k[1]}", k[1], ", ".join(gruende), zweit, ""])
    PRUEFBOGEN.parent.mkdir(parents=True, exist_ok=True)
    with open(PRUEFBOGEN, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f, delimiter="\t", lineterminator="\n")
        wr.writerow(["produktbereich", "produktgruppe", "massnahme", "zeile", "spalte", "art", "jahr", "betrag",
                     "vermerk", "datei", "seite", "auswahl", "zweiter_leseweg", "pruefung"])
        wr.writerows(out)
    gleich = sum(o[12] == "gleich" for o in out)
    print(f"Prüfbogen Einzelmaßnahmen: {len(out)} Zellen, zweiter Leseweg gleich {gleich} → {PRUEFBOGEN}")


def daten():
    """Für die Seiten: {Produktgruppe: [Maßnahme]} aus massnahmen.tsv, je Produktgruppe absteigend nach den Auszahlungen
    im Ansatz 2026 (dann 2025). Je Maßnahme Auszahlungen (Zeilen 6–10) und Einzahlungen (Zeilen 1–4) in den Spalten
    Ansatz 2025, Ansatz 2026 und Gesamt, dazu Datei, Seite und Vermerk. Ohne Freigabe oder ohne Datei {}."""
    if not FREIGEGEBEN or not TSV.exists():
        return {}
    je = {}
    for r in hp.lesen(TSV):
        k = (r["produktgruppe"], int(r["seite"]), int(r["position"]))
        m = je.setdefault(k, {"pg": r["produktgruppe"], "pb": r["produktbereich"], "bezeichnung": r["bezeichnung"],
                              "datei": r["datei"], "seite": int(r["seite"]), "vermerk": r["vermerk"],
                              "aus": {4: 0, 6: 0, 12: 0}, "ein": {4: 0, 6: 0, 12: 0}})
        nr, sp, b = int(r["zeile"]), int(r["spalte"]), int(r["betrag"])
        if nr in AUSZAHLUNG:
            m["aus"][sp] += b
        elif nr in EINZAHLUNG:
            m["ein"][sp] += b
    out = {}
    for m in sorted(je.values(), key=lambda m: (-m["aus"][6], -m["aus"][4], -m["ein"][6], m["bezeichnung"])):
        out.setdefault(m["pg"], []).append(m)
    return out
