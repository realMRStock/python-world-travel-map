import requests
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# -----------------------------
# 1) User input
# -----------------------------
# Countries where you have lived
lived_in = {
    "Germany",
    "France",
    "United States of America",
    # "People's Republic of China",
}

# Countries you have visited
visited = {
    "Germany",
    "France",
    "Austria",
    "Switzerland",
    "Luxembourg",
    "Netherlands",
    "Belgium",
    "United Kingdom",
    "Ireland",
    "United States of America",
    "Chile",
    "Vietnam",
    "Spain",
    "Portugal",
    "Czech Republic",
    "Sweden",
    "Italy",
    "Croatia",
    "Russia",
    "Greece",
    "People's Republic of China",
}

# Specific visited first-level administrative regions (ADM1)
visited_states = {
    ("Germany", "Bayern"),
    ("Germany", "Berlin"),
    ("Germany", "Hamburg"),
    ("Germany", "Nordrhein-Westfalen"),
    ("Germany", "Baden-Württemberg"),
    ("Germany", "Sachsen"),
    ("Germany", "Schleswig-Holstein"),
    ("Germany", "Rheinland-Pfalz"),

    ("Austria", "Wien"),
    ("Austria", "Tirol"),
    ("Austria", "Salzburg"),

    ("France", "Île-de-France"),
    ("France", "Grand Est"),

    ("Russia", "Moscow"),
    ("Russia", "Irkutsk Oblast"),

    ("People's Republic of China", "Beijing Municipality"),
    ("People's Republic of China", "Guangxi Zhuang Autonomous Region"),
    ("People's Republic of China", "Guangzhou Province"),

    ("United States of America", "Hawaii"),
    ("United States of America", "Indiana"),
    ("United States of America", "Kentucky"),

    ("Chile", "RegiÃ³n Metropolitana de Santiago"),
    ("Chile", "RegiÃ³n de Antofagasta"),
    ("Chile", "RegiÃ³n de Los Lagos"),
}

# Manual ISO3 fallback mapping for countries whose code may not be read cleanly
iso3_map = {
    "Germany": "DEU",
    "France": "FRA",
    "Austria": "AUT",
    "Chile": "CHL",
    "United States of America": "USA",
    "Russia": "RUS",
    "People's Republic of China": "CHN",
    "Switzerland": "CHE",
    "Luxembourg": "LUX",
    "Netherlands": "NLD",
    "Belgium": "BEL",
    "United Kingdom": "GBR",
    "Ireland": "IRL",
    "Vietnam": "VNM",
    "Spain": "ESP",
    "Portugal": "PRT",
    "Czech Republic": "CZE",
    "Sweden": "SWE",
    "Italy": "ITA",
    "Croatia": "HRV",
    "Greece": "GRC",
}

# -----------------------------
# 1b) Projection settings
# -----------------------------
# Available options:
#   "robinson_europe"
#   "robinson_bering"
#   "mercator"
projection_mode = "robinson_europe"

# -----------------------------
# 1c) Detail control
# -----------------------------
# Simplify highlighted ADM1 geometries slightly for visual consistency.
# Internal borders are derived from original ADM1 polygons first and only
# then lightly simplified as lines.
ADM1_SIMPLIFY_TOLERANCE = 0.18

# -----------------------------
# 2) Data loading functions
# -----------------------------
def load_ne_countries() -> gpd.GeoDataFrame:
    """Load low-detail world country polygons from Natural Earth."""
    gdf = gpd.read_file(
        "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
    )
    gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    return gdf


def load_ne_coastline() -> gpd.GeoDataFrame:
    """Load low-detail world coastline from Natural Earth."""
    gdf = gpd.read_file(
        "https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_coastline.zip"
    )
    gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    return gdf


def load_gb_adm1(iso3: str) -> gpd.GeoDataFrame:
    """Load first-level administrative boundaries (ADM1) from geoBoundaries."""
    api_url = f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM1/"
    meta = requests.get(api_url, timeout=60).json()

    download_url = meta.get("simplifiedGeometryGeoJSON") or meta.get("gjDownloadURL")
    if not download_url:
        raise RuntimeError(f"No download URL found for {iso3}.")

    gdf = gpd.read_file(download_url)
    gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    return gdf


def detect_name_column(gdf: gpd.GeoDataFrame) -> str:
    """Detect the most likely column containing ADM1 names."""
    candidates = [
        "shapeName", "shapeNAME", "name", "Name",
        "ADM1_NAME", "admin1Name", "shapeGroup"
    ]
    for col in candidates:
        if col in gdf.columns:
            return col

    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        if pd.api.types.is_object_dtype(gdf[col]):
            return col

    raise RuntimeError("No plausible ADM1 name column found.")


def add_country_name_column(
    gdf: gpd.GeoDataFrame,
    country_name: str,
    state_name_col: str
) -> gpd.GeoDataFrame:
    """Add standardized country and state name columns before merging."""
    out = gdf.copy()
    out["country_name"] = country_name
    out["state_name"] = out[state_name_col].astype(str)
    return out


def simplify_geometries(gdf: gpd.GeoDataFrame, tolerance: float) -> gpd.GeoDataFrame:
    """Reduce polygon geometry complexity."""
    out = gdf.copy()
    out["geometry"] = out.geometry.simplify(
        tolerance=tolerance,
        preserve_topology=True
    )
    out = out[out.geometry.notnull() & ~out.geometry.is_empty].copy()
    return out


def simplify_line_geometries(gdf: gpd.GeoDataFrame, tolerance: float) -> gpd.GeoDataFrame:
    """Lightly simplify line geometries after unique border extraction."""
    out = gdf.copy()
    out["geometry"] = out.geometry.simplify(
        tolerance=tolerance,
        preserve_topology=False
    )
    out = out[out.geometry.notnull() & ~out.geometry.is_empty].copy()
    return out


def build_unique_internal_boundaries(adm1_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Create unique shared internal borders between neighboring ADM1 polygons."""
    from shapely.ops import unary_union, linemerge

    records = []

    for country, group in adm1_gdf.groupby("country_name"):
        group = group.reset_index(drop=True)

        if len(group) < 2:
            continue

        shared_segments = []

        # Compare each polygon pair only once
        for i in range(len(group)):
            geom_i = group.geometry.iloc[i]
            if geom_i is None or geom_i.is_empty:
                continue

            for j in range(i + 1, len(group)):
                geom_j = group.geometry.iloc[j]
                if geom_j is None or geom_j.is_empty:
                    continue

                # Only neighboring polygons can share an internal border
                if not geom_i.touches(geom_j):
                    continue

                shared = geom_i.boundary.intersection(geom_j.boundary)

                if shared.is_empty:
                    continue

                if shared.geom_type in ["LineString", "MultiLineString"]:
                    shared_segments.append(shared)
                elif shared.geom_type == "GeometryCollection":
                    line_parts = [
                        g for g in shared.geoms
                        if g.geom_type in ["LineString", "MultiLineString"] and not g.is_empty
                    ]
                    if line_parts:
                        shared_segments.extend(line_parts)

        if not shared_segments:
            continue

        merged = unary_union(shared_segments)

        # Only merge if this is actually a multi-part line geometry
        if merged.geom_type in ["MultiLineString", "GeometryCollection"]:
            try:
                merged = linemerge(merged)
            except Exception:
                pass

        if merged.is_empty:
            continue

        records.append({
            "country_name": country,
            "geometry": merged
        })

    if not records:
        return gpd.GeoDataFrame(
            columns=["country_name", "geometry"],
            geometry="geometry",
            crs=adm1_gdf.crs
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs=adm1_gdf.crs)


def get_projection(mode: str):
    """Return the requested projection plus plotting settings."""
    data_crs = ccrs.PlateCarree()

    if mode == "robinson_europe":
        proj = ccrs.Robinson(central_longitude=8)
        config = {
            "set_global": True,
            "extent": None,
            "figsize": (19, 9),
            "outfile_base": "travel_map_robinson_europe",
            "text_y": (0.41, 0.345, 0.225, 0.16),
            "use_tight_bbox": True,
            "x_text": -0.02,
        }

    elif mode == "robinson_bering":
        proj = ccrs.Robinson(central_longitude=150)
        config = {
            "set_global": True,
            "extent": None,
            "figsize": (19, 9),
            "outfile_base": "travel_map_robinson_bering",
            "text_y": (0.41, 0.345, 0.225, 0.16),
            "use_tight_bbox": True,
            "x_text": -0.02,
        }

    elif mode == "mercator":
        proj = ccrs.Mercator(
            central_longitude=8,
            min_latitude=-84,
            max_latitude=84
        )
        config = {
            "set_global": True,
            "extent": [-100, 100, -100, 100],
            "figsize": (9, 12),
            "outfile_base": "travel_map_mercator",
            "text_y": (0.41, 0.345, 0.225, 0.16),
            "use_tight_bbox": False,
            "x_text": 0.01,
        }

    else:
        raise ValueError(f"Unknown projection mode: {mode}")

    return proj, data_crs, config


# -----------------------------
# 3) Load base world layers
# -----------------------------
countries = load_ne_countries()
coastline = load_ne_coastline()

country_name_col = "NAME_EN" if "NAME_EN" in countries.columns else "ADMIN"

if "ADM0_A3" in countries.columns:
    iso3_col = "ADM0_A3"
elif "ISO_A3" in countries.columns:
    iso3_col = "ISO_A3"
else:
    iso3_col = None


def classify_country(country: str) -> str:
    """Assign one of three categories to each country."""
    if country in lived_in:
        return "lived_in"
    if country in visited:
        return "visited"
    return "not_visited"


countries["status"] = countries[country_name_col].apply(classify_country)

# -----------------------------
# 4) Load ADM1 only for relevant countries
# -----------------------------
adm1_frames = []

if iso3_col is None:
    raise RuntimeError("No ISO3 column found in the countries dataset.")

countries_with_subdivisions = visited | lived_in

selected_countries = (
    countries[countries[country_name_col].isin(countries_with_subdivisions)]
    [[country_name_col, iso3_col]]
    .dropna()
    .drop_duplicates()
)

for _, row in selected_countries.iterrows():
    country = row[country_name_col]
    iso3 = row[iso3_col]

    if not isinstance(iso3, str):
        continue

    iso3 = iso3.strip()

    if len(iso3) != 3 or iso3 == "-99":
        if country in iso3_map:
            iso3 = iso3_map[country]
        else:
            continue

    try:
        adm1 = load_gb_adm1(iso3)
        name_col = detect_name_column(adm1)
        adm1 = add_country_name_column(adm1, country, name_col)
        adm1_frames.append(adm1[["country_name", "state_name", "geometry"]].copy())
        print(f"Loaded ADM1 for {country} ({iso3})")
    except Exception:
        print(f"Skipped ADM1 for {country} ({iso3})")
        continue

if len(adm1_frames) > 0:
    adm1_all = pd.concat(adm1_frames, ignore_index=True)
    adm1_all = gpd.GeoDataFrame(adm1_all, geometry="geometry", crs="EPSG:4326")

    if adm1_all.crs != countries.crs:
        adm1_all = adm1_all.to_crs(countries.crs)

    visited_state_set = set(visited_states)
    adm1_all["is_visited_state"] = adm1_all.apply(
        lambda r: (r["country_name"], r["state_name"]) in visited_state_set,
        axis=1,
    )

    # Build unique internal borders from original ADM1 polygons first
    state_lines = build_unique_internal_boundaries(adm1_all)

    # Only simplify the resulting linework lightly afterwards
    state_lines = simplify_line_geometries(state_lines, 0.02)

    # Keep highlighted visited states unsimplified so they match border geometry better
    state_highlights = adm1_all[adm1_all["is_visited_state"]].copy()
else:
    adm1_all = gpd.GeoDataFrame(
        columns=["country_name", "state_name", "geometry"],
        geometry="geometry",
        crs="EPSG:4326"
    )
    state_lines = gpd.GeoDataFrame(
        columns=["country_name", "geometry"],
        geometry="geometry",
        crs="EPSG:4326"
    )
    state_highlights = adm1_all.copy()

# -----------------------------
# 5) Styling
# -----------------------------
colors = {
    "not_visited": "#edf1f7",
    "visited": "#a9d0ec",
    "lived_in": "#97c6e8",
    "visited_state": "#2f78b7",

    "country_border": "#2f78b7",
    "state_border_default": "#aeb8c8",
    "state_border_visited": "#dfe7f4",

    "lived_outline": "#000000",
    "coastline": "#d2d8e3",

    "halo_country": "#eef3fb",
}

country_line_width = 0.42
internal_line_width = 0.30
gray_internal_line_width = 0.22
black_line_width = 0.52
country_halo_extra = 0.22

mpl.rcParams["lines.solid_joinstyle"] = "round"
mpl.rcParams["lines.solid_capstyle"] = "round"

# -----------------------------
# 6) Plot
# -----------------------------
proj, data_crs, proj_cfg = get_projection(projection_mode)

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Helvetica",
    "Arial",
    "Liberation Sans",
    "DejaVu Sans",
]
plt.rcParams["svg.fonttype"] = "none"

fig = plt.figure(figsize=proj_cfg["figsize"], facecolor="white")
ax = plt.axes(projection=proj)
ax.set_facecolor("white")

if proj_cfg["set_global"]:
    ax.set_global()
else:
    ax.set_extent(proj_cfg["extent"], crs=data_crs)

if projection_mode == "mercator":
    ax.set_aspect(0.9)

for status in ["not_visited", "visited", "lived_in"]:
    subset = countries[countries["status"] == status]
    if not subset.empty:
        subset.plot(
            ax=ax,
            transform=data_crs,
            color=colors[status],
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )

if not state_highlights.empty:
    state_highlights.plot(
        ax=ax,
        transform=data_crs,
        color=colors["visited_state"],
        edgecolor="none",
        linewidth=0,
        zorder=3,
    )

if not state_lines.empty:
    visited_or_lived_countries = visited | lived_in

    state_lines_default = state_lines[
        ~state_lines["country_name"].isin(visited_or_lived_countries)
    ]
    state_lines_visited = state_lines[
        state_lines["country_name"].isin(visited_or_lived_countries)
    ]

    if not state_lines_default.empty:
        state_lines_default.plot(
            ax=ax,
            transform=data_crs,
            color=colors["state_border_default"],
            linewidth=gray_internal_line_width,
            alpha=0.88,
            zorder=4,
        )

    if not state_lines_visited.empty:
        state_lines_visited.plot(
            ax=ax,
            transform=data_crs,
            color=colors["state_border_visited"],
            linewidth=internal_line_width,
            alpha=0.96,
            zorder=4,
        )

coastline.plot(
    ax=ax,
    transform=data_crs,
    color=colors["halo_country"],
    linewidth=country_line_width + country_halo_extra,
    alpha=0.35,
    zorder=4.6,
)
coastline.plot(
    ax=ax,
    transform=data_crs,
    color=colors["coastline"],
    linewidth=country_line_width,
    alpha=0.82,
    zorder=5,
)

countries.boundary.plot(
    ax=ax,
    transform=data_crs,
    color=colors["halo_country"],
    linewidth=country_line_width + country_halo_extra,
    alpha=0.30,
    zorder=5.6,
)
countries.boundary.plot(
    ax=ax,
    transform=data_crs,
    color=colors["country_border"],
    linewidth=country_line_width,
    zorder=6,
)

lived_subset = countries[countries["status"] == "lived_in"]
if not lived_subset.empty:
    lived_subset.boundary.plot(
        ax=ax,
        transform=data_crs,
        color="#ffffff",
        linewidth=black_line_width + 0.18,
        alpha=0.25,
        zorder=6.6,
    )
    lived_subset.boundary.plot(
        ax=ax,
        transform=data_crs,
        color=colors["lived_outline"],
        linewidth=black_line_width,
        zorder=7,
    )

# -----------------------------
# 7) Statistics block
# -----------------------------
visited_count = len(visited)
lived_count = len(lived_in)

x_text = proj_cfg["x_text"]
y1, y2, y3, y4 = proj_cfg["text_y"]

ax.text(
    x_text, y1, f"{visited_count}",
    transform=ax.transAxes,
    fontsize=64,
    fontweight="bold",
    color=colors["visited_state"],
    ha="left",
    va="center",
    zorder=20,
    clip_on=False,
)

ax.text(
    x_text, y2, "countries visited",
    transform=ax.transAxes,
    fontsize=18,
    color=colors["visited_state"],
    ha="left",
    va="center",
    zorder=20,
    clip_on=False,
)

ax.text(
    x_text, y3, f"{lived_count}",
    transform=ax.transAxes,
    fontsize=64,
    fontweight="bold",
    color=colors["lived_outline"],
    ha="left",
    va="center",
    zorder=20,
    clip_on=False,
)

ax.text(
    x_text, y4, "countries lived in",
    transform=ax.transAxes,
    fontsize=18,
    color=colors["lived_outline"],
    ha="left",
    va="center",
    zorder=20,
    clip_on=False,
)

# -----------------------------
# 8) Export
# -----------------------------
ax.set_axis_off()
plt.subplots_adjust(left=0.03, right=0.99, top=0.98, bottom=0.03)

if proj_cfg["use_tight_bbox"]:
    plt.savefig(
        f"{proj_cfg['outfile_base']}.png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white"
    )
    plt.savefig(
        f"{proj_cfg['outfile_base']}.svg",
        bbox_inches="tight",
        facecolor="white"
    )
    plt.savefig(
        f"{proj_cfg['outfile_base']}.pdf",
        bbox_inches="tight",
        facecolor="white"
    )
else:
    plt.savefig(
        f"{proj_cfg['outfile_base']}.png",
        dpi=300,
        facecolor="white"
    )
    plt.savefig(
        f"{proj_cfg['outfile_base']}.svg",
        facecolor="white"
    )
    plt.savefig(
        f"{proj_cfg['outfile_base']}.pdf",
        facecolor="white"
    )

plt.show()

# -----------------------------
# 9) Debug output
# -----------------------------
print(f"\nProjection mode: {projection_mode}")
print("\nCountries with subdivisions shown:")
for c in sorted(countries_with_subdivisions):
    print("-", c)

print("\nVisited states found:")
for _, row in state_highlights.iterrows():
    print("-", row["country_name"], ":", row["state_name"])
