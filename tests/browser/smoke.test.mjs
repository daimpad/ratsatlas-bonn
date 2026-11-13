// Browser-Prüfung der fertigen Seite (Playwright, Chromium): Start mit der Übersicht über ganz Bonn, Navigation
// über die Flächen, Link mit Gebiet und Vorgang, Flächen „Prozesse“ und „Mitmachen in Bonn“, Kartenmenü mobil,
// Ratsassistent (erst beim Öffnen geladen), Tour.
// Barrierefreiheit mit axe-core (WCAG 2.1 A und AA). Erwartet die zusammengestellte Seite unter SITE
// (Standard http://localhost:8765/), siehe Workflow tests.yml.
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

// neue Seite; Fehler im Skript und in der Konsole werden gesammelt (fehlende Dateien, 404, zählen nicht)
async function open(path = "", { width = 1440, height = 900 } = {}) {
  const page = await browser.newPage({ viewport: { width, height }, bypassCSP: true });
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !/404|Failed to load resource/.test(m.text())) page.errors.push(m.text()); });
  await page.goto(SITE + path, { waitUntil: "networkidle" });
  // erst prüfen, wenn app.js gestartet ist (auf einem langsamen Server kann das nach „networkidle“ liegen)
  await page.waitForFunction(() => document.querySelector("#f-area")?.value);
  return page;
}

async function axe(page) {
  if (!(await page.evaluate(() => "axe" in window))) await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => (await window.axe.run(document, { runOnly: ["wcag2a", "wcag2aa"] }))
    .violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.html.slice(0, 100)).join(" | ")}`));
}

// Punkt auf der Karte, an dem eine Fläche der Navigation obenauf liegt (wie ein Klick mit der Maus)
async function areaPoint(page) {
  const scan = () => page.evaluate(() => {
    const o = [];
    for (let y = 100; y < innerHeight - 40; y += 15) for (let x = 20; x < innerWidth - 20; x += 15) {
      const el = document.elementFromPoint(x, y);
      if (el && el.closest(".leaflet-gebiete-pane path")) o.push({ x, y });
    }
    return o;
  });
  // erst klicken, wenn die Karte stillsteht: nach einem Klick zoomt sie in den Stadtbezirk; ein Punkt aus der
  // laufenden Bewegung trifft auf einem langsamen Rechner daneben (CI 02.11.2026)
  let pts = await scan();
  for (let i = 0; i < 20; i++) {
    await page.waitForTimeout(250);
    const next = await scan();
    if (JSON.stringify(next) === JSON.stringify(pts)) break;
    pts = next;
  }
  assert.ok(pts.length, "keine anklickbare Fläche auf der Karte");
  return pts[Math.floor(pts.length / 2)];
}

test("Start: Übersicht über ganz Bonn, Fenster „Los geht's“, ohne Verstöße", async () => {
  const page = await open();
  await page.waitForFunction(() => document.querySelectorAll(".nav-label-bz").length === 4);
  assert.equal(await page.locator("#detail-heading").textContent(), "Los geht's");
  assert.equal(await page.locator("#f-area").inputValue(), "bonn:alle");
  assert.equal(await page.locator("#f-area option:checked").textContent(), "Gebiet wählen");
  assert.equal(await page.locator('#f-area option[value="bonn:ganz"]').textContent(), "Ganz Bonn");
  // Start ohne Hinweistext und Schaltflächen; Legenden und Quellen eingeklappt übereinander oben links
  assert.equal(await page.locator("#detail .intro-actions").count(), 0);
  assert.deepEqual(await page.evaluate(() => [...document.querySelectorAll(".map-stack > details")].map((d) => [d.className, d.open])),
    [["nav-legend", false], ["map-legend", false], ["map-legend map-sources", false]]);
  assert.equal(await page.locator("#mega-ueber #sources").count(), 0, "Quellen nicht im Menü „Über“");
  assert.equal(await page.locator(".nav-label-bz").count(), 4, "Namen der vier Stadtbezirke");
  assert.ok(!/gebiet=/.test(page.url()), "die Übersicht schreibt kein Gebiet in die Adresse");
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Karte: Stadtbezirk anklicken, dann Ortsteil laden", async () => {
  const page = await open();
  let pt = await areaPoint(page);
  await page.mouse.click(pt.x, pt.y);
  await page.waitForFunction(() => document.querySelectorAll(".nav-label-ot").length > 0);
  pt = await areaPoint(page);
  await page.mouse.click(pt.x, pt.y);
  await page.waitForFunction(() => document.querySelector("#f-area").value.startsWith("ortsteil:"));
  // Liste des Ortsteils geladen („N von M Vorlagen“); einige Ortsteile wie Hardthöhe haben keine Vorlage mit
  // Ortsbezug, welcher getroffen wird, hängt vom Kartenausschnitt ab. Die leere Liste der Übersicht zählt nicht.
  await page.waitForFunction(() => /\d+ von \d+ Vorlagen/.test(document.querySelector("#count")?.textContent || ""));
  assert.match(page.url(), /gebiet=ortsteil/);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Link mit Gebiet: Liste, Vorgang mit Prozesslinie, ohne Verstöße", async () => {
  const page = await open("?gebiet=ortsteil:endenich");
  assert.equal(await page.locator("#f-area").inputValue(), "ortsteil:endenich");
  await page.waitForFunction(() => document.querySelectorAll("#papers button[data-ref]").length > 0);
  await page.locator('.toggle[data-panel="panel-list"]').click();
  const first = page.locator("#papers button[data-ref]").first();
  const ref = await first.getAttribute("data-ref");
  await first.click();
  await page.waitForFunction(() => document.querySelector("#detail-heading").textContent === "Vorgang");
  assert.ok(await page.locator("#detail .steps li").count() > 0, "Prozesslinie mit Stationen");
  // Drucksachen wie „260745-03 ST“ stehen kodiert im Anker (%20)
  assert.equal(decodeURIComponent(new URL(page.url()).hash.slice(1)), ref, "Drucksache in der Adresse");
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Themenebene: Flächen nach Anteil eines Themas, Zustand in der Adresse", async () => {
  const page = await open();
  await page.locator(".nav-legend > summary").click();
  await page.locator("#nav-metric").selectOption("verkehr");
  assert.match(page.url(), /flaechen=verkehr/);
  assert.match(await page.locator(".nav-legend summary").textContent(), /Verkehr/);
  // alte Beschriftungen blendet Leaflet 200 ms lang aus, bevor sie entfernt werden
  await page.waitForFunction(() => [...document.querySelectorAll(".nav-label-bz")].every((e) => /%$/.test(e.textContent)));
  assert.equal(await page.locator(".nav-label-bz").count(), 4);
  assert.deepEqual(await axe(page), []);
  await page.goto(SITE + "?flaechen=umwelt", { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelector("#nav-metric")?.value === "umwelt");
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Zahlen zum Gebiet: Flächen nach Kontextdaten, Steckbrief im Ortsteil", async () => {
  const page = await open();
  await page.locator(".nav-legend > summary").click();
  await page.locator("#nav-metric").selectOption("kontext-miete");
  assert.match(page.url(), /flaechen=kontext-miete/);
  assert.match(await page.locator(".nav-legend").textContent(), /Zensus 2022.*Stand 15\.05\.2022.*kein Urteil/s);
  await page.waitForFunction(() => [...document.querySelectorAll(".nav-label-bz")].every((e) => /€\/m²$/.test(e.textContent)));
  assert.deepEqual(await axe(page), []);
  // Steckbrief: Ortsteil neben dem Stadtbezirk, Kennzahlen in fester Reihenfolge
  await page.goto(SITE + "?gebiet=ortsteil:endenich", { waitUntil: "networkidle" });
  await page.waitForFunction(() => !document.querySelector("#kontext-box")?.hidden);
  // Link mit Gebiet: die Farbverläufe der Flächen sind vorhanden (Code-Prüfung 24.10.2026)
  await page.waitForFunction(() => document.querySelector("#nav-c0"));
  await page.locator('.toggle[data-panel="panel-list"]').click();
  await page.locator("#kontext-box > summary").click();
  const head = await page.locator("#kontext-box > table thead").textContent();
  assert.match(head, /Endenich.*Stadtbezirk Bonn/s);
  assert.match(await page.locator("#kontext-box > table tbody tr").first().textContent(), /Einwohner/);
  // Mängelmelder nur mit Archiv (anliegen.json): eigener Abschnitt, als Meldungen der Einwohnerschaft gekennzeichnet
  const an = await fetch(SITE + "data/export/bonn/anliegen.json");
  assert.equal(await page.locator("#kontext-box .anliegen").count(), an.ok ? 1 : 0);
  if (an.ok) assert.match(await page.locator("#kontext-box .anliegen").textContent(), /keine Ratsvorlagen.*Zusammen/s);
  assert.deepEqual(await axe(page), []);
  // Vorgang in genau einem Ortsteil: Kennzahlen passend zum Thema, als Einordnung gekennzeichnet
  const ende = (await (await fetch(SITE + "data/export/bonn/ortsteile/endenich.json")).json()).papers;
  const bau = ende.find((p) => (p.themes || [])[0]?.theme === "bauen" && p.locations.every((l) => l.method !== "vererbt" && l.ortsteil === "Endenich"));
  await page.goto(SITE + "?gebiet=ortsteil:endenich#" + encodeURIComponent(bau.reference), { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelector("#detail-heading").textContent === "Vorgang");
  const box = page.locator("#detail .kontext-vorgang");
  assert.match(await box.locator("h4").textContent(), /Zum Ortsteil Endenich.*abgeleitet/s);
  assert.match(await box.locator("tbody").textContent(), /Bodenrichtwert.*Nettokaltmiete/s);
  assert.match(await box.locator(".hint").textContent(), /kein Beleg für die Vorlage.*Stand/s);
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Zuschaltbare Flächen: erst beim Hineinzoomen, Legende mit Quelle, Zustand in der Adresse", async () => {
  const page = await open("?gebiet=ortsteil:beuel-mitte");
  assert.equal(await page.locator(".map-kx-uesg").isVisible(), false, "Ebenen erst nach „Ebenen“");
  await page.locator(".map-menu").click();
  await page.locator(".map-kx-uesg").click();
  await page.locator(".map-kx-brw").click();
  assert.match(page.url(), /ebenen=uesg%2Cbrw|ebenen=uesg,brw/);
  assert.match(await page.locator(".map-menu").textContent(), /Ebenen\s*2/, "Zahl der eingeschalteten Ebenen");
  const legend = page.locator(".map-legend:not(.map-sources)");
  await page.waitForFunction(() => /Überschwemmungsgebiet, festgesetzt/.test(document.querySelector(".map-legend").textContent));
  // ab Ortsteil-Zoom gezeichnet: Flächen in der eigenen Ebene, Stufen der Bodenrichtwerte in der Legende
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-kontextflaechen-pane path").length > 10);
  await page.waitForFunction(() => /€\/m²/.test(document.querySelector(".map-legend").textContent));
  assert.match(await legend.textContent(), /vorläufig gesichert.*Verbindlich sind die Karten des Landes.*dl-de\/zero-2\.0.*Wohnbauland.*BORIS NRW/s);
  assert.deepEqual(await axe(page), []);
  // herausgezoomt: keine Flächen, Hinweis in der Legende
  // je Klick das Ende der Animation abwarten: Klicks während der Animation rechnen vom selben Zoom aus (CI)
  for (let i = 0; i < 4; i++) {
    await page.locator(".leaflet-control-zoom-out").click();
    await page.waitForFunction(() => !document.querySelector(".leaflet-zoom-anim"));
    await page.waitForTimeout(300);
  }
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-kontextflaechen-pane path").length === 0);
  assert.match(await legend.textContent(), /hineinzoomen/);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Suche im Text der Dokumente: erst nach Klick, ohne Textausschnitt", async () => {
  const page = await open();
  const suche = await (await fetch(SITE + "data/export/bonn/suche.json")).json();
  // zwei Vorlagen, deren Titel das Suchwort nicht enthalten, als nachgebildete Treffer von OParl-Lite
  const word = "zzqxtest", hits = suche.rows.slice(0, 2).map((r) => r[0]);
  const asked = [];
  await page.route("https://oparl.bonn.machdenstaat.de/graphql", async (route) => {
    asked.push(JSON.parse(route.request().postData()));
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ data: { fileFullTextSearch: {
      totalCount: 2, pageInfo: { hasNextPage: false }, items: hits.map((reference) => ({ file: { papers: [{ reference }] } })) } } }) });
  });
  await page.locator("#q").fill(word);
  await page.waitForTimeout(400);
  assert.equal(asked.length, 0, "keine Anfrage vor dem Klick");
  await page.locator("#doc-search").click();
  await page.waitForFunction(() => /erwähn/.test(document.querySelector("#doc-status").textContent));
  assert.equal(asked.length, 1);
  assert.ok(!/snippet/.test(asked[0].query), "kein Textausschnitt angefragt");
  assert.match(await page.locator("#count").textContent(), /2 nur im Text der Dokumente/);
  assert.equal(await page.locator("#papers .doc-tag").count(), 2);
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Prozesse: Verfahren, Gremien und Ämter", async () => {
  for (const tab of ["verfahren", "gremien", "aemter"]) {
    const page = await open(`?prozesse=${tab}&ansicht=liste`);
    const panel = page.locator("#panel-prozesse");
    assert.ok(await panel.isVisible(), `Fläche Prozesse (${tab})`);
    assert.ok((await panel.textContent()).length > 500, `Inhalt im Reiter ${tab}`);
    assert.deepEqual(await axe(page), [], `Reiter ${tab}`);
    assert.deepEqual(page.errors, []);
    await page.close();
  }
});

test("Prozesse: Besetzung eines Gremiums, Fraktion abgeleitet, ohne Kontaktdaten", async () => {
  const page = await open("?prozesse=gremien&ansicht=liste");
  const rat = page.locator('details.pz-item[data-gremium="1"]');
  await rat.locator("> summary").click();
  const text = await rat.textContent();
  assert.match(text, /Besetzung.*Fraktion abgeleitet.*Mitglieder, nach Fraktion/s);
  assert.doesNotMatch(text, /@|Telefon/);
  await rat.locator(".pz-more summary", { hasText: "Mitglieder mit Namen" }).click();
  assert.ok(await rat.locator(".pz-mitglieder tbody tr").count() > 30);
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Mitmachen in Bonn: Stadtbezirk wechseln", async () => {
  const page = await open("?mitmachen=1&bezirk=Beuel");
  await page.waitForFunction(() => /Wege, sich einzubringen/.test(document.querySelector("#bt-body").textContent));
  assert.match(await page.locator("#bt-next-h").textContent(), /Beuel/);
  await page.locator("#bt-bezirk").selectOption("Hardtberg");
  assert.match(await page.locator("#bt-next-h").textContent(), /Hardtberg/);
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Mobil: Hamburger-Menü mit Gebiet, Flächen und Menüs; Esc schließt Menü und Blatt", async () => {
  const page = await open("", { width: 390, height: 844 });
  const burger = page.locator("#nav-burger");
  assert.ok(await page.locator("#q").isVisible(), "Suche bleibt sichtbar");
  assert.equal(await page.locator("#f-area").isVisible(), false, "Gebiet steckt im Menü");
  assert.ok((await page.locator(".nav").boundingBox()).height < 80, "Leiste einzeilig");
  await burger.click();
  assert.equal(await burger.getAttribute("aria-expanded"), "true");
  assert.ok(await page.locator("#f-area").isVisible());
  assert.ok(await page.locator('.toggle[data-panel="panel-list"]').isVisible());
  await page.locator('#nav-more [data-mega="mega-themen"]').click();
  assert.ok(await page.locator("#nav-more #mega-themen").isVisible(), "Menü klappt im Blatt auf");
  assert.deepEqual(await axe(page), []);
  await page.keyboard.press("Escape");
  assert.equal(await page.locator("#mega-themen").isVisible(), false);
  assert.equal(await page.locator("#nav-more #mega-themen").count(), 0, "Menü wieder an seinem Platz");
  await page.keyboard.press("Escape");
  assert.equal(await burger.getAttribute("aria-expanded"), "false");
  assert.equal(await page.evaluate(() => document.activeElement.id), "nav-burger");
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Mobil: Ebenen, Legenden und Quellen im Blatt „Karte“, ohne Verstöße", async () => {
  const page = await open("", { width: 390, height: 844 });
  // auf dem Telefon liegt das Fenster „Los geht's“ über der Karte; erst schließen (eigener Knopf, kein Schalter in der Leiste)
  await page.locator('[data-close="panel-detail"]').click();
  assert.equal(await page.locator("#panel-detail").isVisible(), false);
  const menu = page.locator(".map-menu");
  assert.equal(await menu.getAttribute("aria-expanded"), "false");
  assert.match(await menu.textContent(), /^Karte/);
  assert.equal(await page.locator(".map-plans").isVisible(), false, "Ebenen stecken im Blatt");
  assert.equal(await page.locator("#sources").isVisible(), false, "Legenden und Quellen stecken im Blatt");
  assert.ok(await page.locator(".map-whole").isVisible(), "„Ganz Bonn ansehen“ bleibt sichtbar");
  assert.equal((await page.locator(".map-whole").boundingBox()).width, 44, "als Symbol");
  assert.ok((await page.locator(".leaflet-control-attribution").boundingBox()).height < 24, "Quellenzeile einzeilig");
  await menu.click();
  assert.equal(await menu.getAttribute("aria-expanded"), "true");
  assert.ok(await page.locator(".map-sheet .map-plans").isVisible());
  assert.ok(await page.locator(".map-sheet #sources").isVisible());
  assert.deepEqual(await axe(page), []);
  await page.keyboard.press("Escape");
  assert.equal(await menu.getAttribute("aria-expanded"), "false", "Esc schließt das Blatt");
  // ⓘ in der Quellenzeile öffnet das Blatt mit den Quellen
  await page.locator(".attr-info").click();
  assert.equal(await menu.getAttribute("aria-expanded"), "true");
  assert.ok(await page.locator("#sources").evaluate((d) => d.open));
  await page.locator(".map-sheet-zu").click();
  assert.equal(await menu.getAttribute("aria-expanded"), "false");
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Über und „Was ist neu?“: gestraffter Dialog, eigenes Fenster, ohne Verstöße", async () => {
  const page = await open();
  await page.keyboard.press("Escape");
  await page.locator('.menu-btn[data-mega="mega-ueber"]').click();   // „Über den Ratsatlas“ steht im Menü „Über“
  await page.locator("#about-open").click();
  const about = page.locator("#about");
  assert.ok(await about.isVisible());
  const h3 = await about.locator("h3").allTextContents();
  assert.ok(h3.includes("Wie sicher sind die Angaben?") && h3.includes("Weitere Seiten") && h3.includes("Informiert bleiben"));
  assert.ok(!h3.some((t) => /verlässlich|Version 1\.0/.test(t)), "keine Doppelung, Neuigkeiten im eigenen Fenster");
  assert.equal(await about.locator('a[href="https://paderta.com/"]').count(), 1);
  assert.deepEqual(await axe(page), []);
  await about.locator("[data-neu]").click();
  assert.equal(await about.evaluate((d) => d.open), false);
  const neu = page.locator("#neu");
  assert.ok(await neu.isVisible());
  assert.match(await neu.textContent(), /Version 1\.0.*Seit Version 1\.0/s);
  assert.deepEqual(await axe(page), []);
  await page.keyboard.press("Escape");
  assert.equal(await neu.evaluate((d) => d.open), false);
  // auch über das Menü „Über“
  await page.locator('.menu-btn[data-mega="mega-ueber"]').click();
  await page.locator("#mega-ueber [data-neu]").click();
  assert.ok(await neu.isVisible());
  await neu.locator("[data-close-dialog]").click();
  assert.equal(await neu.evaluate((d) => d.open), false);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Menüs „Wer entscheidet“ und „Themen“: Karten öffnen Verfahren, Gremien, Ämter und Zahlen", async () => {
  const page = await open();
  await page.keyboard.press("Escape");
  for (const [tab, id] of [["gremien", "tab-pz-gremien"], ["aemter", "tab-pz-aemter"], ["verfahren", "tab-pz-verfahren"]]) {
    await page.locator('.menu-btn[data-mega="mega-entscheiden"]').click();
    await page.locator(`#mega-entscheiden [data-pz-tab="${tab}"]`).click();
    await page.waitForFunction((i) => !document.getElementById("panel-prozesse").hidden && document.getElementById(i)?.getAttribute("aria-selected") === "true", id);
    assert.equal(await page.locator("#mega-entscheiden").isVisible(), false, "Menü schließt");
  }
  assert.deepEqual(await axe(page), []);
  await page.keyboard.press("Escape");
  assert.equal(await page.locator("#panel-prozesse").isVisible(), false);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.mega), "mega-entscheiden", "Fokus zurück auf den Menüeintrag");
  await page.locator('.menu-btn[data-mega="mega-themen"]').click();
  assert.equal(await page.locator("#mega-themen .theme-links a").count(), 10);
  await page.locator('#mega-themen [data-open-tab="stats"]').click();
  assert.ok(await page.locator("#panel-auswertung").isVisible());
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Ratsassistent: erst beim Öffnen geladen, ohne Verstöße", async () => {
  const page = await open();
  const chatFiles = () => page.evaluate(() => performance.getEntriesByType("resource").filter((e) => e.name.includes("/chat/")).length);
  assert.equal(await chatFiles(), 0, "beim Start keine Module des Assistenten");
  await page.locator('.toggle[data-panel="panel-assistent"]').click();
  await page.waitForFunction(() => document.querySelectorAll("#chat-provider option").length > 0);
  assert.ok(await chatFiles() >= 7, "Module beim Öffnen geladen");
  await page.locator("#chat-consent").click();
  assert.ok(await page.locator("#chat-settings").isVisible(), "Einstellungen nach dem KI-Hinweis");
  assert.deepEqual(await axe(page), []);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Tour: alle Schritte bis zum Ende", async () => {
  const page = await open();
  await page.locator(".tour-cta[data-tour]").click();   // Knopf im Startfenster (ein weiterer steht im Menü „Über“)
  const titles = [];
  for (let i = 0; i < 30; i++) {
    // Schritte mit Ladevorgang zeigen „Einen Moment …“, bis Gebiet oder Vorgang geladen sind
    await page.waitForFunction(() => !document.querySelector("#tour-text")?.textContent.startsWith("Einen Moment"));
    // nach dem letzten Schritt ist die Karte der Tour entfernt oder ausgeblendet
    if (!(await page.locator("#tour-title").isVisible())) break;
    const title = await page.locator("#tour-title").textContent();
    titles.push(title);
    await page.locator('[data-tour-act="next"]').click();
    await page.waitForFunction((t) => {
      const el = document.querySelector("#tour-title");
      return !el || !el.offsetParent || el.textContent !== t || document.querySelector("#tour-text").textContent.startsWith("Einen Moment");
    }, title);
  }
  assert.ok(titles.length >= 14, `nur ${titles.length} Schritte: ${titles.join(" | ")}`);
  for (const t of ["Menü „Wer entscheidet“", "Menü „Themen“", "Menü „Mitmachen“", "Menü „Über“"]) assert.ok(titles.includes(t), t);
  assert.ok(titles.includes("Der Vorgang"), "Schritt mit dem Beispielvorgang");
  assert.equal(await page.locator(".tour-card").isVisible(), false, "Tour ist beendet");
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Liste in Schritten zu 50: „Weitere anzeigen“ ergänzt 50 Einträge, Fokus auf dem ersten neuen", async () => {
  const page = await open("?gebiet=ortsteil:endenich");
  await page.waitForFunction(() => /\d+ von \d+ Vorlagen/.test(document.querySelector("#count")?.textContent || ""));
  if (!(await page.locator("#panel-list").isVisible())) await page.locator('.toggle[data-panel="panel-list"]').click();
  const eintraege = () => page.locator("#papers > li:not(.more):not(.empty-list)").count();
  assert.equal(await eintraege(), 50);
  const more = page.locator("#more");
  assert.match(await more.textContent(), /Weitere 50 von \d+ anzeigen/);
  await more.focus();
  await page.keyboard.press("Enter");
  assert.equal(await eintraege(), 100);
  const fokusIndex = await page.evaluate(() => [...document.querySelectorAll("#papers > li")].findIndex((li) => li.contains(document.activeElement)));
  assert.equal(fokusIndex, 50);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("Leiste: Ansichten, vier Menüs und Assistent; Menü „Über“ mit Lesehilfen, „Über den Ratsatlas“ und Daten als Kacheln", async () => {
  for (const width of [1440, 390]) {
    const page = await open("", { width, height: 900 });
    await page.keyboard.press("Escape");
    assert.deepEqual(await page.locator(".nav .menu-btn[data-mega]").evaluateAll((bs) => bs.map((b) => b.dataset.mega)),
      ["mega-themen", "mega-entscheiden", "mega-mitmachen", "mega-ueber"]);
    assert.equal(await page.locator('.toggle[data-panel="panel-detail"], .toggle[data-panel="panel-prozesse"]').count(), 0, "kein Schalter für Vorgang und Prozesse");
    if (width < 900) await page.locator("#nav-burger").click();   // Telefon: Menüs hinter ☰
    await page.locator('.menu-btn[data-mega="mega-ueber"]').click();
    const m = page.locator("#mega-ueber");
    assert.ok(await m.isVisible());
    if (width < 900) assert.ok(await page.locator("#nav-more #mega-ueber").count(), "klappt im Hamburger-Menü auf");
    assert.equal(await m.locator('a[href="einfach/"]').count(), 1);
    assert.equal(await m.locator('a[href="begriffe/"]').count(), 1);
    assert.equal(await m.locator("[data-tour]").count(), 1);
    assert.equal(await m.locator(".card").count(), 13, "drei Gruppen als Kacheln");
    assert.equal(await m.locator("#about-open.card, [data-neu].card, #cta-report.card, a.card[href='teilen/'], a.card[href='rss/']").count(), 5);
    assert.deepEqual(await axe(page), [], `Menü Über (${width} px)`);
    await m.locator('[data-about="pruefung"]').click();
    assert.ok(await page.locator("#about").evaluate((d) => d.open));
    await page.keyboard.press("Escape");
    // Leiste ohne Überlauf
    assert.ok(await page.evaluate(() => { const n = document.querySelector(".nav"); return n.scrollWidth <= n.clientWidth + 1; }));
    assert.deepEqual(page.errors, []);
    await page.close();
  }
});
