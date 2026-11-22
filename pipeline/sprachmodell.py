"""Aufruf eines Sprachmodells (Mistral oder Anthropic) für Kurzfassungen und Stufe C.

Anbieter: Umgebungsvariable SPRACHMODELL („mistral“, Standard, oder „anthropic“); Schlüssel MISTRAL_API_KEY bzw.
ANTHROPIC_API_KEY (Secrets im Workflow). Ohne Schlüssel liefert `schluessel()` None und es wird nichts angefragt.
"""
import csv
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone

ANBIETER = os.environ.get("SPRACHMODELL", "mistral")
API = {"mistral": "https://api.mistral.ai/v1/chat/completions", "anthropic": "https://api.anthropic.com/v1/messages"}
SCHLUESSEL = {"mistral": "MISTRAL_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def schluessel(anbieter=None):
    return os.environ.get(SCHLUESSEL[anbieter or ANBIETER])


class AntwortFormat(ValueError):
    """Die Antwort enthält keinen Antworttext. Mistral liefert bei Modellen mit Denkschritten `content` als Liste von
    Teilen (`thinking`, `text`) statt als Zeichenkette (seit dem 13.11.2026 hinter `mistral-large-latest`; fiel bis
    zum 21.11.2026 nur als AttributeError auf). Gelesen werden nur die Teile `text`; fehlen sie (etwa weil die
    Längengrenze schon in den Denkschritten erreicht ist), gilt die Anfrage als gescheitert. Die Meldung nennt Form,
    Modell und Ende der Antwort, nie ihren Text."""


def antworttext(d):
    """Antworttext im Format von Mistral: die Zeichenkette oder die Teile `text` einer Liste; Denkschritte
    (`thinking`) werden nie übernommen. AntwortFormat, wenn kein Text enthalten ist."""
    wahl = (d.get("choices") or [{}])[0] if isinstance(d, dict) else {}
    content = (wahl.get("message") or {}).get("content")
    modell = d.get("model") if isinstance(d, dict) else None
    if wahl.get("finish_reason") == "length":   # an der Längengrenze abgeschnitten: kein vollständiger Text
        raise AntwortFormat(f"Antwort an der Längengrenze abgeschnitten (Modell laut Antwort: {modell}; Ende: length)")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        text = "".join(c["text"] for c in content
                       if isinstance(c, dict) and c.get("type") == "text" and isinstance(c.get("text"), str)).strip()
        if text:
            return text
        form = "Liste mit Teilen " + ", ".join(sorted({str(c.get("type")) if isinstance(c, dict) else type(c).__name__
                                                      for c in content}) or ["(leer)"])
    else:
        form = "leere Zeichenkette" if isinstance(content, str) else type(content).__name__
    raise AntwortFormat(f"Antwort ohne Text (content: {form}; Modell laut Antwort: {modell}; "
                        f"Ende: {wahl.get('finish_reason')})")


def frage(system, nutzer, modell, schluessel, max_tokens=400, json_antwort=False, anbieter=None, tries=4):
    """(Antworttext, {"ein": Eingabe-Tokens, "aus": Ausgabe-Tokens}); wiederholt bei Netzfehlern."""
    anbieter = anbieter or ANBIETER
    if anbieter == "anthropic":
        body = {"model": modell, "max_tokens": max_tokens, "temperature": 0.1, "system": system,
                "messages": [{"role": "user", "content": nutzer}]}
        headers = {"x-api-key": schluessel, "anthropic-version": "2023-06-01"}
    else:
        body = {"model": modell, "max_tokens": max_tokens, "temperature": 0.1,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": nutzer}]}
        if json_antwort:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {schluessel}"}
    req = urllib.request.Request(API[anbieter], data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            break
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** (i + 2))
    if anbieter == "anthropic":
        text = "".join(c.get("text", "") for c in d.get("content", []))
        u = d.get("usage") or {}
        return text.strip(), {"ein": u.get("input_tokens", 0), "aus": u.get("output_tokens", 0)}
    u = d.get("usage") or {}
    return antworttext(d), {"ein": u.get("prompt_tokens", 0), "aus": u.get("completion_tokens", 0)}


def json_aus(text):
    """Erstes JSON-Objekt einer Antwort (auch in einem Codeblock); None, wenn keines lesbar ist."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def protokoll(verzeichnis, schritt, modell, anfragen, tokens, fehler=0):
    """Eine Zeile je Lauf mit Anfragen in laeufe.tsv (Branch kurzfassungen): Zeitpunkt, Schritt, Modell, Anfragen,
    Tokens, Fehler – zur Abschätzung der Kosten."""
    if not anfragen:
        return
    path = os.path.join(verzeichnis, "laeufe.tsv")
    neu = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        if neu:
            w.writerow(["zeitpunkt", "schritt", "modell", "anfragen", "eingabe_tokens", "ausgabe_tokens", "fehler"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), schritt, modell, anfragen,
                    tokens.get("ein", 0), tokens.get("aus", 0), fehler])
