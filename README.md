# DN-guides med kort (forslag)

A mock-up showing how two of Danmarks Naturfredningsforening's guides could include a map of the places they recommend.

- **[12 vidunderlige skove](https://j08lue.github.io/dn-maps-concept/skove.html)**: an overview map at the top with photo markers.
- **[13 vidunderlige søer og vandløb](https://j08lue.github.io/dn-maps-concept/soeer.html)**: a map that follows along as you read (pinned at the top on phones, beside the text on desktop).

Text and photos come from the original articles on dn.dk and belong to DN and the credited photographers. Photos are loaded directly from dn.dk.
Map: [MapLibre GL JS](https://maplibre.org), tiles from [OpenFreeMap](https://openfreemap.org) (© OpenMapTiles, © OpenStreetMap contributors). Outlines of lakes, rivers and forests are from OpenStreetMap, fetched via Nominatim.

## Rebuild

```bash
curl -sL -o tools/source/skove.src.html https://www.dn.dk/oplev-naturen/saerlige-naturoplevelser/12-vidunderlige-skove-i-danmark/
curl -sL -o tools/source/soeer.src.html https://www.dn.dk/oplev-naturen/saerlige-naturoplevelser/13-vidunderlige-soer-og-vandlob-i-danmark
python3 tools/build.py
python3 -m http.server
```

`design.md` holds the design notes.
