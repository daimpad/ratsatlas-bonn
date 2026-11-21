# Paket A2: Sicherheit der Workflows (21.11.2026)

Umsetzung zu `BERICHT_2026-11.md`, Nr. 7, 22, 23, 24, 26 und Hinweis 21. Einzelheiten in `TECHNIK.md`, Abschnitt „Betrieb“.

| Nr. | Umgesetzt |
|---|---|
| 7 | Python-Pakete mit festen Versionen und Prüfsummen (`requirements.in` → `requirements.txt`, auch `pipeline/kacheln/`), `npm ci` mit `package-lock.json` für die Browser-Tests, `persist-credentials: false` bei allen Checkouts, Kurzfassungen in drei Schritten (Schlüssel und Schreib-Token getrennt), `eval.yml` nur mit dem Schlüssel des gewählten Anbieters, Dependabot |
| 22 | `wahlen-rohdaten`: nur https, nur Stellen der Stadt und des Landes, höchstens 100 MB je Datei, auch nach Weiterleitungen |
| 23 | `kacheln.yml`: Token nicht mehr im Arbeitsverzeichnis; keine Aufteilung in zwei Jobs (Begründung in `TECHNIK.md`) |
| 24 | `upload-pages-artifact` v4.0.0 mit festgelegtem `upload-artifact` |
| 21 | `live.yml` prüft `Content-Security-Policy` für `/` per GET und die Weiterleitung von `www.bonn.ratsatlas.de` (Hinweise) |

Beim Auftraggeber (Einstellungen, nicht per Pull Request möglich):

- Schutzregel für den Branch `deploy` (Nr. 7).
- Freigabe von Workflows für alle externen Pull Requests (Nr. 26).
- Weiterleitung von `www.bonn.ratsatlas.de` und Kopfzeilen für statische Dateien in Plesk (Nr. 21, bekannt).

Prüfung: Installation mit `--require-hashes` unter Python 3.12 und 3.13; Unit-Tests; YAML aller Workflows gültig. Die geänderten Workflows laufen erst nach dem Zusammenführen vollständig (täglicher Lauf, `kurzfassungen`).
