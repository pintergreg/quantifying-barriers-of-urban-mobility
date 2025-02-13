import pandas as pd
import geopandas as gpd
import pathlib
from shapely.geometry import Polygon, MultiPolygon


def get_the_largest_set_of_community(
    gdf: gpd.GeoDataFrame, community: gpd.GeoSeries
) -> Polygon:
    extended = gdf.copy()
    extended = extended.query("community==@community")
    dissolved = extended.dissolve()
    if isinstance(dissolved.geometry[0], Polygon):
        return dissolved.geometry[0]
    largest = max(list(dissolved.geometry[0].geoms), key=lambda x: x.area)
    return Polygon(largest.exterior.coords)


def get_the_largest_community_polygon(gdf: gpd.GeoDataFrame) -> Polygon:
    g = gdf.to_crs(23700).dissolve().geometry[0]
    if isinstance(g, Polygon):
        return g
    elif isinstance(g, MultiPolygon):
        return Polygon(max(g.geoms, key=lambda x: x.area).exterior.coords)


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--resolution", type=float, required=True,
                           help="louvain resolution parameter")
    argparser.add_argument("--output", type=str, required=False,
                           default="../output", help="output")
    argparser.add_argument("--communities", type=str, required=False,
                           default="place_communities",
                           help="communities directory")
    argparser.add_argument("--target", type=str, required=False,
                           default="", help="target output")
    argparser.add_argument("--start-date", type=str, required=False,
                           default="2019-09-01", help="start date")
    argparser.add_argument("--end-date", type=str, required=False,
                           default="2020-02-29", help="end date")
    argparser.add_argument("--run-start", type=int, required=False,
                           default=0)
    argparser.add_argument("--run-stop", type=int, required=False,
                           default=10, help="excluded")
    opts = argparser.parse_args()

    for run in range(opts.run_start, opts.run_stop):
        pathlib.Path(f"{opts.output}/{opts.target}/"
                     f"{opts.communities}/louvain/{run}/")\
            .mkdir(parents=True, exist_ok=True)

        hb = gpd.read_file(f"{opts.output}/{opts.target}/"
                           f"{opts.communities}/louvain/{run}/"
                           f"{opts.start_date}_{opts.end_date}"
                           f"_resolution{opts.resolution}.geojson")

        c = []
        for i in hb["community"].dropna().unique():
            area = get_the_largest_set_of_community(hb, i)
            p = get_the_largest_community_polygon(
                hb[hb["geometry"].within(area)])
            c.append([i, p])

        communities = gpd.GeoDataFrame(
            pd.DataFrame.from_records(c, columns=["id", "geometry"]),
            geometry="geometry", crs=23700)
        communities.to_file(f"{opts.output}/"
                            f"{opts.target}/{opts.communities}/louvain/{run}/"
                            f"louvain_r{opts.resolution}_merged.geojson",
                            driver="GeoJSON")
