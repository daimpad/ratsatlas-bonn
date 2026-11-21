// Darstellung der Antworten: kein HTML aus Modellausgaben, Links nur aus Werkzeugergebnissen, Drucksachen
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderMarkdown, collectUrls, resolveRef, esc } from "../../site/chat/render.js";

const URL1 = "https://www.bonn.sitzung-online.de/public/VO020?VOLFDNR=2029541";
const ctx = { urls: new Set([URL1]), refs: new Set(["261798", "261798-01 ST"]) };

test("Kein HTML aus der Modellausgabe (XSS)", () => {
  const evil = `<img src=x onerror=alert(1)> <script>alert(2)</script> [klick](javascript:alert(3)) <a href="https://evil.example">x</a>`;
  const html = renderMarkdown(evil, ctx);
  assert.doesNotMatch(html, /<img|<script|<a href="javascript|<a href="https:\/\/evil/i);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.match(html, /Link entfernt/);
  const attr = renderMarkdown(`[a"onmouseover="x](${URL1}")`, ctx);
  assert.doesNotMatch(attr, /onmouseover="x"/);
});

test("Links nur zu Adressen aus Werkzeugergebnissen", () => {
  const html = renderMarkdown(`[Original](${URL1}) und [Fremd](https://example.org/x) und ${URL1}`, ctx);
  assert.equal((html.match(/<a href=/g) || []).length, 2);
  assert.match(html, /target="_blank" rel="noopener noreferrer"/);
  assert.match(html, /Fremd <span class="link-removed">/);
});

test("Drucksachen: belegte als Schaltfläche (volle Nummer), unbelegte markiert", () => {
  const html = renderMarkdown("Die Vorlage 261798 und ihre Stellungnahme 261798-01; 259999 ist unbekannt.", ctx);
  assert.match(html, /<button type="button" class="ref" data-ref="261798" [^>]*>261798<\/button>/);
  assert.match(html, /data-ref="261798-01 ST"[^>]*>261798-01<\/button>/);
  assert.match(html, /<mark class="unbelegt"[^>]*>259999<\/mark>/);
  assert.equal(resolveRef("261798-01", ctx.refs), "261798-01 ST");
  assert.equal(resolveRef("261798-0", ctx.refs), null);
});

test("Markdown: Absätze, Listen, Überschriften, Hervorhebung, Code, Tabelle", () => {
  const md = "# Stand\n**Entschieden** am *24.09.2026*.\nZweite Zeile\n\n- eins\n- zwei\n1. a\n2. b\n\n`code <b>`\n\n| Gremium | Ergebnis |\n|---|---|\n| Rat | vertagt |\n\n```\n<x>\n```";
  const html = renderMarkdown(md, ctx);
  assert.match(html, /<p class="md-h"><strong>Stand<\/strong><\/p>/);
  assert.match(html, /<strong>Entschieden<\/strong> am <em>24\.09\.2026<\/em>\.<br>Zweite Zeile/);
  assert.match(html, /<ul><li>eins<\/li><li>zwei<\/li><\/ul><ol><li>a<\/li><li>b<\/li><\/ol>/);
  assert.match(html, /<code>code &lt;b&gt;<\/code>/);
  assert.match(html, /<th scope="col">Gremium<\/th>.*<td>vertagt<\/td>/s);
  assert.match(html, /<pre><code>&lt;x&gt;<\/code><\/pre>/);
});

test("Adressen aus Ergebnissen sammeln; Maskierung", () => {
  const urls = collectUrls({ links: { ratsinformationssystem: URL1, dokument: null }, quelle_id: "https://www.bonn.sitzung-online.de/oparl/papers/1", titel: "Siehe https://x.example im Text" });
  assert.deepEqual([...urls].sort(), ["https://www.bonn.sitzung-online.de/oparl/papers/1", URL1].sort());
  assert.equal(esc(`<"'&>`), "&lt;&quot;&#39;&amp;&gt;");
});

test("Zahlen außerhalb der Drucksachen-Nummern bleiben Text", () => {
  const html = renderMarkdown("Kosten von 150000 Euro, 200000 € und die Nummer 999999.", ctx);
  assert.doesNotMatch(html, /<button|<mark/);
});

test("Links nur aus Datenfeldern bekannter Stellen, nicht aus wiederholten Eingaben", () => {
  // Code-Prüfung 23.10.2026: das Stichwort einer Suche kam unverändert zurück und machte so jede Adresse anklickbar
  const urls = collectUrls({ anfrage: { stichwort: "https://angreifer.example/x" }, eingabe: "https://angreifer.example/y",
    links: { ratsinformationssystem: "https://www.bonn.sitzung-online.de/public/VO020?VOLFDNR=1", fremd: "https://angreifer.example/z" } });
  assert.deepEqual([...urls], ["https://www.bonn.sitzung-online.de/public/VO020?VOLFDNR=1"]);
  const html = renderMarkdown("[Quelle](https://angreifer.example/x)", { urls });
  assert.ok(!html.includes("<a "));
  const t = Date.now();
  renderMarkdown("[".repeat(64000), { urls });
  assert.ok(Date.now() - t < 1000, "lange Folgen von [ ohne lange Rechenzeit");
});

test("Links: Aufzeichnungen, Ratstranskripte und Quellen der Zahlen zum Gebiet (Prüfung November 2026, Nr. 17)", () => {
  const ergebnis = {
    sitzungen: [{ aufzeichnung: "https://www.youtube.com/watch?v=abc" }],
    transkripte: "https://bonn.biz/ratstranskripte",
    fremd: ["https://bonn.biz/ratstranskripte?q=geheim", "https://bonn.biz/anderes", "https://youtube.com.example.org/watch", "https://evil.example/www.youtube.com"],
    link: "https://www.zensus2022.de/DE/Ergebnisse.html",
    plan_pdf: "https://stadtplan.bonn.de/mapbender/daten/images/Bebauungsplaene/plan_internet/6322-2%20Teil%20A.pdf",
  };
  const urls = collectUrls(ergebnis);
  assert.deepEqual([...urls].sort(), ["https://bonn.biz/ratstranskripte", "https://stadtplan.bonn.de/mapbender/daten/images/Bebauungsplaene/plan_internet/6322-2%20Teil%20A.pdf",
    "https://www.youtube.com/watch?v=abc", "https://www.zensus2022.de/DE/Ergebnisse.html"]);
  const html = renderMarkdown("[Video](https://www.youtube.com/watch?v=abc), [Transkripte](https://bonn.biz/ratstranskripte), [Suche](https://bonn.biz/ratstranskripte?q=geheim)", { urls, refs: new Set() });
  assert.match(html, /href="https:\/\/www\.youtube\.com\/watch\?v=abc"/);
  assert.match(html, /href="https:\/\/bonn\.biz\/ratstranskripte"/);
  assert.ok(!html.includes("q=geheim\""), html);
});

