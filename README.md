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
- Python dependencies:

pip install requests pandas geopandas matplotlib cartopy shapely pyproj fiona

Note: cartopy, fiona, and pyproj may require system libraries depending on your OS.

---

## Usage

Open the notebook:

```bash
jupyter notebook myworld.ipynb

or in JupyterLab:

jupyter lab myworld.ipynb

Then run all cells to generate the map.

```markdown
Alternatively, open the notebook directly in VS Code or any compatible environment.

The output is saved as:

- PNG (high resolution)  
- SVG (vector format)
- PDF (vector format)

---

## Configuration

Edit the following variables in the script:

lived_in = {...}
visited = {...}
visited_states = {...}

Example:

visited_states = {
    ("Germany", "Bayern"),
    ("China", "Beijing Municipality"),
}

---

## Projection

Set:

projection_mode = "mercator"

Available options:

- robinson_europe  
- robinson_bering  
- mercator  

---

## Detail Control

ADM1 geometries are simplified to match the coarse base map:

ADM1_SIMPLIFY_TOLERANCE = 0.15

- higher → less detail, faster  
- lower → more detail, slower  

---

## Naming Consistency

Different datasets use different country names.

Example:

- Natural Earth → People's Republic of China  
- Input → China  

The script resolves this via:

country_name_map = {
    "China": "People's Republic of China",
}

---

## Data Sources

Natural Earth (countries, coastline)  
https://www.naturalearthdata.com/  

geoBoundaries (ADM1 regions)  
https://www.geoboundaries.org/  

---

## Performance

Only relevant countries are processed:

countries_with_subdivisions = visited | lived_in

This significantly reduces runtime.

---

## Debugging

Inspect available region names:

print(sorted(
    adm1_all.loc[adm1_all["country_name"] == "People's Republic of China", "state_name"].unique()
))

Inspect country names:

print(sorted(countries[country_name_col].unique()))

---

## Output

The script generates:

- travel_map_*.png  
- travel_map_*.svg
- travel_map_*.pdf  


---

## Notes

- Country names must match dataset naming (after normalization)  
- ADM1 naming is not fully standardized  
- Geometry simplification ensures visual consistency  
- The map prioritizes clarity over geographic precision  

---

## License

This repository contains code only.

Data licenses:
- Natural Earth → public domain  
- geoBoundaries → open license  
