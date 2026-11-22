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
      layer.layout["text-field"] = ["coalesce", ["get", "name:da"], ["get", "name"], ["get", "name:latin"]];
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
      "GeolocateControl.FindMyLocation": "Vis min placering",
      "GeolocateControl.LocationNotAvailable": "Din placering er ikke tilgængelig",
    },
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
  map.addControl(new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: false, timeout: 15000 },
    fitBoundsOptions: { maxZoom: 9 },
    trackUserLocation: false,
  }), "top-left");

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

  // Overview page: keep regional context (zoom ~7.5 on phones) instead of zooming to the feature.
  // Story page: frame the lake or river itself.
  function focusPlace(p, opts = {}) {
    const duration = reduceMotion ? 0 : opts.duration ?? 1400;
    if (PAGE.mode === "overview") {
      const zoom = innerWidth < 600 ? 6.4 : 7.2;
      map.flyTo({ center: [p.lon, p.lat], zoom, offset: opts.offset || [0, 0], duration });
    } else if (p.bbox) {
      map.fitBounds([[p.bbox[0], p.bbox[1]], [p.bbox[2], p.bbox[3]]], { padding: 48, maxZoom: 11.5, duration });
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
      if (PAGE.mode === "overview") openPopup(p, true);
      else scrollToPlace(p);
    });
    p.marker = new maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).addTo(map);
  }

  function scrollToPlace(p) {
    document.getElementById(p.id).scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  }

  // ---- overview popups: small card, the whole card links to the story ----
  const popup = new maplibregl.Popup({ offset: 26, maxWidth: "200px", focusAfterOpen: false, className: "pop-wrap" });
  popup.on("close", () => setActive(null));
  function openPopup(p, recentre) {
    // move the marker below the centre so the card above it fits inside the map
    if (recentre) map.easeTo({ center: [p.lon, p.lat], offset: [0, 70], duration: reduceMotion ? 0 : 500 });
    popup.setLngLat([p.lon, p.lat]).setHTML(
      `<a class="pop" href="#${p.id}">${p.card ? `<img src="${p.card}" alt="">` : ""}
        <span class="pop__body"><strong>${p.name}</strong><span class="pop__more">Læs mere ↓</span></span></a>`).addTo(map);
    setActive(p.id);
  }

  // ---- "Vis på kortet" buttons in each section ----
  document.querySelectorAll(".show-on-map").forEach((btn) => btn.addEventListener("click", () => {
    const p = byId[btn.dataset.id];
    if (PAGE.mode === "overview") {
      document.querySelector(".map-block").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
      popup.remove();
      focusPlace(p, { duration: 1600, offset: [0, 70] });
      map.once("moveend", () => openPopup(p, false));
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
    let current;
    let frame = 0;

    function pick() {
      frame = 0;
      const line = innerHeight * (innerWidth >= 960 ? 0.45 : 0.62);
      let id = null;
      for (const s of sections) if (s.getBoundingClientRect().top < line) id = s.id;
      if (id === current) return;
      current = id;
      setActive(id);
      if (id) focusPlace(byId[id]);
      else showAll();
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
})();
