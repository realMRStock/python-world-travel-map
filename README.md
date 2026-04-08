# 🌍 World Travel Map Generator

This repository demonstrates how to generate world maps visualizing personal travel history using Python.

The script combines Natural Earth and geoBoundaries datasets with GeoPandas, Matplotlib, and Cartopy to create consistent and minimal maps.

The map highlights:
- visited countries  
- lived-in countries  
- selected administrative regions (ADM1)  

---

## Features

- 🗺️ World map visualization  
  - Low–detail global map (~110m resolution)  
  - Multiple projections (Robinson, Mercator)  
  - Consistent styling across all regions  

- 🎨 Clean design  
  - Minimal color palette  
  - Thin borders and outlines  
  - Helvetica / sans–serif typography  

- 🌐 Administrative region support (ADM1)  
  - Highlight specific states / provinces  
  - Internal borders shown only for relevant countries  
  - Geometry simplification for visual consistency  

- ⚙️ Flexible configuration  
  - Custom lists for visited and lived–in countries  
  - Custom highlighted regions  
  - Adjustable level of detail  

- ⚡ Efficient data loading  
  - Loads subdivisions only for selected countries  
  - Avoids unnecessary global processing  

---

## Requirements

- Python ≥ 3.8  

Install dependencies:

```bash
pip install requests pandas geopandas matplotlib cartopy shapely pyproj fiona
```

Note: `cartopy`, `fiona`, and `pyproj` may require system libraries.

---

## Usage

Run the script:

```bash
python myworld.py
```

The output is saved as:

- PNG (high resolution)  
- SVG (vector format)  
- PDF (vector format)  

---

## Configuration

Edit the following variables in the script:

```python
lived_in = {...}
visited = {...}
visited_states = {...}
```

Example:

```python
visited_states = {
    ("Germany", "Bayern"),
    ("People's Republic of China", "Beijing Municipality"),
}
```

---

## Projection

Set:

```python
projection_mode = "robinson_europe"
```

Available options:

- robinson_europe  
- robinson_bering  
- mercator  

---

## Detail Control

ADM1 geometries are simplified to match the coarse base map:

```python
ADM1_SIMPLIFY_TOLERANCE = 0.15
```

- higher → less detail, faster  
- lower → more detail, slower  

---

## Naming Consistency

Different datasets use different country names.

Example:

- Natural Earth → People's Republic of China  
- Input → China  

The script resolves this via internal normalization.

---

## Data Sources

- Natural Earth (countries, coastline)  
  https://www.naturalearthdata.com/  

- geoBoundaries (ADM1 regions)  
  https://www.geoboundaries.org/  

---

## Performance

Only relevant countries are processed:

```python
countries_with_subdivisions = visited | lived_in
```

This significantly reduces runtime.

---

## Debugging

Inspect available region names:

```python
print(sorted(
    adm1_all.loc[
        adm1_all["country_name"] == "People's Republic of China",
        "state_name"
    ].unique()
))
```

Inspect country names:

```python
print(sorted(countries[country_name_col].unique()))
```

---

## Output

The script generates:

- travel_map_*.png  
- travel_map_*.svg  
- travel_map_*.pdf  

---

## Notes

- Country names must match dataset naming  
- ADM1 naming is not fully standardized  
- Geometry simplification ensures visual consistency  
- The map prioritizes clarity over geographic precision  

---

## Disclaimer

Map boundaries follow the underlying data sources (Natural Earth, geoBoundaries) and do not imply any political position.

---

## License

This repository contains code only and is licensed under the MIT License.

Data sources are subject to their own licenses:

- Natural Earth → Public Domain
- geoBoundaries → https://www.geoboundaries.org/
