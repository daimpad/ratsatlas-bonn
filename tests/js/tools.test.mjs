// Werkzeuge des Ratsassistenten: Einheitstests mit kleinen Daten im Speicher; zusätzlich ein Lauf gegen den
// echten Export, falls data/export/bonn/chat vorhanden ist (lokal nach `python -m pipeline export`).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { createTools, TOOLS, MAX_CHARS, OHNE_NR, dateBound, fit, norm } from "../../site/chat/tools.js";

const ROOT = new URL("../../data/export/", import.meta.url);
const GLOSSAR = JSON.parse(await readFile(new URL("glossar.json", ROOT), "utf8"));

const STAENDE = ["entschieden", "beraten, ohne Entscheidung", "in Beratung", "offen", "ohne Beratungsfolge"];
const SUCHE = {
  themes: [{ id: "verkehr", label: "Verkehr und Mobilität" }, { id: "umwelt", label: "Umwelt, Grün und Klima" }],
  parties: ["CDU", "SPD", "Verwaltung"], areas: [{ key: "ortsteil:endenich", name: "Endenich" }],
  types: ["Anregungen und Beschwerden", "Antrag", "Beschlussvorlage"], stands: STAENDE,
  aemter: ["61 Stadtplanungsamt", "66 Tiefbauamt"], gremien: ["Bezirksvertretung Bonn", "Rat"],
  rows: [
    ["261749", "Bürgerantrag: Radverkehr im Teilabschnitt Endenicher Straße 238 bis 220", "2026-09-29", 0, 3, 0, [0], [], [], -1, [0]],
    ["261088", "CDU-Antrag: Bäume an der Frongasse 12", "2026-06-02", 1, 2, 0, [1], [0], [], 1, [0]],
    ["255001", "Neubau Radweg Endenicher Strasse", "2025-03-01", 2, 0, 0, [0], [2], [], 0, [0, 1]],
  ],
};
const ORTE = {
  places: [
    { level: "ortsteil", name: "Endenich", ortsteil: "Endenich", stadtbezirk: "Bonn", lon: 7.07, lat: 50.73, papers: [["255001", "B", "ortsteil_name", "mittel"]] },
    { level: "strasse", name: "Endenicher Straße", ortsteil: "Endenich", stadtbezirk: "Bonn", lon: 7.08, lat: 50.731, papers: [["261749", "A", "oparl_location", "hoch"], ["255001", "B", "strasse", "mittel"]] },
    { level: "strasse", name: "Frongasse", ortsteil: "Endenich", stadtbezirk: "Bonn", lon: 7.071, lat: 50.729, papers: [["261088", "B", "strasse", "mittel"]] },
  ],
};
const VORLAGE = {
  reference: "261088", name: "CDU-Antrag: Bäume an der Frongasse 12", paper_type: "Antrag", date: "2026-06-02",
  amt: "66 Tiefbauamt", web: "https://example.org/vo", main_file: null, source_object: "https://example.org/oparl/papers/1",
  stand: "in Beratung", parties: ["CDU"], plans: [],
  soll: { verfahren: "antrag-bv", sicherheit: "hoch", grund: "Antrag mit Beratung in der Bezirksvertretung", passung: "weicht ab", ist: ["bv", "rat"], abweichung: ["rat"] },
  responsibility: [{ kind: "federfuehrend", label: "66 Tiefbauamt", name: "66-2 Straßenbau", derived: false }],
  originators: [{ actor: "CDU", actor_type: "Bezirksfraktion", derived: true, evidence: "CDU-Antrag" }],
  themes: [{ theme: "umwelt", method: "stichwort", evidence: "bäume", confidence: "niedrig" }],
  locations: [{ level: "strasse", name: "Frongasse", ortsteil: "Endenich", stadtbezirk: "Bonn", stage: "B", method: "strasse", confidence: "mittel", evidence: "Frongasse" }],
  superordinated: [], subordinated: [{ reference: "261088-01 ST", paper_type: "Stellungnahme der Verwaltung", name: "Stellungnahme", date: "2026-08-31" }],
  steps: [
    { typ: "initiierung", label: "Antrag", status: "belegt", actors: ["CDU"], actors_status: "abgeleitet" },
    { typ: "veroeffentlichung", label: "Datum der Vorlage", status: "belegt", date: "2026-06-02", note: "datum" },
    { typ: "beratung", label: "Bezirksvertretung Bonn", role: "Empfehlung", status: "belegt", date: "2026-06-24", date_status: "abgeleitet", result: "vertagt", result_source: "oparl-lite", stand: "beraten" },
    { typ: "entscheidung", label: "Rat", role: "Entscheidung", status: "belegt", date_status: "unklar", stand: "offen", note: "ohne_sitzung" },
    { typ: "folgevorlage", label: "Stellungnahme der Verwaltung", status: "belegt", date: "2026-08-31", reference: "261088-01 ST", title: "Stellungnahme" },
  ],
};
const GREMIEN = {
  organizations: [
    { name: "Bezirksvertretung Bonn", short_name: "BV Bonn", type: "Gremium", classification: "Bezirksvertretungen", end_date: null, web: null, source_object: "o/gr/2", consultations: 50, deciding: 20, meetings: 3, theme: null,
      besetzung: { mitglieder: 19, sitze: [{ fraktion: "Grüne", n: 6 }], ohne_fraktion: 2, sachkundig: 0, stellvertretungen: 0, beratend: 16, vorsitz: [{ name: "A. Beispiel", rolle: "Bezirksbürgermeister/in", fraktion: "Grüne" }] } },
    { name: "61-3 Stadtverkehr", short_name: "61-3", type: "Verwaltungsbereich", classification: "61 Stadtplanungsamt", end_date: null, web: null, source_object: "o/at/227", amt: "61 Stadtplanungsamt", papers_led: 900, theme: "bauen" },
    { name: "61 Stadtplanungsamt", short_name: "61", type: "Verwaltungsbereich", classification: "61 Stadtplanungsamt", end_date: null, web: null, source_object: "o/at/30", amt: "61 Stadtplanungsamt", papers_led: 100, theme: "bauen" },
  ],
};
const ZEIT = {
  meetings: [
    { date: "2026-09-15", time: "17:00", gremium: "Bezirksvertretung Bonn", name: "Sitzung der Bezirksvertretung Bonn", cancelled: false, state: "durchgeführt", web: "https://example.org/to", invitation: null, agenda_items: 40, source_object: "o/m/1" },
    { date: "2026-11-24", time: "17:00", gremium: "Bezirksvertretung Bonn", name: "Sitzung der Bezirksvertretung Bonn", cancelled: false, state: "terminiert", web: null, invitation: null, agenda_items: 0, source_object: "o/m/2" },
    { date: "2026-11-26", time: "16:00", gremium: "Rat", name: "Sitzung des Rates", cancelled: false, state: "terminiert", web: null, invitation: null, agenda_items: 0, source_object: "o/m/3" },
    { date: "2026-12-01", time: "15:00", gremium: "Projektbeirat Behindertenpolitischer Teilhabeplan für die Bundesstadt Bonn", name: "Sitzung des Projektbeirats", cancelled: false, state: "terminiert", web: null, invitation: null, agenda_items: 0, source_object: "o/m/4" },
  ],
};
const DATENSTAND = { sources: [{ name: "oparl-bonn", url: "https://example.org", license: "CC0 1.0", retrieved_at: "2026-10-18T12:00:00+00:00" }], papers: 3, gaps: ["Vorlagen vor Oktober 2019 sind nicht enthalten."] };

const PLAENE = {
  schritte: [{ id: "aufstellung", label: "Aufstellungsbeschluss", fundstelle: "§ 2 Abs. 1 BauGB" }, { id: "satzung", label: "Satzungsbeschluss", fundstelle: "§ 10 Abs. 1 BauGB" }],
  plaene: [{ nr: "6122-1", treffer: "eindeutig", ortsteile: ["Dransdorf"],
    plaene: [{ name: "6122-1", inkraft_seit: "2025-06-04", plan: "https://example.org/p.pdf", begruendung: "https://example.org/b.pdf" }],
    vorlagen: [{ drucksache: "190535", datum: "2019-10-28", titel: "Aufstellung des Bebauungsplanes Nr. 6122-1 Grootestraße", art: "Mitteilungsvorlage", stand: "entschieden", schritte: ["aufstellung"], arten: [] }] }],
};
const BAUSTELLEN = {
  meta: { lizenz: "CC0 1.0", archiv_beginn: "2026-10-19", abruf: "2026-10-19T05:23:00+00:00", hinweise: ["Termine unverbindlich."] },
  baustellen: [
    { id: "9746", bezeichnung: "Siemensstraße", strasse: "Siemensstraße", stadtbezirk: "Bonn", von: "2026-08-03", bis: "2027-03-31", traeger: "Bundesstadt Bonn - Amt 66-2", fremd: false,
      massnahme: "Straßenbau", lon: 7.0712, lat: 50.7299, aktiv: true,
      kandidaten: [{ drucksache: "240553", titel: "Umgestaltung der Siemensstraße", entschieden_am: "2024-05-28", abstand_m: 9, kriterien: { raeumlich: true }, konfidenz: "hoch" }] },
    { id: "9001", bezeichnung: "Kölnstraße", strasse: "Kölnstraße", stadtbezirk: "Bonn", von: "2026-11-02", bis: "2026-12-01", traeger: "SWB Bonn-Netz", fremd: true,
      massnahme: "Leitungsbau", lon: 7.0, lat: 50.74, aktiv: true, kandidaten: [] },
    { id: "8000", bezeichnung: "Alte Baustelle", strasse: null, stadtbezirk: "Beuel", von: "2026-01-01", bis: "2026-09-01", traeger: "Bundesstadt Bonn - Amt 66-5", fremd: false,
      massnahme: "Kanalbau", lon: 7.1, lat: 50.73, aktiv: false, kandidaten: [] },
  ],
};

const SOLL = {
  meta: { quelle: "Verfahrensmodell aus „Bonn entscheidet“ (MIT)", hinweis: "Vereinfachtes Modell, keine Rechtsauskunft." },
  bahnen: { bvm: "Bezirksverordnete · Bezirksfraktion", bv: "Bezirksvertretung", rat: "Rat" },
  verfahren: { "antrag-bv": { titel: "Antrag in der Bezirksvertretung", schritte: [
    { id: "b1", label: "Antrag einreichen", was: "Antrag einreichen", bahn: "bvm", beleg: "GeschO § 23", links: [{ label: "Geschäftsordnung des Rates § 23", url: "https://example.org/gescho" }] },
    { id: "b2", label: "Bezirksvertretung entscheidet", was: "Beratung und Beschluss", bahn: "bv", beleg: "BezS § 7" },
    { id: "b3", label: "Anhörung", was: "Anhörung", bahn: "bv", eigen: true, beleg: "BezS § 9" }] } },
  ohne_soll: { "Bürgerbrief": "kein Soll angenommen." },
  mitwirken: [{ id: "termin-offen", wenn: { status: ["offen", "vertagt"], termin: false }, was: "Ein Sitzungstermin steht noch nicht fest.",
    frist: "14 Tage vor der Sitzung", tage: 0, beleg: "GeschO § 2 Abs. 2", links: [] }],
  buergerantrag_ziel: { bezirk: "Bezirksvertretung {bezirk}", stadt: "Ausschuss für Beteiligung der Bürgerinnen und Bürger" },
};
const KONTEXT = {
  meta: { hinweis: "Einordnung, kein Urteil. Alle Werte sind auf Ortsteile umgerechnet (abgeleitet).", mindest_einwohner: 100,
    reihenfolge: ["einwohner", "miete", "bodenrichtwert", "hitze"], bodenrichtwert_hinweis_ohne_zone: 33,
    quellen: { zensus: { titel: "Zensus 2022", lizenz: "dl-de/by-2.0", stand: "2022-05-15", url: "https://www.zensus2022.de/" },
      klima: { titel: "Klimaanalyse NRW", lizenz: "dl-de/zero-2.0", stand: "2026", url: "https://www.opengeodata.nrw.de/" } },
    kennzahlen: { einwohner: { titel: "Einwohner", einheit: "", quelle: "zensus", methode: "Zellen nach Mittelpunkt" },
      miete: { titel: "durchschnittliche Nettokaltmiete", einheit: "€/m²", quelle: "zensus", methode: "Mittel der Zellen" },
      bodenrichtwert: { titel: "Bodenrichtwert Wohnbauland (Median)", einheit: "€/m²", quelle: "zensus", methode: "Median" },
      hitze: { titel: "Hitze", einheit: "%", quelle: "klima", methode: "Anteil der Einwohner" } } },
  bonn: { einwohner: 321351, miete: 9.09, hitze: 55.3 },
  bezirke: { Bonn: { einwohner: 150114, miete: 9.58, hitze: 67.3 }, Hardtberg: { einwohner: 33000, miete: 8.5, hitze: 30 } },
  ortsteile: { Endenich: { einwohner: 12733, miete: 10.12, hitze: 53.3 }, "Hardthöhe": { einwohner: 20 },
    "Bonn-Zentrum": { einwohner: 9000, miete: 11, hitze: 90, bodenrichtwert: 980, bodenrichtwert_abdeckung: 34.2 } },
  stadtbezirk_je_ortsteil: { Endenich: "Bonn", "Hardthöhe": "Hardtberg", "Bonn-Zentrum": "Bonn" },
};
const FILES = {
  "glossar.json": GLOSSAR, "bonn/suche.json": SUCHE, "bonn/chat/orte.json": ORTE, "bonn/chat/vorlagen/2610.json": { papers: { 261088: VORLAGE } },
  "bonn/chat/gremien.json": GREMIEN, "bonn/zeit.json": ZEIT, "bonn/chat/datenstand.json": DATENSTAND,
  "bonn/plaene.json": PLAENE, "bonn/baustellen.json": BAUSTELLEN, "bonn/soll.json": SOLL,
  "bonn/kontext.json": KONTEXT,
};
const tools = () => createTools({
  today: "2026-10-18",
  load: async (p) => { if (!(p in FILES)) throw new Error(`HTTP 404 ${p}`); return structuredClone(FILES[p]); },
});

test("Werkzeugdefinitionen: zwölf Werkzeuge mit Objekt-Schema", () => {
  assert.equal(TOOLS.length, 12);
  assert.equal(new Set(TOOLS.map((t) => t.name)).size, 12);
  for (const t of TOOLS) {
    assert.equal(t.parameters.type, "object");
    assert.ok(t.description.length > 30, t.name);
  }
});

test("Datumsgrenzen", () => {
  assert.equal(dateBound("2025", false), "2025-01-01");
  assert.equal(dateBound("2025-03", true), "2025-03-31");
  assert.equal(dateBound("", true), null);
  assert.throws(() => dateBound("März 2025"));
  assert.equal(norm("Endenicher Straße"), norm("endenicher strasse"));
});

test("suche_vorlagen: Stichwörter, Filter, Seiten", async () => {
  const t = tools();
  const a = await t.run("suche_vorlagen", { stichwort: "endenicher strasse" });
  assert.deepEqual(a.treffer.map((x) => x.drucksache), ["261749", "255001"]);
  const b = await t.run("suche_vorlagen", { amt: "66", von: "2026" });
  assert.deepEqual(b.treffer.map((x) => x.drucksache), ["261088"]);
  const c = await t.run("suche_vorlagen", { gremium: "Rat" });
  assert.deepEqual(c.treffer.map((x) => x.drucksache), ["255001"]);
  const d = await t.run("suche_vorlagen", { ortsteil: "endenich", thema: "verkehr", partei: "Verwaltung" });
  assert.deepEqual(d.treffer.map((x) => x.drucksache), ["255001"]);
  assert.ok(d.hinweise.some((h) => h.includes("abgeleitet")));
  const e = await t.run("suche_vorlagen", { vorlagenart: "Gibt es nicht" });
  assert.ok(e.fehler && e.moegliche_werte.includes("Antrag"));
  const f = await t.run("suche_vorlagen", { seite: 2 });
  assert.equal(f.treffer.length, 0);
  assert.equal(f.seiten, 1);
});

test("Datenschutz: Hausnummern nur in Titeln aus der Einwohnerschaft ausgelassen", async () => {
  const t = tools();
  const r = await t.run("suche_vorlagen", {});
  const titel = Object.fromEntries(r.treffer.map((x) => [x.drucksache, x.titel]));
  assert.equal(titel["261749"], `Bürgerantrag: Radverkehr im Teilabschnitt Endenicher Straße ${OHNE_NR}`);
  assert.equal(titel["261088"], "CDU-Antrag: Bäume an der Frongasse 12");
});

test("Datenschutz: auch Folgevorlagen eines Bürgerantrags ohne Hausnummer, Plannummern bleiben", async () => {
  // Code-Prüfung 23.10.2026: Stellungnahmen zu Bürgeranträgen tragen weder Art noch Wort „Bürgerantrag“
  const vorlage = { ...VORLAGE, plans: [{ nr: "7923-2", evidence: "Bebauungsplan 7923-2 an der Frongasse 12", area: true }] };
  const files = { ...FILES, "bonn/chat/einwohner.json": { drucksachen: ["261088", "261088-01 ST"] }, "bonn/chat/vorlagen/2610.json": { papers: { 261088: vorlage } } };
  const t = createTools({ today: "2026-10-18", load: async (p) => { if (!(p in files)) throw new Error(`HTTP 404 ${p}`); return structuredClone(files[p]); } });
  const r = await t.run("suche_vorlagen", {});
  assert.equal(r.treffer.find((x) => x.drucksache === "261088").titel, `CDU-Antrag: Bäume an der Frongasse ${OHNE_NR}`);
  const v = await t.run("hole_vorlage", { drucksache: "261088" });
  assert.equal(v.titel, `CDU-Antrag: Bäume an der Frongasse ${OHNE_NR}`);
  assert.equal(v.bebauungsplaene[0].fundstelle, `Bebauungsplan 7923-2 an der Frongasse ${OHNE_NR}`);
});

test("Datenschutz: auch Nummern hinter „Hausnummer“, „Haus-Nr.“ und „Straße Nr.“ (Lücke 01.11.2026)", async () => {
  const files = structuredClone(FILES);
  files["bonn/suche.json"].rows[0][1] = "Bürgerantrag: Tempo 30 in Höhe der Hausnummer 82, vor Haus-Nr. 5 und Frongasse Nr. 3 (neben Haus-Nr.) 7";
  const t = createTools({ today: "2026-10-18", load: async (p) => { if (!(p in files)) throw new Error(`HTTP 404 ${p}`); return structuredClone(files[p]); } });
  const r = await t.run("suche_vorlagen", {});
  assert.equal(r.treffer.find((x) => x.drucksache === "261749").titel,
    `Bürgerantrag: Tempo 30 in Höhe der ${OHNE_NR}, vor ${OHNE_NR} und Frongasse ${OHNE_NR} (neben ${OHNE_NR})`);
});

test("hole_vorlage: KI-Kurzfassung als abgeleitet gekennzeichnet", async () => {
  const kurz = { ...VORLAGE, kurzfassung: { text: "Es geht um Bäume.", modell: "m" } };
  const t = createTools({ today: "2026-10-18", load: async (p) => structuredClone(p === "bonn/chat/vorlagen/2610.json" ? { papers: { 261088: kurz } } : FILES[p]) });
  const v = await t.run("hole_vorlage", { drucksache: "261088" });
  assert.equal(v.kurzfassung.text, "Es geht um Bäume.");
  assert.equal(v.kurzfassung.status, "abgeleitet");
  assert.match(v.kurzfassung.hinweis, /kein Zitat/);
});

test("hole_vorlage: Felder, Status und Quellen-ID", async () => {
  const t = tools();
  const v = await t.run("hole_vorlage", { drucksache: " 261088 " });
  assert.equal(v.drucksache, "261088");
  assert.equal(v.quelle_id, "https://example.org/oparl/papers/1");
  assert.equal(v.einreichende[0].status, "abgeleitet");
  assert.equal(v.themen[0].thema, "Umwelt, Grün und Klima");
  assert.equal(v.folgevorlagen[0].drucksache, "261088-01 ST");
  assert.equal(v.abgerufen, "2026-10-18T12:00:00+00:00");
  assert.equal(v.kurzfassung, null);
  assert.match((await t.run("hole_vorlage", { drucksache: "261099" })).fehler, /nicht enthalten/);
  assert.match((await t.run("hole_vorlage", { drucksache: "abc" })).fehler, /keine Drucksachennummer/);
  assert.match((await t.run("hole_vorlage", { drucksache: "999999" })).fehler, /nicht enthalten/);
});

test("hole_prozesslinie: Schritte mit Evidenzstatus und Erläuterung", async () => {
  const p = await tools().run("hole_prozesslinie", { drucksache: "261088" });
  assert.deepEqual(p.schritte.map((s) => s.schritt), ["Anstoß", "Datum der Vorlage", "Beratung", "Entscheidung", "Folgevorlage"]);
  const rat = p.schritte[3];
  assert.equal(rat.datum_status, "unklar");
  assert.equal(rat.hinweis, GLOSSAR.hinweise.ohne_sitzung);
  assert.equal(p.schritte[2].ergebnis, "vertagt");
  assert.deepEqual(Object.keys(p.evidenzstatus), ["belegt", "soll"]);
  // Zeitbezug zum Bezugstag (heute 2026-10-18): Beratung im Juni vergangen, Rat ohne Datum ohne Zeitbezug
  assert.equal(p.heute, "2026-10-18");
  assert.equal(p.schritte[2].zeitbezug, "vergangen");
  assert.equal(rat.zeitbezug, undefined);
});

test("hole_prozesslinie: Soll nach Regelwerk mit Befund und Rechtsgrundlage", async () => {
  const s = (await tools().run("hole_prozesslinie", { drucksache: "261088" })).soll_nach_regelwerk;
  assert.equal(s.verfahren, "Antrag in der Bezirksvertretung");
  assert.equal(s.zuordnung_status, "abgeleitet");
  assert.match(s.befund, /Rat; .*Befund, keine Bewertung/);
  assert.deepEqual(s.schritte.map((x) => x.status), ["soll", "belegt", "belegt"]);
  assert.equal(s.schritte[0].abgleich, "nicht abgeglichen");
  assert.deepEqual(s.schritte[0].links, ["https://example.org/gescho"]);
  assert.equal(s.schritte[2].ergaenzung_ris_karte, true);
  assert.match(s.quelle, /keine Rechtsauskunft/);
  assert.deepEqual(s.mitwirken, [{ hinweis: "Ein Sitzungstermin steht noch nicht fest.", frist: "14 Tage vor der Sitzung", rechtsgrundlage: "GeschO § 2 Abs. 2" }]);
  assert.equal(s.mitwirken_einordnung.status, "vertagt");
});

test("suche_ort: Straße, Ortsteil, Umkreis", async () => {
  const t = tools();
  const s = await t.run("suche_ort", { ort: "Frongasse" });
  assert.deepEqual(s.treffer.map((x) => x.drucksache), ["261088"]);
  assert.equal(s.treffer[0].verortung[0].konfidenz, "mittel");
  const o = await t.run("suche_ort", { ort: "Endenich", bis: "2025" });
  assert.deepEqual(o.treffer.map((x) => x.drucksache), ["255001"]);
  const u = await t.run("suche_ort", { lat: 50.729, lon: 7.071, radius_m: 100 });
  assert.deepEqual(u.treffer.map((x) => x.drucksache), ["261088"]);
  assert.ok((await t.run("suche_ort", { ort: "Atlantis" })).fehler);
  assert.ok((await t.run("suche_ort", {})).fehler);
});

test("liste_sitzungen: kommende und vergangene bezogen auf heute", async () => {
  const t = tools();
  const k = await t.run("liste_sitzungen", { gremium: "Bezirksvertretung Bonn" });
  assert.deepEqual(k.sitzungen.map((m) => m.datum), ["2026-11-24"]);
  const v = await t.run("liste_sitzungen", { zeitraum: "vergangene" });
  assert.deepEqual(v.sitzungen.map((m) => m.quelle_id), ["o/m/1"]);
  const alle = await t.run("liste_sitzungen", { von: "2026-11", bis: "2026-11" });
  assert.equal(alle.treffer_gesamt, 2);
});

test("liste_sitzungen: „Rat der Stadt Bonn“ meint den Rat, nicht ein Gremium mit „…rat“ und „Bundesstadt Bonn“", async () => {
  const t = tools();
  for (const g of ["Rat der Stadt Bonn", "Stadtrat", "Rat der Bundesstadt Bonn", "rat"]) {
    const r = await t.run("liste_sitzungen", { gremium: g, zeitraum: "alle" });
    assert.deepEqual(r.anfrage.gremium, ["Rat"], g);
    assert.deepEqual(r.sitzungen.map((m) => m.datum), ["2026-11-26"], g);
  }
  const p = await t.run("liste_sitzungen", { gremium: "Projektbeirat" });
  assert.deepEqual(p.sitzungen.map((m) => m.quelle_id), ["o/m/4"]);
});

test("hole_gremium_oder_amt: Amtsnummer bevorzugt das Amt selbst", async () => {
  const t = tools();
  const a = await t.run("hole_gremium_oder_amt", { name: "61" });
  assert.equal(a.treffer.name, "61 Stadtplanungsamt");
  assert.equal(a.treffer.federfuehrende_vorlagen_amt_gesamt, 1000);
  const g = await t.run("hole_gremium_oder_amt", { name: "BV Bonn" });
  assert.equal(g.treffer.naechste_sitzung, "2026-11-24");
  assert.equal(g.treffer.letzte_sitzung, "2026-09-15");
  assert.equal(g.treffer.besetzung.mitglieder, 19);
  assert.equal(g.treffer.besetzung.status, "Fraktion abgeleitet");
  assert.equal(a.treffer.besetzung, undefined);
});

test("erklaere_begriff und datenstand", async () => {
  const t = tools();
  const b = await t.run("erklaere_begriff", { begriff: "Bürgerantrag" });
  assert.match(b.eintraege[0].fundstelle, /§ 24 GO NRW/);
  assert.equal((await t.run("erklaere_begriff", { begriff: "vertagt" })).eintraege[0].begriff, "vertagt");
  assert.equal((await t.run("erklaere_begriff", { begriff: "Quantenpolitik" })).gefunden, false);
  const d = await t.run("datenstand");
  assert.equal(d.heute, "2026-10-18");
  assert.equal(d.papers, 3);
});

test("suche_bebauungsplan: Planchronik mit Soll-Schritten, Liste nach Ortsteil", async () => {
  const t = tools();
  const r = await t.run("suche_bebauungsplan", { nummer: "6122-1" });
  assert.equal(r.plaene[0].rechtskraeftig_seit, "2025-06-04");
  assert.deepEqual(r.verfahrensschritte.map((s) => s.status), ["abgeleitet", "soll", "belegt"]);
  assert.equal(r.verfahrensschritte[0].vorlagen[0].drucksache, "190535");
  assert.equal(r.vorlagen.treffer_gesamt, 1);
  assert.equal((await t.run("suche_bebauungsplan", { ortsteil: "Dransdorf" })).items[0].nummer, "6122-1");
  assert.equal((await t.run("suche_bebauungsplan", { stichwort: "Grootestraße" })).treffer_gesamt, 1);
  assert.ok((await t.run("suche_bebauungsplan", { nummer: "9999-9" })).fehler);
});

test("suche_baustellen: Straße, Drucksache, Umkreis, beendete nur auf Wunsch", async () => {
  const t = tools();
  const r = await t.run("suche_baustellen", { ort: "Siemensstraße" });
  assert.equal(r.items[0].stand, "laufend");
  assert.match(r.items[0].moegliche_umsetzung[0].evidenz, /kein Beleg/);
  assert.equal((await t.run("suche_baustellen", { drucksache: "240553" })).items[0].baustelle_id, "9746");
  assert.equal((await t.run("suche_baustellen", {})).treffer_gesamt, 2);
  assert.equal((await t.run("suche_baustellen", { auch_beendete: true })).treffer_gesamt, 3);
  const near = await t.run("suche_baustellen", { lat: 50.73, lon: 7.0713, radius_m: 200 });
  assert.deepEqual(near.items.map((x) => x.baustelle_id), ["9746"]);
  const fremd = await t.run("suche_baustellen", { ort: "Kölnstraße" });
  assert.equal(fremd.items[0].anderer_traeger, true);
  assert.equal(fremd.items[0].stand, "geplant");
});

test("hole_kontext: Ortsteil mit Stadtbezirk, Stadtbezirk mit ganz Bonn, Quelle und Stand, kleine Ortsteile", async () => {
  const t = tools();
  const r = await t.run("hole_kontext", { gebiet: "Ortsteil Endenich" });
  assert.equal(r.gebiet, "Endenich");
  assert.equal(r.ebene, "ortsteil");
  assert.equal(r.vergleich_mit, "Stadtbezirk Bonn");
  assert.equal(r.evidenz, "abgeleitet");
  const miete = r.kennzahlen.find((k) => k.kennzahl === "durchschnittliche Nettokaltmiete");
  assert.deepEqual([miete.wert, miete.vergleich, miete.einheit, miete.stand, miete.lizenz], [10.12, 9.58, "€/m²", "2022-05-15", "dl-de/by-2.0"]);
  assert.ok(r.hinweise.some((h) => /kein Beleg/.test(h) && /keine Rangfolge/.test(h)));
  const bez = await t.run("hole_kontext", { gebiet: "Stadtbezirk Bonn", kennzahlen: ["hitze"] });
  assert.equal(bez.ebene, "stadtbezirk");
  assert.equal(bez.vergleich_mit, "ganz Bonn");
  assert.deepEqual(bez.kennzahlen.map((k) => [k.wert, k.vergleich]), [[67.3, 55.3]]);
  const bonn = await t.run("hole_kontext", { gebiet: "ganz Bonn" });
  assert.equal(bonn.ebene, "stadt");
  assert.ok(!("vergleich" in bonn.kennzahlen[0]));
  const klein = await t.run("hole_kontext", { gebiet: "Hardthöhe" });
  assert.equal(klein.kennzahlen.find((k) => k.kennzahl === "Hitze").wert, null);
  assert.ok(klein.hinweise.some((h) => /Unter 100 Einwohnern/.test(h)));
  const zentrum = await t.run("hole_kontext", { gebiet: "zentrum" });
  assert.equal(zentrum.gebiet, "Bonn-Zentrum");
  const brw = zentrum.kennzahlen.find((k) => /Bodenrichtwert/.test(k.kennzahl));
  assert.equal(brw.anteil_einwohner_in_zone, 34.2);
  assert.match(brw.hinweis, /34 % der Einwohner/);
  assert.ok((await t.run("hole_kontext", { gebiet: "Atlantis" })).fehler);
});

test("Fehler und Begrenzung", async () => {
  const t = tools();
  assert.ok((await t.run("gibt_es_nicht", {})).fehler);
  const broken = createTools({ load: async () => { throw new Error("offline"); } });
  assert.match((await broken.run("datenstand")).fehler, /nicht geladen/);
  const big = fit({ treffer: Array.from({ length: 500 }, (_, i) => ({ drucksache: String(i), titel: "x".repeat(100) })) });
  assert.ok(big.gekuerzt && JSON.stringify(big).length <= MAX_CHARS);
});

// --- Lauf gegen den echten Export ----------------------------------------------------------------------------
const REAL = await access(new URL("bonn/chat/datenstand.json", ROOT)).then(() => true, () => false);

test("echter Export: alle Werkzeuge, Größe, Datenschutz", { skip: !REAL && "kein Export unter data/export/bonn" }, async () => {
  const t = createTools({ today: "2026-10-18", load: async (p) => JSON.parse(await readFile(new URL(p, ROOT), "utf8")) });
  const calls = [
    ["suche_vorlagen", { stichwort: "Endenicher Straße" }], ["suche_vorlagen", { ortsteil: "Endenich", thema: "verkehr" }],
    ["hole_vorlage", { drucksache: "261798" }], ["hole_prozesslinie", { drucksache: "261798" }],
    ["suche_ort", { ort: "Endenich" }], ["suche_ort", { lat: 50.7295, lon: 7.0614 }],
    ["liste_sitzungen", {}], ["hole_gremium_oder_amt", { name: "Rat" }], ["erklaere_begriff", { begriff: "vertagt" }], ["datenstand", {}],
    ["suche_bebauungsplan", { nummer: "6122-1" }], ["suche_bebauungsplan", { ortsteil: "Endenich" }],
    ["hole_kontext", { gebiet: "Endenich" }], ["hole_kontext", { gebiet: "Beuel" }], ["hole_kontext", { gebiet: "ganz Bonn" }],
  ];
  if (await access(new URL("bonn/baustellen.json", ROOT)).then(() => true, () => false)) calls.push(["suche_baustellen", { stadtbezirk: "Bonn" }]);
  for (const [n, a] of calls) {
    const r = await t.run(n, a);
    assert.ok(!r.fehler, `${n}: ${r.fehler}`);
    assert.ok(JSON.stringify(r).length <= MAX_CHARS, n);
  }
  // Titel aus der Einwohnerschaft: keine Zahl direkt hinter einer Straßen-Endung
  const rx = /(straße|strasse|weg|platz|gasse|allee)\s+\d/i;
  for (const art of ["Anregungen und Beschwerden", "Bürgerantrag § 24 GO - Öffentlich", "Einwohnerfrage"]) {
    const first = await t.run("suche_vorlagen", { vorlagenart: art });
    for (let seite = 1; seite <= first.seiten; seite++) {
      const r = await t.run("suche_vorlagen", { vorlagenart: art, seite });
      for (const x of r.treffer) assert.doesNotMatch(x.titel, rx, `${x.drucksache}: ${x.titel}`);
    }
  }
});

// Aufzeichnungen (Ratstranskripte, bonn.biz): nur Verweise, nur YouTube-Adressen, keine Inhalte (transkripte/KONZEPT.md)
test("suche_aufzeichnungen: Sitzungen mit Video, Suchlink, keine fremden Adressen", async () => {
  const zeit = { meetings: [
    { date: "2026-03-12", gremium: "Rat", name: "Sitzung des Rates", source_object: "o/m/10", video: "https://www.youtube.com/watch?v=abc" },
    { date: "2026-05-07", gremium: "Rat", name: "Sitzung des Rates", source_object: "o/m/11", video: "https://example.org/fremd" },
    { date: "2026-06-01", gremium: "Bezirksvertretung Bonn", name: "Sitzung der Bezirksvertretung Bonn", source_object: "o/m/12" },
  ] };
  const t = createTools({ today: "2026-10-18", load: async (p) => (p === "bonn/zeit.json" ? structuredClone(zeit) : FILES[p]) });
  const r = await t.run("suche_aufzeichnungen", { stichwort: "Nordbrücke & Co" });
  assert.deepEqual(r.sitzungen.map((m) => [m.quelle_id, m.aufzeichnung]), [["o/m/10", "https://www.youtube.com/watch?v=abc"]]);
  assert.equal(r.transkript_suche, "https://bonn.biz/ratstranskripte?q=Nordbr%C3%BCcke%20%26%20Co");
  assert.match(r.hinweise.join(" "), /nicht amtlich/);
  const ohne = await t.run("suche_aufzeichnungen", {});
  assert.equal(ohne.transkript_suche, "https://bonn.biz/ratstranskripte");
  const l = await t.run("liste_sitzungen", { zeitraum: "vergangene" });
  assert.equal(l.sitzungen.find((m) => m.quelle_id === "o/m/10").aufzeichnung, "https://www.youtube.com/watch?v=abc");
  assert.equal(l.sitzungen.find((m) => m.quelle_id === "o/m/11").aufzeichnung, undefined);
});
