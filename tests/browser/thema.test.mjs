// Browser-Prüfung der Themenseiten (pipeline/prozessbild.py, site/thema.js): Kunst und Kultur mit Detailfeld
// zu Punkt und Sitzung, Esc, Schalter der Stränge, Auswahl im Seitenlink; Verkehr und Mobilität mit Stadtbezirken
// und Übersicht thema/; Barrierefreiheit mit axe-core
// (WCAG 2.1 A und AA). Erwartet die zusammengestellte Seite mit dem Schritt seo unter SITE.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const SITE = process.env.SITE || "http://localhost:8765/";
const SEITE = SITE + "thema/kunst-und-kultur/";
const AXE = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");
let browser;

before(async () => { browser = await chromium.launch(); });
after(async () => { await browser?.close(); });

async function open(hash = "", { width = 1440, height = 900 } = {}) {
  const page = await browser.newPage({ viewport: { width, height }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !/404|Failed to load resource/.test(m.text())) page.errors.push(m.text()); });
  await page.goto(SEITE + hash, { waitUntil: "networkidle" });
  return page;
}

async function axe(page) {
  await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => (await window.axe.run(document, { runOnly: ["wcag2a", "wcag2aa"] }))
    .violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.html.slice(0, 100)).join(" | ")}`));
}

const feld = (page) => page.evaluate(() => ({
  offen: !document.getElementById("pb-detail").hidden,
  titel: document.getElementById("pb-detail-titel")?.textContent || "",
  hash: location.hash,
}));

test("Themenseite: Punkt öffnet das Detailfeld, Esc schließt es, ohne Verstöße", async () => {
  const page = await open();
  const punkt = page.locator("a.pb-ziel[data-ziel^='punkt-']").first();
  const ref = await punkt.evaluate((a) => JSON.parse(document.getElementById("pb-daten").textContent)
    .punkte[a.dataset.ziel.slice(6)].reference);
  await punkt.click();
  let f = await feld(page);
  assert.ok(f.offen, "Detailfeld offen");
  assert.ok(f.titel.endsWith(ref), `Titel ${f.titel} nennt ${ref}`);
  assert.equal(new URLSearchParams(f.hash.slice(1)).get("auswahl"), ref);
  assert.match(await page.locator("#pb-ansage").textContent(), /^Ausgewählt: /);
  assert.ok(await page.locator("#pb-detail .pb-abgeleitet").count() > 0, "Strang als abgeleitet gekennzeichnet");
  assert.deepEqual(await axe(page), []);
  await page.keyboard.press("Escape");
  f = await feld(page);
  assert.equal(f.offen, false);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.ziel), await punkt.getAttribute("data-ziel"));
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseite: Sitzung per Tastatur, Schalter der Stränge, Zustand im Seitenlink", async () => {
  const page = await open("", { width: 390, height: 800 });
  await page.locator("a.pb-ziel[data-ziel='sitzung-0']").focus();
  await page.keyboard.press("Enter");
  const f = await feld(page);
  assert.ok(f.offen && f.titel, "Detailfeld zur Sitzung");
  assert.ok(await page.locator("#pb-detail a", { hasText: "Kalender" }).count() === 1);
  const schalter = page.locator(".pb-schalter").first();
  const strang = await schalter.getAttribute("data-strang");
  await schalter.click();
  assert.equal(await schalter.getAttribute("aria-pressed"), "false");
  assert.match(await page.evaluate(() => location.hash), /^#auswahl=sitzung-0&straenge=/);
  const gedimmt = await page.locator(`a.pb-ziel.pb-gedimmt[data-strang='${strang}']`).count();
  assert.equal(gedimmt, await page.locator(`a.pb-ziel[data-strang='${strang}']`).count());
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseite: Link mit Auswahl und Strängen stellt den Zustand her", async () => {
  const page = await open("#auswahl=phase-1&straenge=haushalt");
  const f = await feld(page);
  assert.ok(f.offen, "Detailfeld zur Phase");
  const zustand = await page.$$eval(".pb-schalter", (bs) => bs.map((b) => `${b.dataset.strang}=${b.getAttribute("aria-pressed")}`));
  assert.ok(zustand.includes("haushalt=true") && zustand.every((z) => z.startsWith("haushalt") || z.endsWith("false")),
    zustand.join(" "));
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseite Verkehr: Stränge nach Stadtbezirk, Übersicht thema/, ohne Verstöße", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  await page.goto(SITE + "thema/verkehr-und-mobilitaet/", { waitUntil: "networkidle" });
  assert.ok(await page.locator("#weitere ~ details summary").count() >= 2, "weitere Vorlagen je Stadtbezirk");
  assert.ok(await page.locator(".pb-schalter[data-strang='nordbruecke']").isVisible(), "Schalter Nordbrücke");
  await page.locator("a.pb-ziel[data-ziel^='punkt-']").first().click();
  assert.equal(await page.locator("#pb-detail").isHidden(), false);
  assert.deepEqual(await axe(page), []);
  await page.goto(SITE + "thema/", { waitUntil: "networkidle" });
  assert.equal(await page.locator("a[href='../thema/verkehr-und-mobilitaet/']").count(), 1);
  assert.equal(await page.locator("a[href='../thema/kunst-und-kultur/']").count(), 1);
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseite Wohnen: Stränge, weitere nach Stadtbezirk, Verweis auf die Planebene, ohne Verstöße", async () => {
  const page = await browser.newPage({ viewport: { width: 1024, height: 900 }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  await page.goto(SITE + "thema/wohnen-und-bauen/", { waitUntil: "networkidle" });
  for (const k of ["turbo", "bebauungsplan", "wohnraum", "denkmal", "weitere"]) {
    assert.ok(await page.locator(`.pb-schalter[data-strang='${k}']`).count(), "Schalter " + k);
  }
  assert.ok(await page.locator("#weitere ~ details summary").count() >= 2, "weitere je Stadtbezirk");
  assert.equal(await page.locator("a[href='../../?plaene=1']").count(), 1);
  await page.locator("a.pb-ziel[data-ziel^='punkt-']").first().click();
  assert.equal(await page.locator("#pb-detail").isHidden(), false);
  assert.deepEqual(await axe(page), []);
  await page.goto(SITE + "thema/", { waitUntil: "networkidle" });
  assert.equal(await page.locator("a[href='../thema/wohnen-und-bauen/']").count(), 1);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseite Klima: Stränge, Verweise auf die Karte, ohne Verstöße", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  await page.goto(SITE + "thema/klima-und-umwelt/", { waitUntil: "networkidle" });
  for (const k of ["klimaschutz", "anpassung", "gruen", "abfall", "weitere"]) {
    assert.ok(await page.locator(`.pb-schalter[data-strang='${k}']`).count(), "Schalter " + k);
  }
  assert.equal(await page.locator(".thema-kopf .kachel-symbol").count(), 1, "Symbol im Kopf");
  assert.equal(await page.locator(".thema-kopf a.thema-alle[href='../../thema/']").count(), 1, "Link Alle Themen");
  assert.equal(await page.locator("a[href='../../?flaechen=kontext-hitze']").count(), 1);
  assert.equal(await page.locator("a[href='../../?ebenen=uesg']").count(), 1);
  await page.locator("a.pb-ziel[data-ziel^='punkt-']").first().click();
  assert.equal(await page.locator("#pb-detail").isHidden(), false);
  assert.deepEqual(await axe(page), []);
  // Übersicht thema/: Kacheln mit Symbol, Strängen und Sitzung; die ganze Kachel führt zur Themenseite
  await page.goto(SITE + "thema/", { waitUntil: "networkidle" });
  assert.ok(await page.locator(".kachel").count() >= 5, "Kacheln");
  assert.equal(await page.locator(".kachel .kachel-symbol").count(), await page.locator(".kachel").count());
  assert.deepEqual(await axe(page), []);
  await page.locator(".kachel", { hasText: "Klima und Umwelt" }).click({ position: { x: 20, y: 20 } });
  await page.waitForURL(/klima-und-umwelt/);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseite Schule: Stränge, Detailfeld, ohne Verstöße", async () => {
  const page = await browser.newPage({ viewport: { width: 390, height: 900 }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  await page.goto(SITE + "thema/schule-und-bildung/", { waitUntil: "networkidle" });
  for (const k of ["schulweg", "bau", "plaetze", "weitere"]) {
    assert.ok(await page.locator(`.pb-schalter[data-strang='${k}']`).count(), "Schalter " + k);
  }
  await page.locator("a.pb-ziel[data-ziel^='punkt-']").first().click();
  assert.equal(await page.locator("#pb-detail").isHidden(), false);
  assert.deepEqual(await axe(page), []);
  await page.goto(SITE + "thema/", { waitUntil: "networkidle" });
  assert.equal(await page.locator("a[href='../thema/schule-und-bildung/']").count(), 1);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenseiten: Haushalt im Produktbereich, Ist und Plan getrennt, auch auf dem Telefon als Tabelle", async () => {
  const page = await browser.newPage({ viewport: { width: 390, height: 900 }, bypassCSP: true });
  for (const [pfad, pb] of [["kunst-und-kultur", "04"], ["verkehr-und-mobilitaet", "12"], ["schule-und-bildung", "03"],
    ["wohnen-und-bauen", "10"], ["klima-und-umwelt", "13"]]) {
    await page.goto(SITE + `thema/${pfad}/`, { waitUntil: "networkidle" });
    assert.match(await page.locator("#haushalt-produktbereich").textContent(), new RegExp(`Produktbereich ${pb} `));
    const tabelle = page.locator("table.haushalt");
    assert.match(await tabelle.locator("thead").textContent(), /Ergebnis \(Ist\).*Ansatz \(Plan\)/s);
    assert.ok(await tabelle.locator("tbody tr").count() >= 5, pfad);
    assert.equal(await tabelle.locator("thead").isVisible(), true, "Kopf auch mobil sichtbar");
    assert.doesNotMatch(await tabelle.textContent(), /2027|2028|2029/, "keine Finanzplanung");
  }
  assert.deepEqual(await axe(page), []);
  await page.close();
});

test("Themenseiten: Wer berät mit (Fachausschuss, Fraktion abgeleitet), Link in den Reiter „Prozesse“", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  await page.goto(SITE + "thema/verkehr-und-mobilitaet/", { waitUntil: "networkidle" });
  const h = page.locator("#fachausschuss");
  assert.match(await h.textContent(), /Ausschuss für Mobilität und Verkehr/);
  const text = await page.locator("#fachausschuss + p").textContent();
  assert.match(text, /\d+ Mitglieder.*abgeleitet/s);
  const link = page.locator("a[href*='prozesse=gremien']");
  assert.equal(await link.count(), 1);
  await link.click();
  await page.waitForFunction(() => !document.querySelector("#panel-prozesse")?.hidden && /Besetzung/.test(document.querySelector("#panel-prozesse").textContent));
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

// sichtbare Treemaps der Seite haushalt/ (aria-label bis zum Doppelpunkt, mit voller Angabe auf Wunsch)
// nur die umschaltbaren Treemaps (Aufwendungen und Ebenen); der Zuschussbedarf unter der Tabelle steht für sich
const treemaps = (page, voll = false) => page.evaluate((voll) => [...document.querySelectorAll(".hh-wahl .hh-svg")]
  .filter((s) => s.getBoundingClientRect().height > 0).map((s) => voll ? s.getAttribute("aria-label") : s.getAttribute("aria-label").split(":")[0]), voll);

test("Haushalt auf einen Blick: Treemap je Ansicht ohne Skript umschaltbar, Zeile der Tabelle als Sprungziel, ohne Verstöße", async () => {
  for (const [width, format] of [[1440, "breit"], [390, "hoch"]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, bypassCSP: true });
    await page.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
    assert.deepEqual(await treemaps(page), ["Plan 2026"]);
    assert.equal(await page.locator(`.hh-haupt .hh-v0 .hh-${format} a`).count(), 17);
    await page.locator('label[for="hh-ist2023"]').click();
    assert.deepEqual(await treemaps(page), ["Ist 2023"]);
    await page.goto(SITE + "haushalt/#pb-04");   // Sprungziel der Themenseiten
    assert.match(await page.locator("tr:target").textContent(), /Kultur und Wissenschaft.*Themenseite/s);
    assert.match(await page.locator("#tabelle + p + table .hh-summe").textContent(), /1\.797,0 Mio\. €/);   // Plan 2025 = Gesamtergebnisplan
    // Erträge und Ergebnis (02.11.2026): Zuschussbedarf mit 14 Flächen, Sprung in die Ergebnistabelle
    assert.equal(await page.locator(`.hh-erg .hh-${format} a`).count(), 14);
    await page.goto(SITE + "haushalt/#erg-03");
    assert.match(await page.locator("tr:target").textContent(), /Schulträgeraufgaben.*−152 € je Einwohner/s);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(await axe(page), []);
    await page.close();
  }
});

// Ebenen 2 und 3 (freigegeben 28.10.2026; tests.yml erzeugt die Seite zusätzlich mit HAUSHALT_EBENEN=vorschau)
const ebenen = (page) => page.evaluate(() => [...document.querySelectorAll(".hh-ebene")]
  .filter((s) => s.getBoundingClientRect().height > 0).map((s) => s.id));

test("Haushalt: Klick führt zu den Produktgruppen und weiter zu den Aufwandsarten, Brotkrumen zurück, ohne Verstöße", async () => {
  for (const [width, format] of [[1440, "breit"], [390, "hoch"]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, bypassCSP: true });
    page.errors = [];
    page.on("pageerror", (e) => page.errors.push(String(e)));
    await page.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
    assert.equal(await page.locator('section.hh-ebene[id^="zoom-"]').count(), 17, "Ebenen fehlen: Seite mit HAUSHALT_EBENEN=vorschau erzeugen");
    assert.deepEqual(await ebenen(page), []);
    // Ebene 2: Produktgruppen des Bereichs
    await page.locator(`.hh-haupt .hh-v0 .hh-${format} a[href="#zoom-04"]`).click();
    assert.deepEqual(await ebenen(page), ["zoom-04"]);
    assert.equal(await page.locator(".hh-haupt").isVisible(), false, "Treemap der Produktbereiche ausgeblendet");
    assert.equal(await page.locator("#zoom-04 h2").textContent(), "Produktbereich 04 Kultur und Wissenschaft");
    assert.deepEqual(await treemaps(page, true), ["Plan 2026: Produktgruppen im Produktbereich 04 Kultur und Wissenschaft, zusammen 92,8 Mio. €"]);
    assert.ok(await page.locator('label[for="hh-ist2023"]').evaluate((l) => l.getBoundingClientRect().top >= 0), "Auswahlknöpfe sichtbar");
    assert.equal(await page.locator("#zoom-04 .hh-balken:not(.hh-eb)").filter({ visible: true }).count(), 1, "ein Balken der Aufwandsarten je Ansicht");
    await page.locator('label[for="hh-ist2023"]').click();
    assert.match((await treemaps(page, true))[0], /^Ist 2023: Produktgruppen im Produktbereich 04/);
    // Stelle der Ansicht Ist 2023 (dritte, mit Ist 2024 aus dem Jahresabschluss vierte)
    const v = await page.locator(".hh-radio").evaluateAll((rs) => rs.findIndex((r) => r.id === "hh-ist2023"));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(await axe(page), []);
    // Ebene 3: Aufwandsarten der Produktgruppe als Kacheln (site/haushalt.js zeichnet sie aus den Balken)
    await page.locator(`#zoom-04 .hh-v${v} .hh-${format} a[href="#pg-1-04-07"]`).click();
    assert.deepEqual(await ebenen(page), ["pg-1-04-07"]);
    assert.equal(await page.locator("#pg-1-04-07 h2").textContent(), "Produktgruppe 1.04.07 Stadtarchiv");
    assert.match(await page.locator("#pg-1-04-07 .hh-pfad").textContent(), /^Alle Produktbereiche › 04 Kultur und Wissenschaft › 1\.04\.07 Stadtarchiv$/);
    assert.match(await page.locator("#pg-1-04-07").textContent(), /Name in Haushaltsplan 2023\/2024: Z\. f\. Stadtgesch\. u\. Erinnerungskulturen/);
    assert.deepEqual(await treemaps(page, true), ["Ist 2023: Aufwandsarten der Produktgruppe 1.04.07 Stadtarchiv"]);
    assert.equal(await page.locator(`#pg-1-04-07 .hh-v${v} .hh-${format} rect`).count(), 5, "Transfers leer: fünf Kacheln");
    assert.equal(await page.locator("#pg-1-04-07 .hh-balken:not(.hh-eb)").filter({ visible: true }).count(), 0, "Balken nur ohne Skript");
    assert.equal(await page.locator("#pg-1-04-07 > table:first-of-type tbody tr").count(), 7);   // ohne die Liste der Maßnahmen
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(await axe(page), []);
    // Brotkrumen: zurück zu Ebene 2, dann zu allen Produktbereichen; die Ansicht bleibt gewählt
    await page.locator('#pg-1-04-07 .hh-pfad a[href="#zoom-04"]').click();
    assert.deepEqual(await ebenen(page), ["zoom-04"]);
    await page.locator('#zoom-04 .hh-pfad a[href="#produktbereiche"]').click();
    assert.deepEqual(await ebenen(page), []);
    assert.deepEqual(await treemaps(page), ["Ist 2023"], "Ansicht bleibt gewählt");
    assert.deepEqual(page.errors, []);
    await page.close();
  }
});

test("Haushalt: Zoom beim Wechsel der Ebene, ohne Bewegung bei reduzierter Bewegung, ohne Skript Balken", async () => {
  // hashchange läuft nach dem Klick als eigene Aufgabe: auf die Bewegung warten statt sofort zu lesen
  const zoom = (page, soll) => page.waitForFunction((soll) => document.querySelector(".hh-wahl").dataset.zoom === soll, soll, { timeout: 5000 })
    .then(() => soll, () => page.locator(".hh-wahl").getAttribute("data-zoom"));
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  await page.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
  await page.locator('.hh-haupt .hh-v0 .hh-breit a[href="#zoom-04"]').click();
  assert.equal(await zoom(page, "hinein"), "hinein", "Kachel wächst");
  await page.goBack();   // heraus, auch mit dem Zurück des Browsers
  assert.deepEqual(await ebenen(page), []);
  assert.equal(await zoom(page, "heraus"), "heraus", "zurück auf die Kachel");
  await page.close();
  const ruhig = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true, reducedMotion: "reduce" });
  await ruhig.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
  await ruhig.locator('.hh-haupt .hh-v0 .hh-breit a[href="#zoom-04"]').click();
  assert.deepEqual(await ebenen(ruhig), ["zoom-04"]);
  await ruhig.waitForTimeout(300);   // hashchange ist gelaufen
  assert.equal(await ruhig.locator(".hh-wahl").getAttribute("data-zoom"), null, "ohne Animation");
  await ruhig.close();
  const ohne = await browser.newPage({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
  await ohne.goto(SITE + "haushalt/#pg-1-04-07");
  assert.equal(await ohne.locator("#pg-1-04-07 .hh-balken.hh-v0:not(.hh-eb)").isVisible(), true, "ohne Skript: Balken");
  assert.equal(await ohne.locator("#pg-1-04-07 svg").count(), 0);
  await ohne.close();
});

test("Haushalt: Begriffe, Grenzen und Quellen in zugeklappten Akkordeons", async () => {
  const page = await browser.newPage({ viewport: { width: 390, height: 900 }, bypassCSP: true });
  await page.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
  const mehr = page.locator("details.hh-mehr:not(.meta-acc)");   // Metaangaben je Abschnitt eigens eingeklappt (10.11.2026)
  assert.deepEqual(await mehr.locator("summary").allTextContents(), ["So lesen Sie die Zahlen", "Was diese Seite nicht zeigt", "Quellen, Prüfung und Lizenz"]);
  assert.deepEqual(await mehr.evaluateAll((ds) => ds.map((d) => d.open)), [false, false, false]);
  await page.locator("#lesen summary").focus();
  await page.keyboard.press("Enter");
  assert.match(await page.locator("#lesen").textContent(), /Kontenarten, keine Aufgaben/);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390);
  assert.deepEqual(await axe(page), []);
  await page.close();
});

test("Haushalt: Investitionsmaßnahmen je Produktgruppe aufklappbar, zehn größte unter Investitionen, ohne Verstöße", async () => {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, bypassCSP: true });
    await page.goto(SITE + "haushalt/#pg-1-12-01", { waitUntil: "networkidle" });
    const mn = page.locator("#pg-1-12-01 details.hh-mn");
    assert.equal(await mn.evaluate((d) => d.open), false);
    await mn.locator("summary").click();
    assert.match(await mn.textContent(), /Viktoriabrücke BN/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(await axe(page), []);
    await page.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
    assert.equal(await page.locator("#massnahmen + p + table tbody tr").count(), 10);
    await page.close();
  }
});

test("Haushalt: negative und leere Werte ohne Fläche und Balkenstück, 0 € nur in der Tabelle, Tastatur", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  await page.goto(SITE + "haushalt/#zoom-09", { waitUntil: "networkidle" });
  await page.locator('label[for="hh-ist2023"]').click();
  const v = await page.locator(".hh-radio").evaluateAll((rs) => rs.findIndex((r) => r.id === "hh-ist2023"));
  assert.equal(await page.locator(`#zoom-09 .hh-balken.hh-v${v} .hh-f15`).count(), 0, "negativ: kein Balkenstück");
  assert.match(await page.locator("#zoom-09").textContent(), /Negativ sind: Transferaufwendungen im Ist 2023 \(−84\.508 €\)/);
  assert.equal(await page.locator('#zoom-09 a[href="#pg-1-09-06"]').count(), 0, "0 €: ohne Fläche und ohne Ebene 3");
  assert.match(await page.locator("#zoom-09").textContent(), /1\.09\.06 Ortsbaurecht/);
  assert.deepEqual(await axe(page), []);
  await page.goto(SITE + "haushalt/", { waitUntil: "networkidle" });
  await page.locator('.hh-haupt .hh-v0 .hh-breit a[href="#zoom-16"]').focus();
  await page.keyboard.press("Enter");
  assert.deepEqual(await ebenen(page), ["zoom-16"]);
  assert.equal(await page.locator("#zoom-16 .hh-f11").count(), 0, "leer: kein Balkenstück für Personalaufwendungen");
  await page.keyboard.press("Tab");
  assert.equal(await page.evaluate(() => document.activeElement.getAttribute("href")), "#produktbereiche");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");   // erste Fläche der Produktgruppen
  assert.match((await ebenen(page))[0] || "", /^pg-1-16-/);
  await page.close();
});

test("Haushalt: Ertragsarten je Produktbereich und Produktgruppe (Vorschau), ohne Kacheln, ohne Verstöße", async () => {
  for (const [width, ziel] of [[1440, "zoom-03"], [390, "pg-1-11-03"]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, bypassCSP: true });
    await page.goto(SITE + `haushalt/#${ziel}`, { waitUntil: "networkidle" });
    const titel = page.locator(`#${ziel} h3`, { hasText: "Woher kommt das Geld?" });
    assert.equal(await titel.count(), 1, "Ertragsarten fehlen: Seite mit HAUSHALT_ERTRAGSARTEN=vorschau erzeugen");
    assert.equal(await titel.isVisible(), true);
    assert.equal(await page.locator(`#${ziel} .hh-balken.hh-eb`).filter({ visible: true }).count(), 1, "ein Balken je Ansicht");
    if (ziel.startsWith("pg-")) {   // Kacheln nur für die Aufwandsarten
      assert.equal(await page.locator(`#${ziel} .hh-kacheln`).filter({ visible: true }).count(), 1);
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
    assert.deepEqual(await axe(page), []);
    await page.close();
  }
});
