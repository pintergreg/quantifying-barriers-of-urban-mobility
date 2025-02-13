"""
Generate beeline trips from a network.

.. note::
    Networks are identified by a string constructed from the seed value and a\
    number with a given seed, e.g., seed4_2, or called *observed*.

:param number-of-networks [int]: number of networks per seed (default 10)
:param seed [int]: *required*, as part of the network ID.
:param observed: if set, only the observed network is added to agenda.
:param network-dir [str]: directory where the network filed are stored.
:param output [str]: output directory (default ``output/trips``).
"""
from pathlib import Path
import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString


def convert_network_to_dataframe(G: nx.Graph) -> pd.DataFrame:
    """
    Convert network to dataframe.

    :param G: network in NetworkX Graph format.

    :return: network as edge list dtored in a Pandas Dataframe.

    ###### Example
    Consider the following undirected weighted graph, then convert it to a\
        dataframe. Weights are converted to multiplicated rows.

    ```mermaid
    flowchart LR
        1 ---|2| 2
        1 --- 3
    ```
    |   | source | target |
    | - | :----: | :----: |
    | 0 |    1   |    2   |
    | 1 |    1   |    2   |
    | 2 |    1   |    3   |

    >>> G = nx.Graph()
    >>> G.add_edges_from([(1, 2, {'weight': 2}), (1, 3, {'weight': 1})])
    >>> convert_network_to_dataframe(G)
    ... # doctest: +NORMALIZE_WHITESPACE
            source  target
        0       1       2
        1       1       2
        2       1       3

    """
    df = nx.to_pandas_edgelist(G)
    df["source"] = pd.to_numeric(df["source"])
    df["target"] = pd.to_numeric(df["target"])
    df = df.loc[df.index.repeat(df["weight"])]\
           .drop("weight", axis=1).reset_index(drop=True).copy()
    return df


def create_linestring(x: pd.Series) -> LineString:
    """
    Create a LineString from a DataFrame row containing two POINT geometries.

    :param x: a line of a Dataframe, containing two points.\
        One of them is the *source geometry* (centroid of the source block),\
        The seconds is the *target geometry* (centroid of the target block).

    :return: a LineString representing a straight line between the centroid of\
        the source block and the centroid of the target block.

    ###### Example
    >>> from shapely.geometry import Point
    >>> sg = [Point([0, 0]), Point([1, 7])]
    >>> tg = [Point([2, 2]), Point([4, 2])]
    >>> gdf = gpd.GeoDataFrame({'source_geometry': sg, 'target_geometry': tg})
    >>> create_linestring(gdf.iloc[0])
    <LINESTRING (0 0, 2 2)>
    >>> create_linestring(gdf.iloc[1])
    <LINESTRING (1 7, 4 2)>
    """
    return LineString([x["source_geometry"], x["target_geometry"]])


def prepare_house_blocks(filename: str) -> gpd.GeoDataFrame:
    """
    Load the prepare the blocks.

    This method expects that the blocks are downloaded OpenStreetMap with a\
    script that includes the area of the polygon and the CRS is EPSG:4326.

    The are column is dropped, and the polygon geometry is replaced with a\
    point which is the centroid of the polygon.
    To determine the centroid a meter-based projection is used. As the project\
    assumes Hungary, it is EPSG:23700.

    :param filename: filename for the shapefile with the blocks.

    :return: GeoPandas GeoDataFrame containing the blocks.
    """
    hb = gpd.read_file(filename, crs=4326)
    hb.drop("area", axis=1, inplace=True)
    hb.to_crs(23700, inplace=True)
    hb["geometry"] = hb.geometry.centroid
    hb.to_crs(4326, inplace=True)

    hb["lon"] = hb.geometry.x
    hb["lat"] = hb.geometry.y
    # hb_dict = hb[["id", "lon", "lat"]].to_dict(orient="records")
    hb.drop(["lon", "lat"], axis=1, inplace=True)

    return hb


def generate_beeline_trips(
    network: str, path: str, hb: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Load a network and generate beeline trips from it.

    :param network: network ID.
    :param path: directory where the network edgelist is present with the\
        given network ID.
    :param hb: GeoPandas GeoDataFrame containing the blocks.

    :return: Pandas DataFrame with the beeline trips.
    """
    nw = nx.read_edgelist(f"{path}/{network}.edgelist.gz")

    return generate_beeline_trips_from_network(network, nw, hb)


def generate_beeline_trips_from_network(
    network: str, nw: nx.Graph, hb: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Generate beeline trips from a network.

    :param network: network ID. TODO
    :param nw: the network in NetworkX Graph format
    :param hb: GeoPandas GeoDataFrame containing the blocks.

    :return: Pandas DataFrame with the beeline trips.
    """
    df = convert_network_to_dataframe(nw)

    hb.columns = ["source", "source_geometry"]
    df = df.merge(hb, on="source")
    hb.columns = ["target", "target_geometry"]
    df = df.merge(hb, on="target")
    df["geometry"] = df.apply(create_linestring, axis=1)
    df.drop(["source_geometry", "target_geometry"], axis=1, inplace=True)
    df.drop_duplicates(inplace=True)

    return df


def load_beeline_trips(
    network: str, trip_dir: str, network_dir: str, hb: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Load DataFrame with the beeline trips or generate them if not exists.

    :param network: network ID.
    :param trip_dir: folder where the trips are expected.
    :param network_dir: fodler where the network edgelists are expected.
    :param: hb: GeoPandas GeoDataFrame containing the blocks.

    :return: Pandas DataFrame with the beeline trips.
    """
    try:
        df = pd.read_pickle(f"{trip_dir}/network_{network}_beeline.pickle")
    except FileNotFoundError:
        nw = nx.read_edgelist(f"{network_dir}/{network}.edgelist.gz")
        df = generate_beeline_trips(network, nw, hb)

        if not Path(trip_dir).exists():
            Path(trip_dir).mkdir(parents=True, exist_ok=True)
        df.to_pickle(f"{trip_dir}/network_{n}_beeline.pickle")
    return df


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n", "--number-of-networks",
        type=int,
        required=False,
        default=10)
    # required trick: https://stackoverflow.com/a/44210638/4737417
    parser.add_argument(
        "-s", "--seed",
        type=int,
        required="--observed" not in sys.argv)
    parser.add_argument(
        "--observed",
        type=str,
        required=False,
        default="observed",
        help="observed network filename without extension"
    )
    parser.add_argument(
        "--network-dir",
        type=str,
        required=False,
        default="../output/network/",
        help="network directory")
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="output/trips",
        help="output directory")
    parser.add_argument(
        "--blocks",
        type=str,
        required=False,
        default="../07_build_network/data/house_blocks.geojson",
        help="path for the blocks GeoJSON")
    opts = parser.parse_args()

    hb = prepare_house_blocks(opts.blocks)

    if "--observed" in sys.argv:
        networks = [opts.observed]
    else:
        networks = [f"seed{opts.seed}_{i}"
                    for i in range(opts.number_of_networks)]

    for n in networks:
        nw = nx.read_edgelist(f"{opts.network_dir}/{n}.edgelist.gz")
        df = generate_beeline_trips_from_network(n, nw, hb)

        if not Path(opts.output).exists():
            Path(opts.output).mkdir(parents=True, exist_ok=True)
        df.to_pickle(f"{opts.output}/network_{n}_beeline.pickle.gz")
        print(f"trips for {n} saved...")
    # runs 9m
