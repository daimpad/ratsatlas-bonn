// Seite 3d/ „Bonn in 3D“ (pipeline/dreidseite.py): Gebäude aus LoD1 (3d/gebaeude/<slug>.json, Branch gebaeude) und
// Vorlagen als Säulen (3d/orte.json) mit MapLibre GL (site/vendor/maplibre, nur eigener Server). Liste und Tabelle auf der
// Seite sind die gleichwertige Alternative; ohne WebGL bleibt nur der Hinweis.
import * as ml from "./vendor/maplibre/maplibre-gl.mjs";

const maplibregl = ml.default || ml;
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const SCHMAL = matchMedia("(max-width: 700px)").matches;
const DATUM = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Europe/Berlin" });
const fmt = (iso) => (iso ? DATUM.format(new Date(iso + "T12:00:00Z")) : "");
const STANDARD = "endenich";   // Pilot-Ortsteil

// Bereich der grauen Kacheln, den alle Zoomstufen abdecken (wie KACHEL_RAHMEN in site/app.js): außerhalb keine Abrufe
const KACHEL_BEREICH = [6.9873, 50.6007, 7.2455, 50.8059];
const GEB_HOECHSTENS = 6;   // Gebäude so vieler Ortsteile im Speicher (je bis zu 2 MB; Prüfung 25.11.2026)
// deutsche Texte der Bedienelemente (Prüfung 25.11.2026, WCAG 3.1.2)
const LOCALE = {
  "Map.Title": "Karte", "Popup.Close": "Schließen", "NavigationControl.ZoomIn": "Vergrößern",
  "NavigationControl.ZoomOut": "Verkleinern", "NavigationControl.ResetBearing": "Ausrichtung nach Norden zurücksetzen (ziehen zum Drehen und Neigen)",
  "AttributionControl.ToggleAttribution": "Quellen ein- oder ausblenden", "AttributionControl.MapFeedback": "Rückmeldung zur Karte",
  "FullscreenControl.Enter": "Vollbild", "FullscreenControl.Exit": "Vollbild beenden", "LogoControl.Title": "MapLibre",
  "CooperativeGesturesHandler.WindowsHelpText": "Strg und Scrollen zum Zoomen", "CooperativeGesturesHandler.MacHelpText": "⌘ und Scrollen zum Zoomen",
  "CooperativeGesturesHandler.MobileHelpText": "Mit zwei Fingern bewegen",
};

let daten, karte, ansicht = "vorort", ot = null, bezirk = null, schraeg = !SCHMAL, geb = new Map(), aufruf = 0;

function webgl() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); } catch { return false; }
}
function quadrat(lon, lat, m) {
  const dx = m / (111320 * Math.cos((lat * Math.PI) / 180)), dy = m / 110540;
  return [[[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy], [lon - dx, lat + dy], [lon - dx, lat - dy]]];
}
const farbe = (thema) => (daten.themen.find((t) => t.id === thema) || {}).farbe || daten.ohne_thema;
const vorgang = (o, ref) => `../?gebiet=ortsteil:${encodeURIComponent(o.slug)}#${encodeURIComponent(ref)}`;
const zeitraum = () => (daten.bis ? `${fmt(daten.seit)} bis ${fmt(daten.bis)}` : "letzte 12 Monate");

function saeulenVorOrt(o) {
  return { type: "FeatureCollection", features: o.orte.map((x, i) => ({ type: "Feature", id: i,
    properties: { i, n: x[3].length, h: 40 + 28 * x[3].length, farbe: farbe(x[2]) },
    geometry: { type: "Polygon", coordinates: quadrat(x[0], x[1], 12) } })) };   // 24 m breit (Prüfung 25.11.2026, V6)
}
function saeulenBonn() {
  return { type: "FeatureCollection", features: daten.ortsteile.map((o, i) => ({ type: "Feature", id: i,
    properties: { i, n: o.n12, h: Math.max(30, o.n12 * 14) },
    geometry: { type: "Polygon", coordinates: quadrat(o.lon, o.lat, 170) } })) };
}
// Gebäude eines Ortsteils; null, wenn die Datei fehlt oder nicht lesbar ist (dann ohne Speicher: der nächste Aufruf
// versucht es erneut). Höchstens GEB_HOECHSTENS Ortsteile bleiben im Speicher.
async function gebaeude(slug) {
  if (geb.has(slug)) {
    const g = geb.get(slug);
    geb.delete(slug); geb.set(slug, g);   // zuletzt benutzt ans Ende
    return g;
  }
  const g = fetch(`gebaeude/${encodeURIComponent(slug)}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
    .then((d) => (d && Array.isArray(d.gebaeude) ? { type: "FeatureCollection", features: d.gebaeude.map(([h, ring]) => ({ type: "Feature",
      properties: { h }, geometry: { type: "Polygon", coordinates: [ring] } })) } : null));
  geb.set(slug, g);
  const fertig = await g;
  if (!fertig) geb.delete(slug);
  while (geb.size > GEB_HOECHSTENS) geb.delete(geb.keys().next().value);
  return fertig;
}
function kamera(ziel) {
  const opt = { ...ziel, pitch: schraeg ? (ansicht === "bonn" ? 50 : 58) : 0, bearing: schraeg ? -18 : 0 };
  if (REDUCED) karte.jumpTo(opt); else karte.easeTo({ ...opt, duration: 900 });
}
const imBezirk = () => daten.ortsteile.filter((o) => o.stadtbezirk === bezirk);
function ziel() {
  if (ansicht === "bonn" && bezirk && imBezirk().length) {
    const os = imBezirk(), lon = os.map((o) => o.lon), lat = os.map((o) => o.lat);
    const kamera = karte && karte.cameraForBounds([[Math.min(...lon), Math.min(...lat)], [Math.max(...lon), Math.max(...lat)]], { padding: SCHMAL ? 60 : 120 });
    return kamera ? { center: kamera.center, zoom: Math.min(kamera.zoom, 13.5) } : { center: [lon.reduce((a, b) => a + b) / lon.length, lat.reduce((a, b) => a + b) / lat.length], zoom: 12.5 };
  }
  if (ansicht === "bonn") return { center: [7.115, 50.715], zoom: SCHMAL ? 10.2 : 11.2 };
  return { center: [ot.lon, ot.lat], zoom: SCHMAL ? 14.4 : 15.2 };
}

function listeBonn() {
  const os = (bezirk ? imBezirk() : daten.ortsteile).slice().sort((a, b) => b.n12 - a.n12 || a.name.localeCompare(b.name, "de"));
  $("#d3-liste-h").textContent = bezirk ? `Ortsteile im Stadtbezirk ${bezirk}` : "Ortsteile in ganz Bonn";
  $("#d3-liste").innerHTML = `<p>Vorlagen mit Ortsbezug, ${esc(zeitraum())}. Ein Name öffnet den Ortsteil in 3D.</p>
    <ul class="d3-vorlagen">${os.map((o) => `<li><a href="?ortsteil=${encodeURIComponent(o.slug)}" data-ot="${esc(o.slug)}">${esc(o.name)}</a> <span class="hint">${o.n12} Vorlagen</span></li>`).join("")}</ul>`;
}

function liste() {
  if (ansicht === "bonn") { listeBonn(); return; }
  const n = ot.orte.reduce((a, x) => a + x[3].length, 0);
  $("#d3-liste-h").textContent = `Vorlagen in ${ot.name}`;
  if (!ot.orte.length) { $("#d3-liste").innerHTML = `<p>Keine Vorlage mit genauem Ort in ${esc(ot.name)} im Zeitraum ${esc(zeitraum())}.</p>`; return; }
  $("#d3-liste").innerHTML = `<p>${n} ${n === 1 ? "Vorlage" : "Vorlagen"} an ${ot.orte.length} ${ot.orte.length === 1 ? "Ort" : "Orten"}, ${esc(zeitraum())}; ${ot.n12} Vorlagen mit Ortsbezug insgesamt.</p>
    <ul class="d3-vorlagen">${ot.orte.flatMap((x) => x[3]).sort((a, b) => (b[2] || "").localeCompare(a[2] || "")).map(([ref, titel, datum]) =>
      `<li><a href="${vorgang(ot, ref)}">${esc(titel || ref)}</a> <span class="hint">${esc(ref)} · ${esc(fmt(datum))}</span></li>`).join("")}</ul>`;
}

async function zeigen() {
  const nr = ++aufruf;   // spätere Aufrufe gewinnen (Wettlauf beim schnellen Wechsel; Prüfung 25.11.2026)
  const bonn = ansicht === "bonn";
  if (!bonn) bezirk = null;
  document.querySelectorAll("[data-ansicht]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.ansicht === ansicht)));
  $("#d3-ortsteil").value = bonn ? "" : ot.slug;   // in „Ganz Bonn“ ist kein Ortsteil gewählt
  liste();
  const url = new URL(location.href);
  if (bonn) url.searchParams.delete("ortsteil"); else url.searchParams.set("ortsteil", ot.slug);
  if (bonn) url.searchParams.set("ansicht", "bonn"); else url.searchParams.delete("ansicht");
  if (bonn && bezirk) url.searchParams.set("bezirk", bezirk); else url.searchParams.delete("bezirk");
  history.replaceState(null, "", url);
  if (!karte) return;
  document.querySelectorAll(".maplibregl-popup").forEach((el) => el.remove());
  karte.getSource("bonn").setData(saeulenBonn());
  karte.getSource("vor").setData(bonn ? { type: "FeatureCollection", features: [] } : saeulenVorOrt(ot));
  ["vor"].forEach((id) => karte.setLayoutProperty(id, "visibility", bonn ? "none" : "visible"));
  karte.setLayoutProperty("bonn", "visibility", bonn ? "visible" : "none");
  karte.setLayoutProperty("geb", "visibility", bonn ? "none" : "visible");
  kamera(ziel());
  $("#d3-status").textContent = bonn ? `${bezirk ? `Stadtbezirk ${bezirk}` : "Ganz Bonn"}: Säulen je Ortsteil, ${zeitraum()}.` : `${ot.name}: Gebäude werden geladen …`;
  if (!bonn) {
    const leer = { type: "FeatureCollection", features: [] };
    karte.getSource("geb").setData(leer);   // keine Gebäude des vorigen Ortsteils stehen lassen
    const name = ot.name, g = await gebaeude(ot.slug);
    if (nr !== aufruf) return;   // inzwischen anderer Ortsteil oder andere Ansicht
    karte.getSource("geb").setData(g || leer);
    $("#d3-status").textContent = g
      ? `${name}: ${g.features.length.toLocaleString("de-DE")} Gebäude, Vorlagen an ${ot.orte.length} Orten (${zeitraum()}).`
      : `${name}: Die Gebäude konnten nicht geladen werden; die Säulen der Vorlagen stehen ohne Gebäude. Vorlagen an ${ot.orte.length} Orten (${zeitraum()}).`;
  }
}

// Vollbild (Entscheidung des Auftraggebers 24.11.2026): die Bühne (Leiste, Karte, Statuszeile) füllt das Fenster; auf Klick
// zusätzlich den Bildschirm, wo der Browser das erlaubt (iPhone: nur das Fenster). ?vollbild=1 öffnet die Seite so
// (Knopf „In 3D ansehen“ der Hauptkarte); den Bildschirm darf eine Seite nur nach einem Klick belegen.
let voll = false, traege = [];
const vollElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
// Im Vollbild ist die übrige Seite nicht erreichbar (inert): keine Tab-Stopps hinter der Karte (Prüfung 25.11.2026)
function rest(an) {
  traege.forEach((el) => { el.inert = false; });
  traege = [];
  if (!an) return;
  for (let el = $("#d3-buehne"); el && el.parentElement; el = el.parentElement) {
    for (const g of el.parentElement.children) if (g !== el && !g.inert && g.tagName !== "SCRIPT") { g.inert = true; traege.push(g); }
  }
}
function vollbild(an, bildschirm = false) {
  voll = an;
  const buehne = $("#d3-buehne"), knopf = $("#d3-voll");
  buehne.classList.toggle("ist-voll", an);
  document.documentElement.classList.toggle("d3-gesperrt", an);
  rest(an);
  knopf.querySelector("span").textContent = an ? "Vollbild beenden" : "Vollbild";
  if (an && bildschirm) {
    const f = buehne.requestFullscreen || buehne.webkitRequestFullscreen;
    try { const r = f && f.call(buehne); if (r && r.catch) r.catch(() => {}); } catch { /* nur das Fenster */ }
  }
  if (!an && vollElement()) {
    const r = (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    if (r && r.catch) r.catch(() => {});
  }
  const url = new URL(location.href);
  if (an) url.searchParams.set("vollbild", "1"); else url.searchParams.delete("vollbild");
  history.replaceState(null, "", url);
  if (karte) { karte.resize(); requestAnimationFrame(() => karte.resize()); }
  leisteMessen();
}
function leisteMessen() {
  const l = document.querySelector(".d3-leiste");
  if (l) $("#d3-buehne").style.setProperty("--d3-leiste-h", `${l.offsetTop + l.offsetHeight + 8}px`);
}
function vollbildEinrichten() {
  const knopf = $("#d3-voll");
  knopf.hidden = false;
  knopf.addEventListener("click", () => vollbild(!voll, true));
  const ende = () => { if (!vollElement() && voll) { vollbild(false); knopf.focus(); } else if (karte) karte.resize(); };
  addEventListener("resize", () => { if (voll) leisteMessen(); });
  document.addEventListener("fullscreenchange", ende);
  document.addEventListener("webkitfullscreenchange", ende);
  // Esc schließt zuerst ein offenes Popup, erst danach das Vollbild
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const pop = document.querySelectorAll(".maplibregl-popup:not(.d3-tip)");
    if (pop.length) { pop.forEach((el) => el.remove()); e.preventDefault(); return; }
    if (voll) { vollbild(false); knopf.focus(); }
  });
}

function popup(lngLat, html) {
  new maplibregl.Popup({ maxWidth: "320px", closeButton: true }).setLngLat(lngLat).setHTML(html).addTo(karte);
}

async function start() {
  daten = await fetch("orte.json").then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
  const wahl = $("#d3-ortsteil");
  wahl.innerHTML = '<option value="" disabled>Ortsteil wählen …</option>' + [...daten.ortsteile].sort((a, b) => a.name.localeCompare(b.name, "de")).map((o) => `<option value="${esc(o.slug)}">${esc(o.name)}</option>`).join("");
  const p = new URLSearchParams(location.search);
  ot = daten.ortsteile.find((o) => o.slug === p.get("ortsteil")) || daten.ortsteile.find((o) => o.slug === STANDARD) || daten.ortsteile[0];
  ansicht = p.get("ansicht") === "bonn" ? "bonn" : "vorort";
  bezirk = ansicht === "bonn" && daten.ortsteile.some((o) => o.stadtbezirk === p.get("bezirk")) ? p.get("bezirk") : null;
  // fester Name, Zustand nur über aria-pressed (WCAG 4.1.2; Prüfung 25.11.2026)
  $("#d3-neigung").setAttribute("aria-pressed", String(schraeg));
  if (!webgl()) {
    $("#d3-ohne").hidden = false;
    $("#d3-karte").hidden = true;
  } else {
    vollbildEinrichten();
    if (p.get("vollbild") === "1") vollbild(true);
    if (maplibregl.setWorkerUrl) maplibregl.setWorkerUrl(new URL("./vendor/maplibre/maplibre-gl-worker.mjs", new URL("..", location.href)).href);
    karte = new maplibregl.Map({
      container: "d3-karte", ...ziel(), pitch: schraeg ? 58 : 0, bearing: schraeg ? -18 : 0, maxPitch: 70, minZoom: 9.5, maxZoom: 18, locale: LOCALE,
      style: { version: 8, sources: { grau: { type: "raster", tiles: [new URL("../kacheln/{z}/{x}/{y}.png", location.href).href.replace(/%7B/g, "{").replace(/%7D/g, "}")],
        tileSize: 256, minzoom: 10, maxzoom: 16, bounds: KACHEL_BEREICH, attribution: "© OpenStreetMap-Mitwirkende (ODbL), Protomaps · Gebäude: Geobasis NRW (dl-de/zero-2.0)" } },
        layers: [{ id: "grau", type: "raster", source: "grau" }] },
      attributionControl: { compact: true },
    });
    karte.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    await new Promise((res) => karte.on("load", res));
    const leer = { type: "FeatureCollection", features: [] };
    karte.addSource("geb", { type: "geojson", data: leer });
    karte.addLayer({ id: "geb", type: "fill-extrusion", source: "geb", paint: { "fill-extrusion-color": "#d9d7e1", "fill-extrusion-height": ["get", "h"], "fill-extrusion-opacity": 0.92 } });
    karte.addSource("vor", { type: "geojson", data: leer });
    karte.addLayer({ id: "vor", type: "fill-extrusion", source: "vor", paint: { "fill-extrusion-color": ["get", "farbe"], "fill-extrusion-height": ["get", "h"], "fill-extrusion-opacity": 0.95 } });
    karte.addSource("bonn", { type: "geojson", data: leer });
    karte.addLayer({ id: "bonn", type: "fill-extrusion", source: "bonn", layout: { visibility: "none" }, paint: {
      "fill-extrusion-color": ["interpolate", ["linear"], ["get", "n"], 0, "#ddd6fe", 60, "#a78bfa", 200, "#6d28d9"],
      "fill-extrusion-height": ["get", "h"], "fill-extrusion-opacity": 0.88 } });
    karte.on("click", "vor", (e) => {
      const x = ot.orte[e.features[0].properties.i];
      popup(e.lngLat, `<p class="d3-pop-h">${x[3].length} ${x[3].length === 1 ? "Vorlage" : "Vorlagen"} an diesem Ort</p><ul class="d3-pop">${x[3].map(([ref, titel, datum]) =>
        `<li><a href="${vorgang(ot, ref)}">${esc(titel || ref)}</a><br><span>${esc(ref)} · ${esc(fmt(datum))}</span></li>`).join("")}</ul>`);
    });
    karte.on("click", "bonn", (e) => { ot = daten.ortsteile[e.features[0].properties.i]; ansicht = "vorort"; zeigen(); });
    // Name und Zahl beim Überfahren (Prüfung 25.11.2026, V6: in „Ganz Bonn“ standen keine Ortsteilnamen)
    const hinweis = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "d3-tip", offset: 12 });
    const text = (id, f) => {
      if (id === "bonn") { const o = daten.ortsteile[f.properties.i]; return `${o.name}: ${o.n12} Vorlagen – Klick öffnet den Ortsteil`; }
      const n = f.properties.n;
      return `${n} ${n === 1 ? "Vorlage" : "Vorlagen"} an diesem Ort – Klick nennt sie`;
    };
    for (const id of ["vor", "bonn"]) {
      karte.on("mousemove", id, (e) => {
        karte.getCanvas().style.cursor = "pointer";
        hinweis.setLngLat(e.lngLat).setText(text(id, e.features[0])).addTo(karte);
      });
      karte.on("mouseleave", id, () => { karte.getCanvas().style.cursor = ""; hinweis.remove(); });
    }
  }
  document.querySelectorAll("[data-ansicht]").forEach((b) => b.addEventListener("click", () => { ansicht = b.dataset.ansicht; if (ansicht === "bonn") bezirk = null; zeigen(); }));
  $("#d3-liste").addEventListener("click", (e) => {
    const a = e.target.closest("[data-ot]");
    if (!a) return;
    e.preventDefault();
    ot = daten.ortsteile.find((o) => o.slug === a.dataset.ot) || ot; ansicht = "vorort"; zeigen();
  });
  wahl.addEventListener("change", () => { ot = daten.ortsteile.find((o) => o.slug === wahl.value); ansicht = "vorort"; zeigen(); });
  $("#d3-neigung").addEventListener("click", (e) => {
    schraeg = !schraeg;
    e.currentTarget.setAttribute("aria-pressed", String(schraeg));
    if (karte) kamera({});
  });
  $("#d3-zurueck").addEventListener("click", () => karte && kamera(ziel()));
  await zeigen();
  window.__d3bereit = true;
}

start().catch((e) => { $("#d3-status").textContent = `Die 3D-Ansicht konnte nicht geladen werden (${e.message}). Liste und Tabelle bleiben nutzbar.`; });
