// Browser-Prüfung der Seiten je Vorgang (Entscheidungen 09.11.2026): Link „Seite zu dieser Vorlage“ im Vorgang der Karte,
// statische Seite ohne Skripte mit Beratungsfolge, Rückweg zur Karte; Barrierefreiheit (axe, WCAG 2.1 A und AA) bei 1440
// und 390 px.
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

test("Vorgang auf der Karte → eigene Seite → zurück zur Karte", async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(SITE + "?gebiet=ortsteil:endenich", { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelectorAll("#papers button[data-ref]").length > 0);
  await page.locator('.toggle[data-panel="panel-list"]').click();
  // die jüngste Vorlage mit Seite (Liste nach Datum, neueste zuerst; Vorlagen der Einwohnerschaft haben keine)
  const refs = await page.locator("#papers button[data-ref]").evaluateAll((bs) => bs.map((b) => b.dataset.ref));
  let link;
  for (const ref of refs.slice(0, 40)) {
    await page.locator(`#papers button[data-ref="${ref}"]`).click();
    await page.waitForFunction((r) => document.querySelector("#detail")?.textContent.includes(r), ref);
    link = page.locator('#detail a[href^="vorgang/"]');
    if (await link.count()) break;
  }
  assert.ok(link && await link.count(), "kein Vorgang mit Seite unter den ersten 40");
  const href = await link.getAttribute("href");
  assert.match(href, /^vorgang\/[a-z0-9-]+\/$/);
  assert.equal(await link.textContent(), "Seite zu dieser Vorlage");
  await link.click();
  await page.waitForURL((u) => u.pathname.endsWith(href));
  assert.equal(await page.locator("h2", { hasText: "Beratungsfolge" }).count(), 1);
  assert.equal(await page.locator("script").count(), 0);
  assert.deepEqual(await axe(page), []);
  await page.locator(".pb-aktionen a", { hasText: "Auf der Karte öffnen" }).click();
  await page.waitForFunction(() => document.querySelector("#detail-heading")?.textContent === "Vorgang");
  assert.deepEqual(errors, []);
  await page.close();
});

test("Seite je Vorgang auf dem Telefon, ohne Verstöße", async () => {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, bypassCSP: true });
  const sitemap = await (await page.request.get(SITE + "sitemap-vorgaenge.xml")).text();
  const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  assert.ok(urls.length > 100, `nur ${urls.length} Seiten`);
  // eine Seite mit Ergebnis in der Beratungsfolge und eine aus der Mitte der Liste
  for (const url of [urls.at(-1), urls[Math.floor(urls.length / 2)]]) {
    const res = await page.goto(url.replace(/^https?:\/\/[^/]+\//, SITE));
    assert.equal(res.status(), 200, url);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `waagrechter Bildlauf: ${url}`);
    assert.deepEqual(await axe(page), [], url);
  }
  await page.close();
});
