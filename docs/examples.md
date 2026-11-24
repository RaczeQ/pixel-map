# Examples

The first argument is a file that [GeoPandas](https://geopandas.org/en/stable/docs/user_guide/io.html) can open: GeoParquet, GeoJSON, GeoPackage, Shapefile and others. The files named after `--example` come with `pixel-map`.

```sh
$ pixel-map --example monaco_buildings
```

![Buildings of Monaco](images/monaco.png)

## Your own data

Here are the [urban areas of Natural Earth](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-urban-area/):

```sh
$ curl -sLO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_urban_areas.geojson
$ pixel-map ne_10m_urban_areas.geojson
```

![Urban areas of the world](images/urban_areas.png)

## Bounding box

`--bbox` takes west, south, east and north in degrees. The map is extended to the shape of the terminal:

```sh
$ pixel-map ne_10m_urban_areas.geojson --bbox -5,50.5,9,54
```

![Urban areas of England, Belgium and the Netherlands](images/bbox.png)

## Light mode

```sh
$ pixel-map ne_10m_urban_areas.geojson --bbox -5,50.5,9,54 --light
```

![Urban areas on the light basemap](images/light.png)

## Multiple files and colors

A color is anything that [matplotlib understands](https://matplotlib.org/stable/users/explain/colors/colors.html). Pass one per file, or one for all of them:

```sh
$ pixel-map --example london_buildings london_water london_park -c sandybrown,#33a1fd,C2
```

![Buildings, water and parks of London](images/colors.png)

## Opacity

The basemap shows through, and so do the overlapping files:

```sh
$ pixel-map --example london_buildings london_water london_park --light -c C1,C0,C2 -a 0.8,0.3,0.5
```

![Buildings, water and parks of London with three opacities](images/opacity.png)

## Full screen

```sh
$ pixel-map --example london_buildings --fullscreen
```

![Map without a border](images/fullscreen.png)

## Size

The map fills the terminal. `--width` and `--height` set other sizes, in columns and lines:

```sh
$ pixel-map --example monaco_buildings --width 120 --height 34
```

![Map of 120 columns and 34 lines](images/size.png){ width="50%" }
