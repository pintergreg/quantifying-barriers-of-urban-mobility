"""
Script to calculate barrier crossings.

:param network [str]: network ID, used to load the trip files for the given\
     network from the ``output/trips`` folder withe the filename of\
     ``network_{network}_beeline.pickle``, where network can be *observed*,\
     *seed4_2*, *seed5_7*, etc.
:param barrier-types: one of the following
    - *road1*: primary roads (OSM primary + motorway)
    - *road2*: secondary roads (OSM primary + motorway + secondary)
    - *railways*: railways
    - *river*: rivers (in the paper only river Danube with its fork)
    - *districts*: districts, OSM admin level 9
    - *neighborhhods*: OSM admin level 10
:param multithreading: if set, calculation for all the barriers types are\
    started on separate threads
:param output [str]: output directory (default ``output/barrier_crossing``)
"""
import pathlib
import pandas as pd
from os.path import exists
from typing import Literal
from multiprocessing import Pool
import geopandas as gpd
from itertools import repeat


def calculate_crossings_dataframe(
    network: str,
    barrier_type: Literal["road1", "road2", "railways", "river", "districts",
                          "neighborhoods"],
    barrier_types: dict, trips: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Calculate barrier crossings.

    The algorithm considers trips in straight line, the intersections of the\
    trip lines are counted by the specified barrier.

    The result is written to a gzipped CSV file.

    :param network: network ID, e.g., observed or seed4_2
    :param barrier_type: one of the following
    - *road1*: primary roads (OSM primary + motorway)
    - *road2*: secondary roads (OSM primary + motorway + secondary)
    - *railways*: railways
    - *river*: rivers (in the paper only river Danube with its fork)
    - *districts*: districts, OSM admin level 9
    - *neighborhhods*: OSM admin level 10
    :param barrier_types: a dictionary containing infor to handle barriers
    :param trips: beeline trips as LineStrings in GeoPandas GeoDataFrame format

    :return: DataFrame with three columns: *source*, *target*, *count*

    ###### Examples
    >>> from shapely.geometry import Point, LineString
    >>> r = LineString([Point(3, 1), Point(3, 18)])
    >>> river = gpd.GeoDataFrame({'name': 'Dummy', 'geometry': [r]})
    >>> t1 = LineString([Point(2, 7), Point(9, 11)])
    >>> t2 = LineString([Point(4, 9), Point(8, 15)])
    >>> t3 = LineString([Point(0, 5), Point(5, 6)])
    >>> t4 = LineString([Point(2, 7), Point(5, 6)])
    >>> trips = gpd.GeoDataFrame({\
        'source': [1, 2, 3, 1, 1],\
        'target': [4, 5, 6, 6, 6],\
        'geometry': [t1, t2, t3, t4, t4]})
    >>> bt = {'river': {'data': river, 'column': 'name'}}
    >>> calculate_crossings_dataframe('dummy', 'river', bt, trips)
    ... # doctest: +NORMALIZE_WHITESPACE
           source  target  count
    0       1       4      1
    1       1       6      1
    2       3       6      1
    """
    column = barrier_types[barrier_type]["column"]
    bc = trips.sjoin(barrier_types[barrier_type]["data"])\
              .groupby(["source", "target"])\
              .agg(count=pd.NamedAgg(column, "nunique"))
    return bc.reset_index()


def calculate_crossings(
    network: str,
    barrier_type: Literal["road1", "road2", "railways", "river", "districts",
                          "neighborhoods"],
    barrier_types: dict, trips: gpd.GeoDataFrame, output: str
) -> None:
    """
    Calculate barrier crossings and save the result.

    The algorithm considers trips in straight line, the intersections of the\
    trip lines are counted by the specified barrier.

    The result is written to a gzipped CSV file.

    :param network: network ID, e.g., observed or seed4_2
    :param barrier_type: one of the following
    - *road1*: primary roads (OSM primary + motorway)
    - *road2*: secondary roads (OSM primary + motorway + secondary)
    - *railways*: railways
    - *river*: rivers (in the paper only river Danube with its fork)
    - *districts*: districts, OSM admin level 9
    - *neighborhhods*: OSM admin level 10
    :param barrier_types: a dictionary containing infor to handle barriers
    :param trips: beeline trips as LineStrings in GeoPandas GeoDataFrame format
    :param output: output directory
    """
    path = f"{output}/{network}"
    filename = barrier_type
    if not exists(f"{path}/{filename}"):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    calculate_crossings_dataframe(
        network,
        barrier_type,
        barrier_types,
        trips
    ).to_csv(f"{path}/{barrier_type}.csv.gz", index=False)


def read_barrier_data(
    roads_path: str,
    admin_path: str,
    river_path: str,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame,
           gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Read barrier data.

    :param path: path of the barrier GeoJSONs.

    ###### Returns
    - **road1**: OSM motorways and primary roads
    - **road2**: OSM secondary and primary roads
    - **railw**: railways
    - **river**: river
    - **distr**: districts
    - **adm10**: neightborhoods

    .. warning::
        Code assumes as inputs: name_unioned_roads_mp.geojson (road1),\
        name_unioned_roads_s.geojson (road2),\
        railways.geojson and duna.geojson.
    """
    road1 = gpd.read_file(f"{roads_path}/name_unioned_roads_mp.geojson",
                          engine="pyogrio")
    road2 = gpd.read_file(f"{roads_path}/name_unioned_roads_s.geojson",
                          engine="pyogrio")
    railw = gpd.read_file(f"{roads_path}/railways.geojson", engine="pyogrio")
    river = gpd.read_file(river_path, engine="pyogrio")
    # river.set_crs(23700, inplace=True)
    # river.to_crs(4326, inplace=True)
    distr = gpd.read_file(f"{admin_path}/budapest_districts.geojson",
                          engine="pyogrio")
    adm10 = gpd.read_file(f"{admin_path}/admin10.geojson",
                          engine="pyogrio")

    return road1, road2, railw, river, distr, adm10


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=str, required=True)
    parser.add_argument(
        "--trip-type", type=str, required=False, default="beeline")
    parser.add_argument(
        "--barrier-types", type=str, required=False, nargs="+",
        default=["road1", "road2", "railways", "river", "districts",
                 "neighborhoods"],
        help=("valid values are: road1, road2, railways, river, districts, "
              "neighborhoods"))
    parser.add_argument("--multithreading", action="store_true")
    parser.add_argument("--pool", type=int, required=False)
    parser.add_argument("--admin-data", type=str, required=False,
                        default="data",
                        help="directory where administrative barriers are")
    parser.add_argument("--roads", type=str, required=False,
                        default="output/roads",
                        help="directory where road and railway data is")
    parser.add_argument(
        "--river", type=str, required=False,
        default="data/duna_linestring.geojson",
        help="GeoJSON containing the river as a LineString in EPSG:4326")
    parser.add_argument("--output", type=str, required=False,
                        default="output/barrier_crossing",
                        help="output directory")
    opts = parser.parse_args()

    road1, road2, railw, river, distr, \
        adm10 = read_barrier_data(opts.roads, opts.admin_data, opts.river)
    barrier_types = {
        "road1": {"data": road1, "column": "name"},
        "road2": {"data": road2, "column": "name"},
        "railways": {"data": railw, "column": "ref"},
        "river": {"data": river, "column": "index_right"},
        "districts": {"data": distr, "column": "did"},
        "neighborhoods": {"data": adm10, "column": "id"}
    }

    trips = pd.read_pickle(
        f"output/trips/network_{opts.network}_{opts.trip_type}.pickle.gz"
    )
    trips = gpd.GeoDataFrame(trips, crs=4326)

    pool = len(opts.barrier_types)
    if opts.pool:
        pool = opts.pool

    if opts.multithreading:
        with Pool(pool) as p:
            p.starmap(
                calculate_crossings,
                zip(
                    repeat(opts.network),
                    opts.barrier_types,
                    repeat(barrier_types),
                    repeat(trips),
                    repeat(opts.output)
                    )
                )
    else:
        for i in opts.barrier_types:
            calculate_crossings(opts.network, i, barrier_types, trips,
                                output=opts.output)
