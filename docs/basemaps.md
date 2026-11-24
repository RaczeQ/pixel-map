# Basemaps

The map under your data is a [MapLibre style](https://maplibre.org/maplibre-style-spec/) without its labels, drawn by [basemaplibre](https://raczeq.github.io/basemaplibre/): `OpenFreeMap.Dark` by default and `OpenFreeMap.Positron` with `--light`.

```sh
$ pixel-map --example london_water
```

![OpenFreeMap.Dark](images/basemap_dark.png)

```sh
$ pixel-map --example london_water --light
```

![OpenFreeMap.Positron](images/basemap_light.png)

## Other styles

`--basemap` takes a name from the [style gallery of basemaplibre](https://raczeq.github.io/basemaplibre/gallery/):

```sh
$ pixel-map --example london_water -t VersaTiles.Colorful -c blue
```

![VersaTiles.Colorful](images/basemap_colorful.png)

It can be satellite imagery or a relief:

```sh
$ pixel-map --example london_water -t VersaTiles.Satellite -c C0 -a 0.6
```

![VersaTiles.Satellite](images/basemap_satellite.png)

```sh
$ curl -sLO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_urban_areas.geojson
$ pixel-map ne_10m_urban_areas.geojson --bbox 5,43,11,47 -t Mapterhorn.Relief -c black
```

![Mapterhorn.Relief](images/basemap_relief.png)

The URL or the path of a style JSON works as well:

```sh
$ pixel-map --example london_buildings -t https://tiles.openfreemap.org/styles/bright
```

![A style of a URL](images/basemap_url.png)

## Raster tiles

Anything else is drawn by [contextily](https://contextily.readthedocs.io/), if you have it installed (`pip install contextily`): a provider of [xyzservices](https://xyzservices.readthedocs.io/en/stable/gallery.html) or a URL of tiles.

```sh
$ pixel-map --example london_buildings -t OpenTopoMap -c red
```

![OpenTopoMap](images/basemap_raster.png)

## No basemap

`--no-background` leaves only your data, on black or on the color of `--background-color`:

```sh
$ pixel-map --example london_buildings --no-background
```

![No basemap](images/basemap_none.png)

```sh
$ pixel-map --example london_buildings --no-background --background-color midnightblue -c gold
```

![No basemap on a color](images/basemap_color.png)
