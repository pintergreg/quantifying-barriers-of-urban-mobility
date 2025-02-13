"""
Calculate sysmmetric area difference between communities and barriers.

:param output: output directory (default `../output`)
:param target: output 'version', subdirectory of the output folder
:param resolution-start: first resolution value to involve, 1.0 by default
:param resolution-stop: upper limit of the loop, *excluded*, 10.5 by default
:param resolution-step: step for the resolution loop, 0.5 by default
:param run-start: lower limit of the runs, 0 by default
- run also serves as the seed for the community detection
:param run-stop: excluded upper limit of the run loop, 10 by default
:param data: directory where the input data files can be found\
    (default `../data`)
"""
from collections import namedtuple
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely import symmetric_difference
from shapely.geometry import Polygon, MultiPolygon

Options = namedtuple(
    "Options",
    [
        "input",
        "output",
        "target",
        "run_start",
        "run_stop",
        "res_start",
        "res_stop",
        "res_step",
        "community_dir"
    ],
)


def select_largest(mp: MultiPolygon) -> Polygon:
    """
    Select larges polygon from a MultiPolygon.

    :param: c: polygon collection

    :return: the largest polygon

    ###### Example
    >>> from shapely.geometry import Point
    >>> p1 = Polygon([Point(1, 1), Point(2, 1), Point(2, 2), Point(1, 2)])
    >>> p1.area
    1.0
    >>> p2 = Polygon([Point(1, 1), Point(3, 1), Point(3, 3), Point(1, 3)])
    >>> p2.area
    4.0
    >>> m = MultiPolygon([p1, p2])
    >>> select_largest(m)
    <POLYGON ((1 1, 3 1, 3 3, 1 3, 1 1))>
    >>> select_largest(m).area
    4.0
    """
    return Polygon(max(mp.geoms, key=lambda x: x.area).exterior.coords)


def compare_communities_to_barriers(
    barriers: gpd.GeoDataFrame,
    options: Options,
    id_column: str = "id",
    columns: list[str] = [
        "run",
        "resolution",
        "community_id",
        "barrier_id",
        "area_symmdiff",
    ],
) -> pd.DataFrame:
    """
    Compare communities to barrier polygons.

    :param barriers: barrier polygons in GeoPandas GeoDataFrame format
    :param options: options set by the CLI, including parameter for the loops
    - run start, stop
    - resolution start, stop, step
    - input, output folder and target
    :param id_column: ID column of the barrier DataFrame
    - default `id` due to the barrier polygons, but OSM data uses different ID\
      for the administrative barriers
    :param columns: column names for the returned DataFrame

    :return: DataFrame with the symmetric area difference between the\
        communities and the barriers per run and resolution
    """
    result = []
    for run in range(options.run_start, options.run_stop):
        for res in np.arange(
            options.res_start, options.res_stop, options.res_step
        ):
            communities = gpd.read_file(
                f"{options.input}/"
                f"{options.target}/{options.community_dir}/louvain/{run}/"
                f"louvain_r{res}_merged.geojson"
            )
            for c in communities.itertuples():
                overlapping = barriers[
                    barriers["geometry"].intersects(c.geometry)
                ].copy()
                for poly in overlapping.itertuples():
                    diff = symmetric_difference(poly.geometry, c.geometry).area
                    result.append(
                        [run, res, c.id, getattr(poly, id_column), diff]
                    )
    return pd.DataFrame.from_records(result, columns=columns)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        type=str,
        required=False,
        default="",
        help="Neighborhoods and Boundaries of Urban Mobility",
    )
    parser.add_argument(
        "--community-dir",
        type=str,
        required=False,
        default="place_communities",
        help="community subfolder",
    )
    parser.add_argument(
        "--resolution-start", type=float, required=False, default=1.0
    )
    parser.add_argument(
        "--resolution-stop",
        type=float,
        required=False,
        default=10.5,
        help="excluded",
    )
    parser.add_argument(
        "--resolution-step", type=float, required=False, default=0.5
    )
    parser.add_argument("--run-start", type=int, required=False, default=0)
    parser.add_argument(
        "--run-stop", type=int, required=False, default=10, help="excluded"
    )
    parser.add_argument(
        "--data",
        type=str,
        required=False,
        default="data",
        help="data directory",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=False,
        default="output",
        help="input directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="output/symmetric_area_difference",
        help="output directory",
    )
    opts = parser.parse_args()

    options = Options(
        input=opts.input,
        output=opts.output,
        target=opts.target,
        run_start=opts.run_start,
        run_stop=opts.run_stop,
        res_start=opts.resolution_start,
        res_stop=opts.resolution_stop,
        res_step=opts.resolution_step,
        community_dir=opts.community_dir,
    )

    barriers_primary = gpd.read_file(f"{opts.data}/barriers_mp.geojson")
    barriers_primary.to_crs(23700, inplace=True)

    barriers_secondary = gpd.read_file(f"{opts.data}/barriers_mps.geojson")
    barriers_secondary.to_crs(23700, inplace=True)

    districts = gpd.read_file(f"{opts.data}/budapest_districts.geojson")
    districts.to_crs(23700, inplace=True)

    neighborhoods = gpd.read_file(f"{opts.data}/admin10.geojson")
    neighborhoods.to_crs(23700, inplace=True)

    railways = gpd.read_file(f"{opts.data}/barriers_railways.geojson")
    railways.to_crs(23700, inplace=True)

    river = gpd.read_file(
        f"{opts.data}/barriers_river.geojson",
        engine="pyogrio"
    )
    river.to_crs(23700, inplace=True)

    Path(opts.output).mkdir(parents=True, exist_ok=True)

    # # runs 3m
    # sad_p = compare_communities_to_barriers(barriers_primary, options)
    # sad_p.to_csv(
    #     f"{opts.output}/communities_vs_primary_area_symmdiff.csv", index=False
    # )

    # # runs 4m
    # sad_s = compare_communities_to_barriers(barriers_secondary, options)
    # sad_s.to_csv(
    #     f"{opts.output}/communities_vs_secondary_area_symmdiff.csv",
    #     index=False,
    # )

    # # runs 3m
    # sad_d = compare_communities_to_barriers(
    #     districts, options, id_column="did"
    # )
    # sad_d.to_csv(
    #     f"{opts.output}/communities_vs_districts_area_symmdiff.csv",
    #     index=False,
    # )

    # # runs 4m
    # sad_n = compare_communities_to_barriers(
    #     neighborhoods, options, id_column="name"
    # )
    # sad_n.to_csv(
    #     f"{opts.output}/communities_vs_neighborhoods_area_symmdiff.csv",
    #     index=False,
    # )

    # # runs ?m
    # sad_rw = compare_communities_to_barriers(
    #     railways, options, id_column="id"
    # )
    # sad_rw.to_csv(
    #     f"{opts.output}/communities_vs_railways_area_symmdiff.csv",
    #     index=False,
    # )

    # runs ?m
    sad_r = compare_communities_to_barriers(
        river, options, id_column="id"
    )
    sad_r.to_csv(
        f"{opts.output}/communities_vs_river_area_symmdiff.csv",
        index=False,
    )
