"""Build the two mock-up pages from DN's original article HTML.

Usage:  python3 tools/build.py
Reads:  tools/source/*.src.html (saved copies of the dn.dk articles)
        tools/source/*.nominatim.geojson (OSM outlines fetched via Nominatim)
Writes: skove.html, soeer.html, data/*.geojson
"""
import hashlib, html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "source"
DN = "https://www.dn.dk"

# --- places --------------------------------------------------------------
# id, short name, lat, lon, outline keys (from the Nominatim files)
SKOVE = [
    ("rold-skov", "Rold Skov", 56.8038, 9.7832, ["rold"]),
    ("silkeborgskovene", "Silkeborgskovene", 56.1173, 9.6261, ["soenderskov"]),
    ("noeffelskoven", "Nøffelskoven", 54.9289, 9.6739, ["noeffel"]),
    ("dyrehaven", "Dyrehaven", 55.7942, 12.5665, ["dyrehaven"]),
    ("skovtaarnet", "Skovtårnet, Gisselfeld", 55.2532, 11.9770, []),
    ("naesbyhoved-skov", "Næsbyhoved Skov", 55.4133, 10.3734, ["naesbyhoved"]),
    ("boserup-skov", "Boserup Skov", 55.6627, 12.0398, ["boserup"]),
    ("gribskov", "Gribskov", 55.9977, 12.3332, ["gribskov"]),
    ("bolderslev-skov", "Bolderslev Skov", 55.0019, 9.3646, ["bolderslev"]),
    ("draved-skov", "Draved Skov", 55.0157, 8.9779, ["draved"]),
    ("orkanskoven", "Orkanskoven, Almindingen", 55.1120, 14.9350, ["almindingen"]),
    ("velling-skov", "Velling Skov", 56.0389, 9.5290, ["velling"]),
]
SOEER = [
    ("furesoe", "Furesø", None, None, ["furesoe"]),
    ("klosterhede", "Klosterhede Plantage", 56.4628, 8.4214, ["klosterhede", "flynder"]),
    ("arresoe", "Arresø", None, None, ["arresoe"]),
    ("lille-vildmose", "Tofte Sø, Lille Vildmose", 56.8818, 10.2138, ["lille-vildmose"]),
    ("esrum-soe", "Esrum Sø", None, None, ["esrum"]),
    ("maribosoeerne", "Maribosøerne", 54.7566, 11.5064, ["maribo-soendersoe", "maribo-noerresoe", "maribo-roegbolle"]),
    ("susaaen", "Susåen", 55.3040, 11.7390, ["susaa"]),
    ("gudenaaen", "Gudenåen", 56.1690, 9.5500, ["gudenaa"]),
    ("stubbe-soe", "Stubbe Sø", None, None, ["stubbe"]),
    ("nors-soe", "Nors Sø", None, None, ["nors"]),
    ("arreskov-soe", "Arreskov Sø", None, None, ["arreskov"]),
    ("hald-soe", "Hald Sø", None, None, ["hald"]),
    ("tissoe", "Tissø", None, None, ["tissoe"]),
]

# The fairy-tale post: coordinates from DN's own Google Maps embeds
# (Ravnsby Bakker from OSM; its embed is zoomed far out).
EVENTYR = [
    ("troldeskoven", "Troldeskoven, Tisvilde", 56.0345, 12.0141, []),
    ("dollerup-bakker", "Dollerup Bakker", 56.3712, 9.3105, []),
    ("svartingedalen", "Svartingedalen", 55.1889, 14.7390, []),
    ("moens-klint", "Møns Klint", 54.9841, 12.5415, []),
    ("ravnsby-bakker", "Ravnsby Bakker", 54.8966, 11.3546, []),
    ("raabjerg-mile", "Råbjerg Mile", 57.6482, 10.4037, []),
    ("himmelbjerget", "Himmelbjerget", 56.1042, 9.6782, []),
    ("mols-bjerge", "Mols Bjerge", 56.2980, 10.4955, []),
    ("fur", "Fur", 56.8213, 8.9470, []),
]

# --- parsing DN's article markup ----------------------------------------

def absolute(url):
    return DN + url if url.startswith("/") else url


def fix_links(fragment):
    fragment = re.sub(r'href="(/[^"]*)"', lambda m: f'href="{DN}{m.group(1)}"', fragment)
    fragment = re.sub(r'\s(target|data-router-slot)="[^"]*"', "", fragment)
    return fragment


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def text(s):
    return html.unescape(clean(re.sub(r"<[^>]+>", " ", s)))


def parse_blocks(path):
    raw = path.read_text()
    title = text(re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S).group(1))
    main = raw[raw.find("<main"):raw.find("</main>")]
    main = re.sub(r"<svg.*?</svg>", "", main, flags=re.S)
    parts = re.split(r'<div class="block-component', main)[1:]
    blocks = []
    for p in parts:
        if "script-component" in p and "<iframe" in p:
            src = re.search(r'<iframe[^>]*src="([^"]+)"', p).group(1)
            blocks.append({"type": "embed", "src": html.unescape(src)})
        elif "cta-component" in p:
            h = re.search(r"<h2[^>]*>(.*?)</h2>", p, re.S)
            body = re.search(r'<section class="rte-component">(.*?)</section>', p, re.S)
            a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', p, re.S)
            blocks.append({"type": "cta", "title": text(h.group(1)) if h else "",
                           "body": fix_links(clean(body.group(1))) if body else "",
                           "href": absolute(a.group(1)) if a else DN,
                           "label": text(a.group(2)) if a else "",
                           "bg": "blad" if "bg-blad" in p[:200] else "skov"})
        elif "image-card-component" in p:
            h = re.search(r"<h2[^>]*>(.*?)</h2>", p, re.S)
            img = re.search(r'<img src="([^"]+)"', p)
            credit = re.search(r'credits[^>]*>(.*?)</p>', p, re.S)
            tw = p.split("image-card-component__text-wrapper", 1)[1]
            tw = tw.split(">", 1)[1]
            tw = re.sub(r"<h2[^>]*>.*?</h2>", "", tw, count=1, flags=re.S)
            a = re.search(r'<a href="([^"]+)" class="button[^"]*"[^>]*>(.*?)</a>', tw, re.S)
            body = re.sub(r'<a href="[^"]+" class="button.*?</a>', "", tw, flags=re.S)
            body = re.sub(r'^\s*<p class="image-card-component__text[^"]*">', "", body)
            body = re.sub(r"(</div>\s*)+</section>.*$", "", body, flags=re.S)
            body = re.sub(r"</p>\s*</p>", "</p>", body)
            ctitle = text(h.group(1)) if h else ""
            blocks.append({"type": "card", "title": "" if ctitle in ("", "ㅤ") else ctitle,
                           "img": absolute(html.unescape(img.group(1))) if img else "",
                           "credit": text(credit.group(1)) if credit else "",
                           "body": fix_links(clean(body)),
                           "button": {"href": absolute(a.group(1)), "label": text(a.group(2))} if a else None,
                           "bg": "blad" if "bg-blad" in p else "kridt",
                           "reverse": "flex-reverse" in p})
        elif "image-and-text-component" in p:
            img = re.search(r'<img src="([^"]+)"', p)
            credit = re.search(r'credits[^>]*>(.*?)</p>', p, re.S)
            blocks.append({"type": "image", "img": absolute(html.unescape(img.group(1))),
                           "credit": text(credit.group(1)) if credit else ""})
        elif "fact-box" in p:
            h = re.search(r"<h2[^>]*>(.*?)</h2>", p, re.S)
            body = re.search(r'<div class="style-body-small">(.*?)</div>\s*</div>\s*</article>', p, re.S)
            blocks.append({"type": "fact", "title": text(h.group(1)), "body": fix_links(clean(body.group(1)))})
        elif "rte-component" in p:
            body = re.search(r'<section class="rte-component">(.*?)</section>', p, re.S).group(1)
            # split at <h3> so every place heading starts its own block
            for seg in re.split(r"(?=<h3>)", clean(body)):
                if seg.strip():
                    blocks.append({"type": "rte", "body": fix_links(seg.strip())})
    return title, blocks


def heading_of(block):
    if block["type"] == "rte":
        m = re.match(r"<h3>(.*?)</h3>", block["body"])
        return text(m.group(1)) if m else None
    if block["type"] == "card" and block["title"] and block["title"] != "Bliv naturbeskytter":
        return block["title"]
    return None


def group(blocks, places):
    """Split blocks into intro, one group per place (in order), outro."""
    intro, groups, outro = [], [], []
    for i, b in enumerate(blocks):
        is_last_cta = b["type"] == "cta" and i == len(blocks) - 1
        h = heading_of(b)
        if is_last_cta:
            outro.append(b)
        elif h:
            groups.append({"heading": h, "blocks": [b]})
        elif groups:
            groups[-1]["blocks"].append(b)
        else:
            intro.append(b)
    assert len(groups) == len(places), (len(groups), [g["heading"] for g in groups])
    return intro, groups, outro


# --- geometry ------------------------------------------------------------

def rnd(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 4), round(c[1], 4)]
    return [rnd(x) for x in c]


def outlines(path):
    fc = json.loads(path.read_text())
    best = {}
    for f in fc["features"]:
        k = f["properties"]["key"]
        cat = f["properties"]["category"]
        if k in best or f["geometry"]["type"] == "Point":
            continue
        if k == "stubbe" and "Syddjurs" not in f["properties"]["display_name"]:
            continue
        if cat in ("water", "waterway", "landuse", "natural", "leisure"):
            best[k] = f["geometry"]
    return best


def bbox(geoms):
    xs, ys = [], []
    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c: walk(x)
    for g in geoms: walk(g["coordinates"])
    return [min(xs), min(ys), max(xs), max(ys)]


def make_places(spec, groups, shapes):
    places, areas = [], []
    for n, ((pid, name, lat, lon, keys), g) in enumerate(zip(spec, groups), start=1):
        geoms = [shapes[k] for k in keys if k in shapes]
        box = bbox(geoms) if geoms else None
        if lat is None:
            lon, lat = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        img = next((b["img"] for b in g["blocks"] if b.get("img")), "")
        places.append({"id": pid, "n": n, "name": name, "heading": g["heading"],
                       "lon": round(lon, 4), "lat": round(lat, 4), "img": img,
                       "bbox": [round(v, 4) for v in box] if box else None})
        for k in keys:
            if k in shapes:
                gtype = shapes[k]["type"]
                areas.append({"type": "Feature", "properties": {"id": pid,
                              "kind": "line" if "Line" in gtype else "area"},
                              "geometry": {"type": gtype, "coordinates": rnd(shapes[k]["coordinates"])}})
    return places, {"type": "FeatureCollection", "features": areas}


# --- HTML ----------------------------------------------------------------

def thumb(url, size=160):
    base = url.split("?")[0]
    q = url.split("?")[1] if "?" in url else ""
    keep = "&".join(x for x in q.split("&") if x.startswith(("cc=", "rxy=", "v=")))
    return f"{base}?{keep}&width={size}&height={size}&rmode=crop&format=webp".replace("?&", "?")


def wide(url, w=1280):
    base = url.split("?")[0]
    q = url.split("?")[1] if "?" in url else ""
    keep = "&".join(x for x in q.split("&") if x.startswith(("cc=", "rxy=", "v=")))
    return f"{base}?{keep}&width={w}&format=webp&quality=85".replace("?&", "?")


def render_block(b, place=None):
    t = b["type"]
    if t == "rte":
        body = b["body"]
        if place and body.startswith("<h3>"):
            body = re.sub(r"^<h3>(.*?)</h3>", lambda m: place_heading(m.group(1), place), body)
        body = re.sub(r"^<h2>(.*?)</h2>", r'<p class="lead">\1</p>', body)
        return f'<div class="rte col">{body}</div>'
    if t == "image":
        cr = f'<p class="credit">{html.escape(b["credit"])}</p>' if b["credit"] else ""
        return f'<figure class="wide-image"><img src="{wide(b["img"])}" alt="" loading="lazy">{cr}</figure>'
    if t == "card":
        head = place_heading(html.escape(b["title"]), place, tag="h2") if (place and b["title"]) else \
            (f'<h2 class="h3">{html.escape(b["title"])}</h2>' if b["title"] else "")
        cr = f'<p class="credit">{html.escape(b["credit"])}</p>' if b["credit"] else ""
        btn = f'<a class="button" href="{b["button"]["href"]}">{html.escape(b["button"]["label"])}</a>' if b["button"] else ""
        cls = "card" + (" card--blad" if b["bg"] == "blad" else "") + (" card--reverse" if b["reverse"] else "")
        return (f'<section class="{cls}"><div class="card__image"><img src="{wide(b["img"], 960)}" alt="" loading="lazy">{cr}</div>'
                f'<div class="card__text">{head}{b["body"]}{btn}</div></section>')
    if t == "fact":
        return f'<aside class="fact col"><h2 class="h4">{html.escape(b["title"])}</h2>{b["body"]}</aside>'
    if t == "cta":
        return (f'<section class="cta cta--{b["bg"]}"><div class="cta__inner"><h2 class="h3">{html.escape(b["title"])}</h2>'
                f'{b["body"]}<a class="button button--light" href="{b["href"]}">{html.escape(b["label"])}</a></div></section>')
    if t == "embed":
        return (f'<div class="embed"><iframe src="{html.escape(b["src"])}" loading="lazy" '
                f'title="Google Maps-kort" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe></div>')
    raise ValueError(t)


def place_heading(inner, place, tag="h3"):
    cls = ' class="h3"' if tag == "h2" else ""
    return (f'<{tag}{cls}>{inner}</{tag}>'
            f'<p class="place-meta"><button type="button" class="show-on-map" data-id="{place["id"]}">'
            f'<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>'
            f'Vis på kortet</button></p>')


HEAD = """<!doctype html>
<html lang="da">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} – forslag med kort</title>
<meta name="description" content="Mockup: DN's guide med et kort over stederne.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&display=swap">
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css">
<link rel="stylesheet" href="assets/style.css?v={v}">
</head>
"""

HEADER = """<div class="mock-banner" id="mock-banner">
  <p><strong>Forslag:</strong> Sådan kunne guiden se ud med et kort. Dette er en mockup, ikke en officiel DN-side.
  <a href="{orig}">Se originalen på dn.dk</a></p>
  <button type="button" class="mock-banner__close" aria-label="Luk">×</button>
</div>
<header class="site-header">
  <div class="site-header__inner">
    <a class="logo" href="./" aria-label="Til forsiden af forslaget">
      <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M19 20C12 6 4 6 3 12c-1 7 6 9 16 8zM21 20c7-14 15-14 16-8 1 7-6 9-16 8zM19 21c-9 0-15 3-13 10 2 5 9 3 13-10zM21 21c9 0 15 3 13 10-2 5-9 3-13-10z"/></svg>
      <span>Danmarks<br>Naturfrednings<br>forening</span>
    </a>
    <a class="pill" href="https://www.dn.dk/">Støt nu</a>
  </div>
</header>
<section class="hero">
  <svg class="hero__wings" viewBox="0 0 600 400" aria-hidden="true"><path d="M300 200C220 40 90 20 60 90c-30 80 60 120 240 110zM310 200c80-160 210-180 240-110 30 80-60 120-240 110z"/></svg>
  <div class="hero__inner"><h1>{h1}</h1></div>
</section>
<nav class="breadcrumb" aria-label="Brødkrumme"><ol>
  <li><a href="https://www.dn.dk/">dn.dk</a></li>
  <li><a href="https://www.dn.dk/oplev-naturen/">Oplev naturen</a></li>
  <li><a href="https://www.dn.dk/oplev-naturen/saerlige-naturoplevelser/">Særlige naturoplevelser</a></li>
  <li aria-current="page">{crumb}</li>
</ol></nav>
"""

FOOT = """<footer class="mock-footer"><p>Mockup lavet som forslag til Danmarks Naturfredningsforening. Tekst og fotos: DN og de nævnte fotografer, fra <a href="{orig}">den originale artikel</a>.
Kort: <a href="https://openfreemap.org">OpenFreeMap</a> © <a href="https://www.openmaptiles.org/">OpenMapTiles</a>, data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap-bidragydere</a>.</p></footer>
<script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
<script>window.PAGE = {config};</script>
<script src="assets/app.js?v={v}"></script>
</body>
</html>
"""

MAP_OVERVIEW = """<section class="map-block" aria-label="{label}">
  <div class="map-block__head col">
    <h2 class="h3">{heading}</h2>
    <p>Tryk på et billede for at se stedet, og tryk igen for at læse mere.</p>
  </div>
  <div class="map-frame"><div id="map" class="map"></div></div>
</section>
"""


# cache-busting tag: changes whenever the CSS or JS changes
VERSION = hashlib.sha1(b"".join((ROOT / "assets" / f).read_bytes() for f in ("style.css", "app.js"))).hexdigest()[:8]


def build(slug, src, spec, shape_file, mode, orig, crumb, kind_word, map_heading=""):
    title, blocks = parse_blocks(SRC / src)
    intro, groups, outro = group(blocks, spec)
    places, areas = make_places(spec, groups, outlines(SRC / shape_file) if shape_file else {})
    for p in places:
        p["thumb"] = thumb(p["img"]) if p["img"] else ""
        p["card"] = wide(p["img"], 560) if p["img"] else ""
    (ROOT / "data" / f"{slug}-omraader.geojson").write_text(json.dumps(areas, ensure_ascii=False, separators=(",", ":")))

    out = [HEAD.format(title=html.escape(crumb), v=VERSION), f'<body class="page--{mode}">',
           HEADER.format(orig=orig, h1=html.escape(title), crumb=html.escape(crumb))]
    out.append('<main class="article">')
    if mode == "overview":
        out += [render_block(b) for b in intro]
        out.append(MAP_OVERVIEW.format(label=map_heading, heading=map_heading))
        for p, g in zip(places, groups):
            out.append(f'<div class="place" id="{p["id"]}" data-id="{p["id"]}">')
            out += [render_block(b, p if i == 0 else None) for i, b in enumerate(g["blocks"])]
            out.append("</div>")
    else:
        out += [render_block(b) for b in intro if not heading_of(b)]
        out.append('<div class="story">')
        out.append('<div class="story__map"><div class="map-frame"><div id="map" class="map"></div>'
                   '<button type="button" class="map-toggle" aria-expanded="true">Skjul kort</button></div></div>')
        out.append('<div class="story__text">')
        for p, g in zip(places, groups):
            out.append(f'<div class="place" id="{p["id"]}" data-id="{p["id"]}">')
            out += [render_block(b, p if i == 0 else None) for i, b in enumerate(g["blocks"])]
            out.append("</div>")
        out.append("</div></div>")
    out += [render_block(b) for b in outro]
    out.append("</main>")
    config = {"mode": mode, "areas": f"data/{slug}-omraader.geojson", "places": places, "kindWord": kind_word}
    out.append(FOOT.format(orig=orig, config=json.dumps(config, ensure_ascii=False), v=VERSION))
    (ROOT / f"{slug}.html").write_text("\n".join(out))
    print(slug, len(places), "places,", len(areas["features"]), "outlines")


build("skove", "skove.src.html", SKOVE, "forests.nominatim.geojson", "overview",
      "https://www.dn.dk/oplev-naturen/saerlige-naturoplevelser/12-vidunderlige-skove-i-danmark/",
      "12 vidunderlige skove i Danmark", "skov", "Se skovene på kortet")
build("soeer", "soeer.src.html", SOEER, "water.nominatim.geojson", "scrolly",
      "https://www.dn.dk/oplev-naturen/saerlige-naturoplevelser/13-vidunderlige-soer-og-vandlob-i-danmark",
      "13 vidunderlige søer og vandløb i Danmark", "sø eller å")
build("eventyr", "eventyr.src.html", EVENTYR, None, "overview",
      "https://www.dn.dk/oplev-naturen/saerlige-naturoplevelser/9-steder-i-danmark-her-ligner-naturen-noget-fra-et-eventyr/",
      "9 steder i Danmark, der ligner noget fra et eventyr", "sted", "Se de 9 steder på kortet")
