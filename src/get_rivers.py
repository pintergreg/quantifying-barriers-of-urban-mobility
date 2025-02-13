"""
Downloads rivers from OpenStreetMap within an area.

Also merges the multiple polygons of the river by name \
to produce a single polygon, and extracts the waterway as a LineString.

:param area: GeoJSON with a polygon to define the area in which the rivers are\
    to download.
:param river: array, with river names
:param output: output folder
:param filename: name of the output GeoJSON file without extension

.. note::
    By default downloads river Danube within Budapest adminstrative boundaries.
"""
import geopandas as gpd
import osmnx as ox
from osmnx.geometries import geometries_from_polygon

ox.settings.use_cache = True
ox.settings.log_console = False


def union_by_name(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Apply unary union to the geometries groupped by the name attribute.

    Used to create a single polygon from the segmens of a river downloaded\
        from OpenStreetMap.

    :param gdf: input data from OSM by OSMnX

    :return: GeoDataFrame with the unioned geometries.\
        There might be more records as there can be multiple rivers\
        in a given area.
    >>> from shapely import Point, LineString
    >>> l1 = LineString([Point(1, 1), Point(7, 2), Point(8, 5), Point(9, 0)])
    >>> l2 = LineString([Point(9, 0), Point(8, -4), Point(10, -6)])
    >>> l3 = LineString([Point(4, 2), Point(1, 7)])
    >>> gdf = gpd.GeoDataFrame({"name": ["flod", "flod", "joki"],\
         "geometry": [l1, l2, l3]})
    >>> u = union_by_name(gdf)
    >>> u[u["name"] == "flod"].at[0, "geometry"].length == l1.length+l2.length
    True
    """
    tmp = gdf[gdf["geometry"].type == "LineString"]
    result =  tmp.groupby("name").apply(lambda x: x.unary_union).reset_index()
    result.columns = ["name", "geometry"]
    return gpd.GeoDataFrame(result)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--area",
        type=str,
        required=False,
        default="data/budapest.geojson",
        help=(
            "observation area defined by a polygon in GeoJSON format "
            "and EPSG:4326 projection"
            ),
    )
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="output",
        help="output folder",
    )
    parser.add_argument(
        "--filename",
        type=str,
        required=False,
        default="duna",
        help="name of the output GeoJSON file",
    )
    parser.add_argument(
        "-r",
        "--river",
        type=str,
        required=False,
        nargs="+",
        default=["Duna", "Ráckevei-Duna", "Ráckevei (Soroksári)-Duna"],
        help=(
            "name of the river(s), "
            "NB: branches of the river may be provided as well"
            ),
    )
    opts = parser.parse_args()
    Path(opts.output).mkdir(parents=True, exist_ok=True)


    area = gpd.read_file(opts.area)

    gfp = geometries_from_polygon(
        area.convex_hull.geometry[0],
        tags={"name": opts.river, "water": "river"}
    )
    gfp.reset_index(inplace=True)

    duna = gfp.copy()
    duna["geometry"] = gfp.geometry.unary_union
    duna[["geometry", "name", "name:en"]]\
        .to_file(f"{opts.output}/{opts.filename}.geojson", driver="GeoJSON")

    duna_ls = union_by_name(gfp)
    duna_ls.to_file(f"{opts.output}/{opts.filename}_linestring.geojson")
