// Systemprompt: Markierungen, Platzhalter, Übereinstimmung mit den Werkzeugen
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { extractPrompt, fillPrompt, promptValues, deDate, version, loadSystemPrompt } from "../../site/chat/prompt.js";
import { TOOLS } from "../../site/chat/tools.js";

const SITE = new URL("../../site/", import.meta.url);
const MD = await readFile(new URL("chat/systemprompt.md", SITE), "utf8");
const STATUS = { first_date: "2019-10-07", sources: [{ name: "oparl-bonn", retrieved_at: "2026-10-17T23:30:00+00:00" }] };

test("Datumsformat TT.MM.JJJJ, Tagesgrenze in Bonn", () => {
  assert.equal(deDate("2019-10-07"), "07.10.2019");
  assert.equal(deDate("2026-10-17T23:30:00+00:00"), "18.10.2026");
  assert.equal(deDate(null), "unbekannt");
});

test("Prompt: alle Platzhalter befüllt, Version, Änderungsvermerk außerhalb des Prompts", async () => {
  const p = await loadSystemPrompt({ loadText: async () => MD, status: STATUS, now: new Date("2026-10-18T10:00:00Z") });
  assert.equal(p.version, "0.8");
  assert.doesNotMatch(p.text, /\{[A-ZÄÖÜ_]+\}/);
  assert.match(p.text, /Heute ist der 18\.10\.2026\. Der Datenstand ist der 18\.10\.2026\. Die Daten umfassen Vorlagen ab dem 07\.10\.2019\./);
  assert.match(p.text, /höchstens 8 Aufrufe/);
  assert.doesNotMatch(p.text, /Änderungen gegenüber/);
  assert.match(p.text, /https:\/\/www\.bonn\.de\/vv\/produkte\/buergerantrag/);
  assert.throws(() => fillPrompt("{HEUTE} {UNBEKANNT}", { heute: "x" }), /UNBEKANNT/);
  assert.throws(() => extractPrompt("ohne Markierung"), /Markierungen/);
  assert.equal(version("kein"), null);
});

test("Prompt nennt genau die Werkzeuge aus tools.js", () => {
  const section = extractPrompt(MD).split("## Werkzeuge")[1].split("\n## ")[0];
  const named = [...section.matchAll(/^- `([a-z_]+)`/gm)].map((m) => m[1]);
  assert.deepEqual(named.sort(), TOOLS.map((t) => t.name).sort());
});

test("Werte aus dem Datenstand", () => {
  const v = promptValues(STATUS, new Date("2026-01-02T00:30:00Z"));
  assert.deepEqual(v, { heute: "02.01.2026", datenstand: "18.10.2026", datenbeginn: "07.10.2019" });
  assert.equal(promptValues({}).datenstand, "unbekannt");
});
