/* Map behaviour for both mock-ups.
   PAGE.mode === "overview": map at the top, photo markers open a card that links to the section.
   PAGE.mode === "scrolly":  map pinned beside/above the text, follows the section being read. */
(async function () {
  const PAGE = window.PAGE;
  const places = PAGE.places;
  const byId = Object.fromEntries(places.map((p) => [p.id, p]));
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DK = [[8.0, 54.55], [15.2, 57.76]];
  const isWater = PAGE.mode === "scrolly";

  document.querySelector(".mock-banner__close")?.addEventListener("click", () => {
    document.getElementById("mock-banner").hidden = true;
  });

  // ---- basemap: OpenFreeMap Positron, recoloured towards DN's palette ----
  const [style, areas] = await Promise.all([
    fetch("https://tiles.openfreemap.org/styles/positron").then((r) => r.json()),
    fetch(PAGE.areas).then((r) => r.json()),
  ]);
  const paint = {
    background: { "background-color": "#f4f0e6" },
    water: { "fill-color": "#c9dde2" },
    waterway: { "line-color": "#b4d0d8" },
    landcover_wood: { "fill-color": "#dce8cc", "fill-opacity": 1 },
    park: { "fill-color": "#e2ead3" },
    landuse_residential: { "fill-color": "#ece6da" },
  };
  for (const layer of style.layers) {
    Object.assign((layer.paint ||= {}), paint[layer.id] || {});
    if (layer.type === "symbol" && layer.paint["text-color"]) layer.paint["text-color"] = "#55685a";
    // Danish place names instead of English ones
    if (layer.type === "symbol" && layer.layout?.["text-field"] && !layer.id.includes("shield")) {
      layer.layout["text-field"] = ["coalesce", ["get", "name"], ["get", "name:latin"]];
    }
  }

  const map = new maplibregl.Map({
    container: "map",
    style,
    bounds: DK,
    fitBoundsOptions: { padding: 16 },
    cooperativeGestures: true,
    dragRotate: false,
    pitchWithRotate: false,
    attributionControl: { compact: true },
    locale: {
      "CooperativeGesturesHandler.WindowsHelpText": "Hold Ctrl nede og scroll for at zoome",
      "CooperativeGesturesHandler.MacHelpText": "Hold ⌘ nede og scroll for at zoome",
      "CooperativeGesturesHandler.MobileHelpText": "Brug to fingre for at flytte kortet",
      "NavigationControl.ZoomIn": "Zoom ind",
      "NavigationControl.ZoomOut": "Zoom ud",
    },
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

  const fillColor = isWater ? "#2f7fae" : "#4f8a45";
  map.on("load", () => {
    // keep the attribution folded into the (i) button on small maps
    document.querySelectorAll(".maplibregl-ctrl-attrib").forEach((e) => e.classList.remove("maplibregl-compact-show"));
    map.addSource("areas", { type: "geojson", data: areas });
    map.addLayer({ id: "areas-fill", type: "fill", source: "areas", filter: ["==", ["get", "kind"], "area"],
      paint: { "fill-color": fillColor, "fill-opacity": 0.22 } });
    map.addLayer({ id: "areas-line", type: "line", source: "areas", filter: ["==", ["get", "kind"], "area"],
      paint: { "line-color": fillColor, "line-width": 1, "line-opacity": 0.7 } });
    map.addLayer({ id: "rivers", type: "line", source: "areas", filter: ["==", ["get", "kind"], "line"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": "#2f7fae", "line-width": ["interpolate", ["linear"], ["zoom"], 6, 2, 10, 4], "line-opacity": 0.8 } });
  });

  // ---- active place highlight ----
  let activeId = null;
  function setActive(id) {
    activeId = id;
    document.querySelectorAll(".marker").forEach((m) => m.classList.toggle("is-active", m.dataset.id === id));
    if (!map.getLayer("areas-fill")) return;
    const is = ["==", ["get", "id"], id || ""];
    map.setPaintProperty("areas-fill", "fill-opacity", ["case", is, 0.55, 0.22]);
    map.setPaintProperty("areas-line", "line-width", ["case", is, 2.5, 1]);
    map.setPaintProperty("rivers", "line-width",
      ["interpolate", ["linear"], ["zoom"], 6, ["case", is, 4, 2], 10, ["case", is, 7, 4]]);
    map.setPaintProperty("rivers", "line-color", ["case", is, "#1d5f8a", "#2f7fae"]);
  }

  function focusPlace(p, opts = {}) {
    const duration = reduceMotion ? 0 : opts.duration ?? 1400;
    const padding = opts.padding ?? 48;
    if (p.bbox) {
      map.fitBounds([[p.bbox[0], p.bbox[1]], [p.bbox[2], p.bbox[3]]], { padding, maxZoom: 11.5, duration });
    } else {
      map.flyTo({ center: [p.lon, p.lat], zoom: 11, duration });
    }
  }

  function showAll() {
    map.fitBounds(DK, { padding: 16, duration: reduceMotion ? 0 : 1200 });
  }

  // ---- markers ----
  for (const p of places) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "marker";
    el.dataset.id = p.id;
    el.setAttribute("aria-label", p.name);
    el.title = p.name;
    if (p.thumb) el.style.backgroundImage = `url("${p.thumb}")`;
    if (PAGE.mode === "scrolly") {
      const n = document.createElement("span");
      n.className = "marker__n";
      n.textContent = p.n;
      el.append(n);
    }
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      if (PAGE.mode === "overview") openPopup(p);
      else document.getElementById(p.id).scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
    });
    p.marker = new maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).addTo(map);
  }

  // ---- overview popups ----
  const popup = new maplibregl.Popup({ offset: 30, maxWidth: "270px", focusAfterOpen: false });
  popup.on("close", () => setActive(null));
  function openPopup(p) {
    const dist = p.km != null ? `<span class="pop__dist">${fmtKm(p.km)} fra dig</span>` : "";
    const dir = `https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}`;
    popup.setLngLat([p.lon, p.lat]).setHTML(
      `<div class="pop">${p.card ? `<img src="${p.card}" alt="">` : ""}<div class="pop__body">
        <strong>${p.name}</strong>${dist}
        <div class="pop__links"><a href="#${p.id}">Læs mere ↓</a><a href="${dir}" target="_blank" rel="noopener">Rutevejledning ↗</a></div>
      </div></div>`).addTo(map);
    setActive(p.id);
  }

  // ---- "Vis på kortet" buttons in each section ----
  document.querySelectorAll(".show-on-map").forEach((btn) => btn.addEventListener("click", () => {
    const p = byId[btn.dataset.id];
    if (PAGE.mode === "overview") {
      document.querySelector(".map-block").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
      focusPlace(p, { duration: 1600 });
      map.once("moveend", () => openPopup(p));
    } else {
      expandMap();
      setActive(p.id);
      focusPlace(p);
    }
  }));

  // ---- scrollytelling: follow the section being read ----
  if (PAGE.mode === "scrolly") {
    const story = document.querySelector(".story");
    const toggle = document.querySelector(".map-toggle");
    const sections = places.map((p) => document.getElementById(p.id));
    let current = undefined;
    let frame = 0;

    function pick() {
      frame = 0;
      const wide = innerWidth >= 960;
      const line = innerHeight * (wide ? 0.45 : 0.62);
      let id = null;
      for (const s of sections) if (s.getBoundingClientRect().top < line) id = s.id;
      if (id === current) return;
      current = id;
      setActive(id);
      if (id) focusPlace(byId[id]);
      else if (!located) showAll();
    }
    addEventListener("scroll", () => { if (!frame) frame = requestAnimationFrame(pick); }, { passive: true });
    map.on("load", pick);

    toggle.addEventListener("click", () => {
      const collapsed = story.classList.toggle("story--collapsed");
      toggle.textContent = collapsed ? "Vis kort" : "Skjul kort";
      toggle.setAttribute("aria-expanded", String(!collapsed));
      if (!collapsed) setTimeout(() => map.resize(), 50);
    });
    window.expandMap = () => { if (story.classList.contains("story--collapsed")) toggle.click(); };
  }
  function expandMap() { window.expandMap?.(); }

  // ---- Find nærmeste ----
  let located = false;
  let youMarker = null;
  const coordsOf = {};
  for (const f of areas.features) {
    (coordsOf[f.properties.id] ||= []).push(...flatten(f.geometry.coordinates));
  }
  function flatten(c) { return typeof c[0] === "number" ? [c] : c.flatMap(flatten); }
  function haversine(a, b) {
    const R = 6371, toRad = (d) => (d * Math.PI) / 180;
    const dLat = toRad(b[1] - a[1]), dLon = toRad(b[0] - a[0]);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function fmtKm(km) { return km < 1 ? "under 1 km" : km < 10 ? `${km.toFixed(1).replace(".", ",")} km` : `${Math.round(km)} km`; }

  document.querySelectorAll(".locate").forEach((btn) => btn.addEventListener("click", () => {
    const status = document.querySelector(".nearest__status");
    const list = document.querySelector(".nearest__list");
    if (!navigator.geolocation) { status.textContent = "Din browser kan ikke finde din placering."; return; }
    btn.disabled = true;
    status.textContent = "Finder din placering …";
    navigator.geolocation.getCurrentPosition((pos) => {
      btn.disabled = false;
      located = true;
      const you = [pos.coords.longitude, pos.coords.latitude];
      for (const p of places) {
        const pts = coordsOf[p.id]?.length ? coordsOf[p.id] : [[p.lon, p.lat]];
        p.km = Math.min(...pts.map((c) => haversine(you, c)));
      }
      const sorted = [...places].sort((a, b) => a.km - b.km);
      document.querySelectorAll(".distance").forEach((s) => {
        s.textContent = `${fmtKm(byId[s.dataset.id].km)} fra dig`;
        s.hidden = false;
      });
      status.textContent = "Nærmest dig (i luftlinje):";
      list.innerHTML = sorted.slice(0, 3)
        .map((p) => `<li><a href="#${p.id}">${p.name}</a> <span>· ${fmtKm(p.km)}</span></li>`).join("");
      list.hidden = false;
      btn.textContent = "Opdater min placering";

      const el = document.createElement("div");
      el.className = "you";
      el.title = "Du er her";
      youMarker?.remove();
      youMarker = new maplibregl.Marker({ element: el }).setLngLat(you).addTo(map);
      expandMap();
      const b = new maplibregl.LngLatBounds(you, you);
      sorted.slice(0, 3).forEach((p) => b.extend([p.lon, p.lat]));
      map.fitBounds(b, { padding: 60, maxZoom: 11, duration: reduceMotion ? 0 : 1400 });
      if (PAGE.mode === "overview") setActive(sorted[0].id);
    }, (err) => {
      btn.disabled = false;
      status.textContent = err.code === 1
        ? "Du har ikke givet adgang til din placering. Tillad det i browseren, og prøv igen."
        : "Vi kunne ikke finde din placering lige nu. Prøv igen om lidt.";
    }, { enableHighAccuracy: false, timeout: 15000, maximumAge: 600000 });
  }));
})();
