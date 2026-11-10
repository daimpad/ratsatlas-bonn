// Browser-Prüfung der Strukturdaten (strukturdaten/PHASE3.md, Entscheidungen 10.11.2026): Flächen der 65 statistischen
// Bezirke nach einer Kennzahl, Jahr und Stufen in der Adresse, Tabelle (zuerst nach Nummer, sortierbar), Steckbrief für
// einen sauber zusammengesetzten und einen geteilten Ortsteil sowie für ganz Bonn mit dem Vergleich der Städte;
// Barrierefreiheit (axe, WCAG 2.1 A und AA) bei 1440 und 390 px.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const SITE = process.env.SITE || "http://localhost:8765/";
const AXE = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");
let browser;
before(async () => { browser = await chromium.launch(); });
after(async () => { await browser?.close(); });

async function axe(page) {
  if (!(await page.evaluate(() => "axe" in window))) await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => (await window.axe.run(document, { runOnly: ["wcag2a", "wcag2aa"] }))
    .violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.html.slice(0, 100)).join(" | ")}`));
}

test("Flächen der statistischen Bezirke, Jahr in der Adresse, Tabelle", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(SITE + "?flaechen=struktur-i23", { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-gebiete-pane path").length === 65);
  await page.evaluate(() => { document.querySelector(".nav-legend").open = true; });
  assert.match(await page.locator(".nav-legend > summary").textContent(), /Ausländeranteil/);
  assert.equal(await page.locator("#nav-metric").inputValue(), "struktur-i23");
  await page.selectOption("#s-jahr", "2016");
  await page.waitForFunction(() => location.search.includes("sjahr=2016"));
  await page.selectOption("#s-stufen", "fest");
  await page.waitForFunction(() => location.search.includes("sstufen=fest"));
  await page.evaluate(() => { document.querySelector("#s-tabelle-acc").open = true; });
  const erste = await page.locator("#s-tabelle tbody tr th").first().textContent();
  assert.match(erste, /^110 /, "Vorgabe: Reihenfolge nach Nummer, keine Rangfolge");
  await page.locator('[data-ssort="wert"]').click();
  assert.equal(await page.locator('#s-tabelle th[aria-sort="descending"]').count(), 1);
  assert.equal(await page.locator("#s-tabelle tbody tr").count(), 65);
  assert.deepEqual(await axe(page), []);
  // zurück zur Zahl der Vorlagen: Bezirke weg, Stadtbezirke wieder da
  await page.selectOption("#nav-metric", "");
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-gebiete-pane path").length < 65);
  assert.ok(!(await page.evaluate(() => location.search.includes("sjahr"))));
  assert.deepEqual(errors, []);
  await page.close();
});

test("Steckbrief: Endenich (zwei Bezirke), Beuel-Mitte (geteilt), ganz Bonn mit Vergleich", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  const offen = async () => {
    await page.locator('.toggle[data-panel="panel-list"]').click();
    await page.waitForSelector("#struktur-box:not([hidden])");
    await page.evaluate(() => { document.querySelector("#struktur-box").open = true; });
    return page.locator("#struktur-box");
  };
  await page.goto(SITE + "?gebiet=ortsteil:endenich", { waitUntil: "networkidle" });
  let box = await offen();
  assert.match(await box.textContent(), /Strukturdaten zu Endenich/);
  assert.match(await box.textContent(), /Statistische Bezirke in Endenich/);
  assert.ok(await box.locator("svg.s-linie").count() > 0);
  await page.goto(SITE + "?gebiet=ortsteil:beuel-mitte", { waitUntil: "networkidle" });
  box = await offen();
  assert.match(await box.textContent(), /decken sich nicht mit Beuel-Mitte/);
  await page.goto(SITE, { waitUntil: "networkidle" });
  box = await offen();
  const t = await box.textContent();
  assert.match(t, /Bonn, Köln und Wuppertal im Vergleich/);
  assert.match(t, /Wegweiser Kommune/);
  assert.deepEqual(await axe(page), []);
  await page.close();
});

test("Strukturdaten auf dem Telefon, ohne Verstöße", async () => {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, bypassCSP: true });
  await page.goto(SITE + "?flaechen=struktur-i9&gebiet=ortsteil:endenich", { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-gebiete-pane path").length === 65);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  assert.deepEqual(await axe(page), []);
  await page.close();
});
