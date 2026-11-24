# Renderers

A renderer picks the character of every cell of the terminal, and its two colors, that come closest to the map. `--renderer` sets which characters it picks from.

## block

Quarters and eighths of a cell. The default.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r block
```

![block](images/renderer_block.png)

## half

Upper and lower halves of a cell, which make square pixels.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r half
```

![half](images/renderer_half.png)

## quad

Quarters of a cell.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r quad
```

![quad](images/renderer_quad.png)

## space

Only the background of the cells.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r space
```

![space](images/renderer_space.png)

## braille

Braille patterns, with eight dots in a cell.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r braille
```

![braille](images/renderer_braille.png)

## braille-bw

Braille patterns without colors, for a terminal that has none. They look best without a basemap.

```sh
$ pixel-map --example london_buildings london_water -c white --no-bg -r braille-bw
```

![braille-bw](images/renderer_braille_bw.png)

## ascii

Characters of ASCII.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r ascii
```

![ascii](images/renderer_ascii.png)

## ascii-bw

Characters of ASCII without colors.

```sh
$ pixel-map --example london_buildings london_water -c white --no-bg -r ascii-bw
```

![ascii-bw](images/renderer_ascii_bw.png)

## all

Characters of all the renderers above.

```sh
$ pixel-map --example london_buildings london_water -c C1,C0 -r all
```

![all](images/renderer_all.png)
