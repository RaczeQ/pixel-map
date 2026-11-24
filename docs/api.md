# Python API

`pixel-map` is a command line tool, but its map can be printed from Python too:

```python
from pixel_map.plotter import plot_geo_data

plot_geo_data(["buildings.parquet"], renderer="block", basemap_provider="OpenFreeMap.Dark")
```

::: pixel_map.plotter
    options:
      members:
        - plot_geo_data
        - get_predefined_dark_style
        - get_predefined_light_style
        - BasemapError
