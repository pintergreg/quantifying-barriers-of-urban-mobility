import pandas as pd
import geopandas as gpd
import numpy as np
import networkx as nx
import pathlib
from itertools import repeat
from multiprocessing import Pool
from networkx.algorithms.community import louvain_communities


def create_community_df(
    communities: list,
    column_suffix: str = ""
) -> pd.DataFrame:
    """
    Create DataFrame from Louvain community output.

    :param communities: community annotations returned by\
        ``networkx.algorithms.community.louvain_communities``
    :param column_suffix: optional suffix after column name *community*.

    :return: DataFrame with block ID and community ID

    .. note::
        Community ID-s are order numbers, valid only for a given execution.
    """
    res = {}
    for i, comms in enumerate(communities):
        for c in comms:
            res[c] = i
    comm_df = pd.DataFrame.from_dict(res, orient="index",
                                     columns=["community"+column_suffix])
    comm_df.index.name = "id"
    comm_df.reset_index(inplace=True)
    comm_df["id"] = pd.to_numeric(comm_df["id"])

    return comm_df


def save_blocks_with_community_annotaion(
    cdf: pd.DataFrame, res: float, run: int
) -> None:
    """
    Save the blocks with community anotations as GeoJSON.

    :param cdf: community DataFrame.
    :param res: resolution parameter of the Louvain community detection.
    :param run: number of execution with the given resolution.
    """
    global hb
    global options
    hbc = hb.merge(cdf, on="id", how="left")
    path = (f"{options['output']}/{options['target']}/"
            f"{options['community_dir']}/louvain/{run}")
    pathlib.Path(f"{path}/").mkdir(parents=True, exist_ok=True)
    hbc.to_file(f"{path}/{options['start_date']}_{options['end_date']}"
                f"_resolution{res}.geojson", driver="GeoJSON")


def save_community_df(cdf: pd.DataFrame, res: float, run: int) -> None:
    """
    Save the community DataFrame.

    :param cdf: community DataFrame.
    :param res: resolution parameter of the Louvain community detection.
    :param run: number of execution with the given resolution.
    """
    global options
    path = (f"{options['output']}/{options['target']}/"
            f"{options['community_dir']}/louvain/{run}")
    cdf.to_csv(f"{path}/{options['start_date']}_{options['end_date']}"
               f"_resolution{res}.csv", index=False)


def kernel(run: int, res: float) -> pd.DataFrame:
    global g
    communities = louvain_communities(g, resolution=res, seed=run)
    cdf = create_community_df(communities)

    save_blocks_with_community_annotaion(cdf, res, run)

    cdf["resolution"] = res
    cdf["run"] = run

    save_community_df(cdf, res, run)
    return cdf


def load_network(place_connections_path: str) -> nx.Graph:
    """
    Read place connections (observed network) and transforms the edgelist to a\
    network.

    :param place_connections_path: path of the observed network in CSV format.

    :return: movement network.
    """
    full = pd.read_csv(place_connections_path)

    nw = full.groupby(["source", "target"])["weight"].sum().reset_index()
    g = nx.from_pandas_edgelist(nw, source="source", target="target",
                                edge_attr="weight")
    return g


if __name__ == "__main__":
    import argparse
    import logging
    import sys

    logger = logging.getLogger("community detection")
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=int, required=False, default=4)
    parser.add_argument("--start-date", type=str, required=False,
                        default="2019-09-01")
    parser.add_argument("--end-date", type=str, required=False,
                        default="2020-02-29")
    parser.add_argument("--resolution-start", type=float, required=False,
                        default=1.0)
    parser.add_argument("--resolution-stop", type=float, required=False,
                        default=10.5, help="excluded")
    parser.add_argument("--resolution-step", type=float, required=False,
                        default=0.5)
    parser.add_argument("--run-start", type=int, required=False,
                        default=0)
    parser.add_argument("--run-stop", type=int, required=False,
                        default=10, help="excluded")
    parser.add_argument("--community-dir", type=str, required=False,
                        default="place_communities",
                        help="communities directory")
    parser.add_argument(
        "--observed-network", type=str, required=False,
        default=("../07_build_network/output/"
                 "place_connections_2019-09-01_2020-02-29.csv"),
        help="observed network in edgelist pickle format")
    parser.add_argument(
        "--blocks", type=str, required=False,
        default="../07_build_network/data/house_blocks.geojson",
        help="blocks GeoJSON")
    parser.add_argument("--target", type=str, required=False,
                        default="", help="output version")
    parser.add_argument("--output", type=str, required=False,
                        default="output", help="output directory")
    opts = parser.parse_args()

    hb = gpd.read_file(opts.blocks)

    g = load_network(opts.observed_network)

    output_file = (
        f"{opts.output}/{opts.target}/{opts.community_dir}/"
        f"louvain_{opts.resolution_start}-{opts.resolution_stop}_runs_"
        f"{opts.run_start}-{opts.run_stop}.pickle"
    )
    pathlib.Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    options = {"output": opts.output, "target": opts.target,
               "community_dir": opts.community_dir,
               "start_date": opts.start_date, "end_date": opts.end_date}
    result = pd.DataFrame()
    for res in np.arange(opts.resolution_start, opts.resolution_stop,
                         opts.resolution_step):
        logger.info(f"resolution {res}")
        with Pool(opts.pool) as pool:
            partials = pool.starmap(
                kernel,
                zip(range(opts.run_start, opts.run_stop), repeat(res))
            )
            for i in partials:
                result = pd.concat([result, i])
    result.to_pickle(output_file)
