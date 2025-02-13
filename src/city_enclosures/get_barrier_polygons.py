"""Get barrier polygons from OSM."""

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.ops import polygonize

ox.settings.use_cache = True
ox.settings.log_console = False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--area",
        type=str,
        required=True,
        help="observation area defined by GeoJSON polygon",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="output polygons in GeoJSON format",
    )
    parser.add_argument(
        "-s",
        "--street",
        type=str,
        required=False,
        nargs="*",
        default=["motorway", "trunk", "primary", "secondary"],
        help=(
            "OSM highway types: motorway trunk primary "
            "secondary tertiary unclassified residential"
        ),
    )
    parser.add_argument(
        "-r",
        "--railway",
        type=str,
        required=False,
        nargs="*",
        default=["rail", "light_rail"],
        help="OSM railway types",
    )
    parser.add_argument("--no-railway", action="store_true")
    parser.add_argument(
        "-R",
        "--excluding-railway-service",
        type=str,
        required=False,
        nargs="*",
        default=["spur", "yard", "siding"],
        help="without OSM railway service types",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        required=False,
        default=0.1,
        help="area threshold in square kilometer",
    )
    parser.add_argument(
        "-c",
        "--threshold-crs",
        type=int,
        required=False,
        default=23700,
        help="CRS in which the threshold is defined",
    )
    parser.add_argument(
        "-b",
        "--buffer",
        type=float,
        required=False,
        default=50,
        help="buffer used to dissolve rifts",
    )
    parser.add_argument(
        "-u",
        "--buffer-crs",
        type=int,
        required=False,
        default=23700,
        help="CRS in which the buffer is defined",
    )
    parser.add_argument(
        "--river",
        type=str,
        required=False,
        help="GeoJSON containing a single river polygon",
    )
    parser.add_argument(
        "--river-shrink",
        type=float,
        required=False,
        default=50,
        help="buffer used to shrink river for enclosure difference",
    )
    parser.add_argument(
        "--river-shrink-crs",
        type=int,
        required=False,
        default=23700,
        help="CRS in which the river shrink buffer is defined",
    )
    opts = parser.parse_args()

    area = gpd.read_file(opts.area)

    barriers_elements = [area.boundary]
    if opts.street:
        road_filter = f'["highway"~"{"|".join(map(lambda x: f"^{x}.*", opts.street))}"]'
        g = ox.graph_from_polygon(
            area.convex_hull.geometry[0], custom_filter=road_filter, simplify=False
        )
        roads = ox.graph_to_gdfs(g, nodes=False)
        barriers_elements.append(roads.geometry)

    if not opts.no_railway:
        rail_filter = f'["railway"~"({"|".join(opts.railway)})"]["service"!~"{"|".join(opts.excluding_railway_service)}"]'
        g_rw = ox.graph_from_polygon(
            area.convex_hull.geometry[0],
            custom_filter=rail_filter,
            simplify=False,
            retain_all=True,
        )
        railways = ox.graph_to_gdfs(g_rw, nodes=False)
        barriers_elements.append(railways.geometry)

    barriers = pd.concat(barriers_elements)

    if opts.river:
        river = gpd.read_file(opts.river).set_crs(crs=4326)
        river = gpd.clip(river, area)
        shrank_river = (
            river.to_crs(opts.river_shrink_crs).buffer(-opts.river_shrink).to_crs(4326)
        )

        barriers = pd.concat([barriers, gpd.GeoSeries(river.boundary)])

    unioned = barriers.union_all()

    polygons = polygonize(unioned)
    enclosures = gpd.array.from_shapely(list(polygons), crs=4326)

    enclosures_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(enclosures), crs=4326)

    if opts.river:
        enclosures_gdf = enclosures_gdf[
            ~enclosures_gdf["geometry"].intersects(shrank_river.union_all())
        ]

    enclosures_gdf = gpd.clip(enclosures_gdf, area)
    enclosures_gdf = enclosures_gdf[
        (enclosures_gdf.geometry.type == "Polygon")
        | (enclosures_gdf.geometry.type == "MultiPolygon")
    ].copy()

    # not guaranteed to be deterministic across executions
    enclosures_gdf["id"] = range(1, len(enclosures_gdf) + 1)
    if opts.buffer > 0:
        enclosures_gdf["geometry"] = (
            enclosures_gdf.to_crs(opts.buffer_crs)
            .buffer(opts.buffer)
            .buffer(-opts.buffer)
            .to_crs(4326)
        )

    enclosures_gdf["area"] = (
        enclosures_gdf.to_crs(opts.threshold_crs).geometry.area / 1e6
    )

    if opts.threshold > 0:
        enclosures_gdf = enclosures_gdf[enclosures_gdf["area"] >= opts.threshold].copy()

    enclosures_gdf.to_file(opts.output + ".geojson", driver="GeoJSON")
    enclosures_gdf.to_csv(opts.output + ".csv", index=False)
