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

let daten, karte, ansicht = "vorort", ot = null, schraeg = !SCHMAL, geb = new Map();

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
    geometry: { type: "Polygon", coordinates: quadrat(x[0], x[1], 8) } })) };
}
function saeulenBonn() {
  return { type: "FeatureCollection", features: daten.ortsteile.map((o, i) => ({ type: "Feature", id: i,
    properties: { i, n: o.n12, h: Math.max(30, o.n12 * 14) },
    geometry: { type: "Polygon", coordinates: quadrat(o.lon, o.lat, 170) } })) };
}
async function gebaeude(slug) {
  if (!geb.has(slug)) {
    geb.set(slug, fetch(`gebaeude/${encodeURIComponent(slug)}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
      .then((d) => ({ type: "FeatureCollection", features: (d ? d.gebaeude : []).map(([h, ring]) => ({ type: "Feature", properties: { h },
        geometry: { type: "Polygon", coordinates: [ring] } })) })));
  }
  return geb.get(slug);
}
function kamera(ziel) {
  const opt = { ...ziel, pitch: schraeg ? (ansicht === "bonn" ? 50 : 58) : 0, bearing: schraeg ? -18 : 0 };
  if (REDUCED) karte.jumpTo(opt); else karte.easeTo({ ...opt, duration: 900 });
}
function ziel() {
  if (ansicht === "bonn") return { center: [7.115, 50.715], zoom: SCHMAL ? 10.2 : 11.2 };
  return { center: [ot.lon, ot.lat], zoom: SCHMAL ? 14.4 : 15.2 };
}

function liste() {
  const n = ot.orte.reduce((a, x) => a + x[3].length, 0);
  $("#d3-liste-h").textContent = `Vorlagen in ${ot.name}`;
  if (!ot.orte.length) { $("#d3-liste").innerHTML = `<p>Keine Vorlage mit genauem Ort in ${esc(ot.name)} im Zeitraum ${esc(zeitraum())}.</p>`; return; }
  $("#d3-liste").innerHTML = `<p>${n} ${n === 1 ? "Vorlage" : "Vorlagen"} an ${ot.orte.length} ${ot.orte.length === 1 ? "Ort" : "Orten"}, ${esc(zeitraum())}; ${ot.n12} Vorlagen mit Ortsbezug insgesamt.</p>
    <ul class="d3-vorlagen">${ot.orte.flatMap((x) => x[3]).sort((a, b) => (b[2] || "").localeCompare(a[2] || "")).map(([ref, titel, datum]) =>
      `<li><a href="${vorgang(ot, ref)}">${esc(titel || ref)}</a> <span class="hint">${esc(ref)} · ${esc(fmt(datum))}</span></li>`).join("")}</ul>`;
}

async function zeigen() {
  document.querySelectorAll("[data-ansicht]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.ansicht === ansicht)));
  $("#d3-ortsteil").value = ot.slug;
  liste();
  const url = new URL(location.href);
  url.searchParams.set("ortsteil", ot.slug);
  if (ansicht === "bonn") url.searchParams.set("ansicht", "bonn"); else url.searchParams.delete("ansicht");
  history.replaceState(null, "", url);
  if (!karte) return;
  const bonn = ansicht === "bonn";
  karte.getSource("bonn").setData(saeulenBonn());
  karte.getSource("vor").setData(bonn ? { type: "FeatureCollection", features: [] } : saeulenVorOrt(ot));
  ["vor"].forEach((id) => karte.setLayoutProperty(id, "visibility", bonn ? "none" : "visible"));
  karte.setLayoutProperty("bonn", "visibility", bonn ? "visible" : "none");
  karte.setLayoutProperty("geb", "visibility", bonn ? "none" : "visible");
  kamera(ziel());
  $("#d3-status").textContent = bonn ? `Ganz Bonn: Säulen je Ortsteil, ${zeitraum()}.` : `${ot.name}: Gebäude werden geladen …`;
  if (!bonn) {
    const g = await gebaeude(ot.slug);
    karte.getSource("geb").setData(g);
    $("#d3-status").textContent = `${ot.name}: ${g.features.length.toLocaleString("de-DE")} Gebäude, Vorlagen an ${ot.orte.length} Orten (${zeitraum()}).`;
  }
}

// Vollbild (Entscheidung des Auftraggebers 24.11.2026): die Bühne (Leiste, Karte, Statuszeile) füllt das Fenster; auf Klick
// zusätzlich den Bildschirm, wo der Browser das erlaubt (iPhone: nur das Fenster). ?vollbild=1 öffnet die Seite so
// (Knopf „In 3D ansehen“ der Hauptkarte); den Bildschirm darf eine Seite nur nach einem Klick belegen.
let voll = false;
const vollElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
function vollbild(an, bildschirm = false) {
  voll = an;
  const buehne = $("#d3-buehne"), knopf = $("#d3-voll");
  buehne.classList.toggle("ist-voll", an);
  document.documentElement.classList.toggle("d3-gesperrt", an);
  knopf.setAttribute("aria-pressed", String(an));
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
}
function vollbildEinrichten() {
  const knopf = $("#d3-voll");
  knopf.hidden = false;
  knopf.addEventListener("click", () => vollbild(!voll, true));
  const ende = () => { if (!vollElement() && voll) { vollbild(false); knopf.focus(); } else if (karte) karte.resize(); };
  document.addEventListener("fullscreenchange", ende);
  document.addEventListener("webkitfullscreenchange", ende);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && voll) { vollbild(false); knopf.focus(); } });
}

function popup(lngLat, html) {
  new maplibregl.Popup({ maxWidth: "320px", closeButton: true }).setLngLat(lngLat).setHTML(html).addTo(karte);
}

async function start() {
  daten = await fetch("orte.json").then((r) => r.json());
  const wahl = $("#d3-ortsteil");
  wahl.innerHTML = [...daten.ortsteile].sort((a, b) => a.name.localeCompare(b.name, "de")).map((o) => `<option value="${esc(o.slug)}">${esc(o.name)}</option>`).join("");
  const p = new URLSearchParams(location.search);
  ot = daten.ortsteile.find((o) => o.slug === p.get("ortsteil")) || daten.ortsteile.find((o) => o.slug === STANDARD) || daten.ortsteile[0];
  ansicht = p.get("ansicht") === "bonn" ? "bonn" : "vorort";
  $("#d3-neigung").setAttribute("aria-pressed", String(schraeg));
  $("#d3-neigung").textContent = schraeg ? "Von oben ansehen" : "Schräg ansehen";
  if (!webgl()) {
    $("#d3-ohne").hidden = false;
    $("#d3-karte").hidden = true;
  } else {
    vollbildEinrichten();
    if (p.get("vollbild") === "1") vollbild(true);
    if (maplibregl.setWorkerUrl) maplibregl.setWorkerUrl(new URL("./vendor/maplibre/maplibre-gl-worker.mjs", new URL("..", location.href)).href);
    karte = new maplibregl.Map({
      container: "d3-karte", ...ziel(), pitch: schraeg ? 58 : 0, bearing: schraeg ? -18 : 0, maxPitch: 70, minZoom: 9.5, maxZoom: 18,
      style: { version: 8, sources: { grau: { type: "raster", tiles: [new URL("../kacheln/{z}/{x}/{y}.png", location.href).href.replace(/%7B/g, "{").replace(/%7D/g, "}")],
        tileSize: 256, minzoom: 10, maxzoom: 16, attribution: "© OpenStreetMap-Mitwirkende (ODbL), Protomaps · Gebäude: Geobasis NRW (dl-de/zero-2.0)" } },
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
    for (const id of ["vor", "bonn"]) {
      karte.on("mouseenter", id, () => { karte.getCanvas().style.cursor = "pointer"; });
      karte.on("mouseleave", id, () => { karte.getCanvas().style.cursor = ""; });
    }
  }
  document.querySelectorAll("[data-ansicht]").forEach((b) => b.addEventListener("click", () => { ansicht = b.dataset.ansicht; zeigen(); }));
  wahl.addEventListener("change", () => { ot = daten.ortsteile.find((o) => o.slug === wahl.value); ansicht = "vorort"; zeigen(); });
  $("#d3-neigung").addEventListener("click", (e) => {
    schraeg = !schraeg;
    e.currentTarget.setAttribute("aria-pressed", String(schraeg));
    e.currentTarget.textContent = schraeg ? "Von oben ansehen" : "Schräg ansehen";
    if (karte) kamera({});
  });
  $("#d3-zurueck").addEventListener("click", () => karte && kamera(ziel()));
  await zeigen();
  window.__d3bereit = true;
}

start().catch((e) => { $("#d3-status").textContent = `Die 3D-Ansicht konnte nicht geladen werden (${e.message}). Liste und Tabelle bleiben nutzbar.`; });
