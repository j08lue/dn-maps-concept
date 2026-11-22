# DN guides with maps – design

## Intent
Show Danmarks Naturfredningsforening (DN) how their "best places" guides could include a map,
so readers can see at a glance which places are near them. Jonas sends the link to DN with his
own pitch in an email. The mock-ups must look like dn.dk today so the idea feels realistic.

## Goals
- Two mock-ups that copy two real DN guides closely (text, photos, credits, layout, colours).
- Mobile first; works well on desktop too.
- Show two levels of ambition so DN can choose:
  - **Skove** ("12 vidunderlige skove"): overview map at the top with round photo markers.
  - **Søer og vandløb** ("13 vidunderlige søer og vandløb"): map pinned to the top of the screen
    (side column on desktop) that flies to each place as the reader scrolls.
- "Find nærmeste" on both: uses the phone's location, shows "xx km fra dig" on each place and
  lets the reader jump to the nearest.

## Non-goals / anti-goals
- No pitch text on the pages (Jonas writes that in the email).
- No new DN content, no redesign of their page. If it looks like a different website, it fails.
- The map must not trap scrolling on phones (one finger scrolls the page).

## Approaches considered
- **MapLibre GL + OpenFreeMap vector tiles (chosen):** free, no key, smooth fly-to for
  scrollytelling, restyled to DN's greens/cream, rivers and areas drawn as lines/outlines.
- Leaflet + raster tiles: lighter, but choppy fly-to and a styled basemap needs a keyed provider.
- Hosting: claude.ai Artifact (chosen) over GitHub Pages; plain static files, so a move later is easy.

## Decided
- Danish throughout. DN's photos loaded from dn.dk, with their photo credits kept.
- Small dismissible banner on each page: "Forslag/mockup – se originalen" with a link.
- Minimal index page: two links, nothing else.
- Rivers (Gudenå, Susåen) as lines; large areas may get an outline if easy, otherwise a point.
- Marker tap on mobile opens a small card (photo, name, "Læs mere ↓"), not a direct jump.

## Left to the builder (Claude's calls)
- Free font close to SommerfuglSans (e.g. DM Sans).
- Exact basemap colours, marker size, map heights (~60% of screen for overview, ~35% pinned).
- Coordinates per place (checked by hand); river geometry from OpenStreetMap, simplified.
