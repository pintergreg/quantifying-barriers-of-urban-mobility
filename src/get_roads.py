import geopandas as gpd
import osmnx as ox
from pyogrio.errors import DataSourceError
from fiona.errors import DriverError

ox.settings.use_cache = True
ox.settings.log_console = False


def filter_roads(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Filter roads downloaded from OSM.

    .. note::
        Motorways do not have name, the ID is in ref,\
        so if the highway is motorway the ref is copied.
        However, there are some parts with primary highway type that also part\
        of a motorway route, so ref is copied if name is NA, but ref is not.

    """
    exclude = ['footway', 'pedestrian', 'bus_stop', 'corridor', 'bridleway',
               'raceway', 'cycleway', 'path', 'steps', 'track', 'proposed',
               'platform']

    filtered = roads[~roads["highway"].isin(exclude)].copy()

    filtered["highway"] = filtered["highway"].str.replace("_link", "")

    # inspired by: https://stackoverflow.com/a/43002728/4737417
    filtered["name"] = filtered["ref"]\
        .where((filtered["highway"] == "motorway") | (filtered["name"].isna()),
               filtered["name"])

    return filtered


def save_roads_by_type(filtered_roads: gpd.GeoDataFrame, path: str) -> None:
    filtered_roads.query("highway.isin(['motorway'])")\
        .to_file(f"{path}/filtered_roads_m.geojson", driver="GeoJSON")
    filtered_roads.query("highway.isin(['primary'])")\
        .to_file(f"{path}/filtered_roads_p.geojson", driver="GeoJSON")
    filtered_roads.query("highway.isin(['secondary'])")\
        .to_file(f"{path}/filtered_roads_s.geojson", driver="GeoJSON")
    filtered_roads.query("highway.isin(['motorway', 'primary'])")\
        .to_file(f"{path}/filtered_roads_mp.geojson", driver="GeoJSON")


def union_by_road_name(
    gdf: gpd.GeoDataFrame,
    highway: list[str]
) -> gpd.GeoDataFrame:
    """
    Union roads by road name using unary union.

    :param gdf: GeoDataFrame with the roads downloaded from OSM.\
        Output of :py:func:`get_roads`.
    :param highway: OSM highway type

    :return: a GeoDataFrame with two columns (road name and the geometry).\
        The geometry can be a MultiLineString.
    """
    result = gdf[gdf["highway"].isin(highway)]\
        .groupby("name").apply(lambda x: x.unary_union).reset_index()
    result.columns = ["name", "geometry"]
    return gpd.GeoDataFrame(result)


def get_roads(area: gpd.GeoDataFrame, output: str) -> gpd.GeoDataFrame:
    """
    Download roads from OSM using OSMnX.

    If the roads are already downloaded it reads from the disk, otherwise\
        downloads the OSM highway type elements from OpenStreetMap and saves\
        the data to the output folder as a GeoJSON.

    :param area: the area within the roads will be downloaded
    :param output: output folder

    :return: roads as GeoDataFrame
    """
    try:
        roads = gpd.read_file(f"{output}/roads.geojson", engine="pyogrio")
    except (FileNotFoundError, DataSourceError):
        # runs about 5m
        g = ox.graph_from_polygon(
            area.geometry[0],
            custom_filter='["highway"]',
            simplify=False
        )
        roads = ox.graph_to_gdfs(g, nodes=False)
        roads.to_file(f"{output}/roads.geojson", driver="GeoJSON")
    return roads


def get_railways(area: gpd.GeoDataFrame, output: str) -> gpd.GeoDataFrame:
    """
    Download railways from OSM using OSMnX.

    If the railways are already downloaded it reads from the disk, otherwise\
        downloads railways from OSM with 'rail' or 'light_rail' types elements\
        and saves the data to the output folder as a GeoJSON.

    .. note::
        OSM raileays types such as *spur*, *yard* and *siding* are excluded.

    :param area: the area within the railways will be downloaded
    :param output: output folder

    :return: railways as GeoDataFrame
    """
    try:
        rgdf = gpd.read_file(f"{output}/railways.geojson")
    except (FileNotFoundError, DataSourceError, DriverError):
        opts_railway = ["rail", "light_rail"]
        opts_excluding_railway_service = ["spur", "yard", "siding"]
        rail_filter = f'["railway"~"({"|".join(opts_railway)})"]["service"!~"{"|".join(opts_excluding_railway_service)}"]'
        g_rw = ox.graph_from_polygon(
            area.convex_hull.geometry[0],
            custom_filter=rail_filter,
            simplify=False,
            retain_all=True
        )
        railways = ox.graph_to_gdfs(g_rw, nodes=False)

        rgdf = railways.groupby("ref")\
            .apply(lambda x: x.unary_union).reset_index()
        rgdf.columns = ["ref", "geometry"]
        rgdf = gpd.GeoDataFrame(rgdf, crs=4326)

        rgdf.to_file(f"{opts.output}/railways.geojson", driver="GeoJSON")

    return rgdf


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--area",
        type=str,
        required=False,
        default="../data/budapest.geojson",
        help="area of the roads to download")
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="../output/roads",
        help="output directory")
    opts = parser.parse_args()
    Path(opts.output).mkdir(parents=True, exist_ok=True)

    area = gpd.read_file(opts.area)

    roads = get_roads(area, opts.output)

    filtered = filter_roads(roads)
    if not Path(f"{opts.output}/filtered_roads.geojson").exists():
        filtered.to_file(f"{opts.output}/filtered_roads.geojson",
                         driver="GeoJSON")

    save_roads_by_type(filtered, opts.output)

    name_unioned_p = union_by_road_name(filtered, ["primary"])
    name_unioned_p.to_file(f"{opts.output}/name_unioned_roads_p.geojson",
                           driver="GeoJSON")

    name_unioned_mp = union_by_road_name(filtered, ["motorway", "primary"])
    name_unioned_mp.to_file(f"{opts.output}/name_unioned_roads_mp.geojson",
                            driver="GeoJSON")

    name_unioned_s = union_by_road_name(filtered, ["secondary"])
    name_unioned_s.to_file(f"{opts.output}/name_unioned_roads_s.geojson",
                           driver="GeoJSON")

    _ = get_railways(area, opts.output)
