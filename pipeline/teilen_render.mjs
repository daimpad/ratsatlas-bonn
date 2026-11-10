// Bilder zum Teilen rendern (aufgerufen von pipeline/teilen.py): erst Bildschirmfotos der Seite (Vorschau unter
// auftraege.site), dann jede Komposition als PNG, für Druckformate zusätzlich in 3000 px Breite.
// Aufruf: node pipeline/teilen_render.mjs <Arbeitsordner mit auftraege.json>
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require("playwright")); } catch {
  ({ chromium } = require(join(process.cwd(), "tests/browser/node_modules/playwright")));
}

const dir = process.argv[2];
const auftraege = JSON.parse(readFileSync(join(dir, "auftraege.json"), "utf8"));
const browser = await chromium.launch();

for (const f of auftraege.fotos) {
  const page = await browser.newPage({ viewport: { width: f.w, height: f.h }, deviceScaleFactor: 3 });
  await page.goto(f.url, { waitUntil: "networkidle" });
  // Startfenster „Los geht's“ (Fläche Vorgang) einklappen, damit die Karte frei liegt
  await page.waitForTimeout(3000);
  const zu = page.locator('[data-close="panel-detail"]');
  if (await zu.isVisible().catch(() => false)) await zu.click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: f.datei });
  await page.close();
}

for (const s of auftraege.seiten) {
  for (const [scale, suffix] of [[1, ""], ...(s.druck ? [[s.druck, "-druck"]] : [])]) {
    const page = await browser.newPage({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: scale });
    await page.goto("file://" + s.html);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    await page.screenshot({ path: join(dir, `${s.name}${suffix}.png`) });
    await page.close();
  }
}
await browser.close();
