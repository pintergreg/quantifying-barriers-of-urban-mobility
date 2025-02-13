import pathlib
import pandas as pd
import geopandas as gpd
import numpy as np
import networkx as nx


def read_community_data(
    path: str,
    run_range: range,
    resolution_range: np.ndarray
) -> pd.DataFrame:
    """
    Read or generate (if not exist) the communities per resolution and run.

    :param path: directory of the data
    :param run_range: range of the different community detection runs\
        to iterate over
    - from 0 to 20 (excluded) in the paper
    :param resolution_range: range of the resolution to iterate over
    - from 1.0 to 10.5 (excluded) by 0.5 steps in the paper

    :return: communities per resolution and run
    """
    try:
        comm = pd.read_csv(f"{path}/communities_per_res_and_run.csv.gz")
    except FileNotFoundError:
        # 2m 25s
        comm = pd.DataFrame()
        for run in run_range:
            for res in resolution_range:
                temp = gpd.read_file(
                    f"{path}/{run}/"
                    f"2019-09-01_2020-02-29_resolution{res}.geojson",
                    engine="pyogrio")
                temp["run"] = run
                temp["res"] = res
                temp.drop(["area", "geometry"], axis=1, inplace=True)
                comm = pd.concat([comm, temp])
        comm.dropna(subset=["community"], inplace=True)
        comm.to_csv(f"{path}/communities_per_res_and_run.csv.gz",
                    index=False)
    return comm


def read_barrier_crossing_data(
    path: str, network: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame,
           pd.DataFrame, pd.DataFrame]:
    """
    Read the network-specific barrier crossing data.

    :param network: the ID of the network

    :return: six DataFrames with the barrier crossing data.
    - bc_road1: OSM motorways and primary road crossing count per edge
    - bc_road2: OSM secondary and primary road crossing count per edge
    - bc_railw: railway crossing count per edge
    - bc_river: river crossing count
    - bc_distr: district crossing count
    - bc_adm10: neighborhood crossing count

    .. note::
        Every returned DataFrames has three columns: source, target and count.
    """
    bc_road1 = pd.read_csv(f"{path}/{network}/road1.csv.gz")
    bc_road1.columns = ["source", "target", "road1_count"]
    bc_road2 = pd.read_csv(f"{path}/{network}/road2.csv.gz")
    bc_road2.columns = ["source", "target", "road2_count"]
    bc_railw = pd.read_csv(f"{path}/{network}/railways.csv.gz")
    bc_railw.columns = ["source", "target", "railways_count"]
    bc_river = pd.read_csv(f"{path}/{network}/river.csv.gz")
    bc_river.columns = ["source", "target", "river_count"]
    bc_distr = pd.read_csv(f"{path}/{network}/districts.csv.gz")
    bc_distr.columns = ["source", "target", "districts_count"]
    bc_adm10 = pd.read_csv(f"{path}/{network}/neighborhoods.csv.gz")
    bc_adm10.columns = ["source", "target", "neighborhoods_count"]

    return bc_road1, bc_road2, bc_railw, bc_river, bc_distr, bc_adm10


def merge_network_with_barrier_data(
    df: pd.DataFrame, network: str, path: str
) -> pd.DataFrame:
    """
    Merge network with barrier data and replaces NAs with zero.

    :param df: network as edglist DataFrame
    :param network: network ID.
    :param path: path for barrier crossing data

    :return: the merged DataFrame.
    """
    road1, road2, railw, river, distr, \
        adm10 = read_barrier_crossing_data(path, network)
    m = df.merge(road1, on=["source", "target"], how="left")\
          .merge(road2, on=["source", "target"], how="left")\
          .merge(railw, on=["source", "target"], how="left")\
          .merge(river, on=["source", "target"], how="left")\
          .merge(distr, on=["source", "target"], how="left")\
          .merge(adm10, on=["source", "target"], how="left")
    m.fillna(0, inplace=True)
    return m


def merge_with_communities(
    m: pd.DataFrame, comm: pd.DataFrame,
    run_range: range, resolution_range: np.ndarray
) -> tuple[pd.DataFrame, pd.DataFrame]:
    intra = pd.DataFrame()
    inter = pd.DataFrame()
    for run in run_range:
        for res in resolution_range:
            c = comm.query(f"run == {run} & res == {res}").copy()
            q = m.merge(c.rename({"id": "source"}, axis=1), on="source")\
                .merge(c.rename({"id": "target"}, axis=1), on="target",
                       suffixes=["_source", "_target"])

            columns_to_sum = ["road1_count", "road2_count", "railways_count",
                              "river_count", "districts_count",
                              "neighborhoods_count"]
            bc_inter = q.query(
                "community_source != community_target"
            )[columns_to_sum].sum()
            bc_intra = q.query(
                "community_source == community_target"
            )[columns_to_sum].sum()
            bc_inter = bc_inter.reset_index()
            bc_inter.columns = ["barrier", "count"]
            bc_inter["run"] = run
            bc_inter["res"] = res

            bc_intra = bc_intra.reset_index()
            bc_intra.columns = ["barrier", "count"]
            bc_intra["run"] = run
            bc_intra["res"] = res

            intra = pd.concat([intra, bc_intra])
            inter = pd.concat([inter, bc_inter])
    return inter, intra


def calc_ratio(inter: pd.DataFrame, intra: pd.DataFrame) -> pd.DataFrame:
    bc = inter.reset_index()\
            .merge(intra.reset_index(), on=["run", "res", "barrier"],
                   suffixes=["_inter", "_intra"])\
            .drop(["index_inter", "index_intra"], axis=1)
    bc["ratio"] = bc["count_inter"] / (bc["count_inter"] + bc["count_intra"])
    bc["ratio2"] = bc["count_inter"] / bc["count_intra"]
    return bc


def read_network(name: str, path: str) -> pd.DataFrame:
    """
    Read a network.

    :param name: network ID
    :param path: directory with the networks

    :return: network in a Pandas DataFrame format.
    """
    G = nx.read_edgelist(f"{path}/{name}.edgelist.gz")
    df = nx.to_pandas_edgelist(G)
    df["source"] = pd.to_numeric(df["source"])
    df["target"] = pd.to_numeric(df["target"])
    df = df.loc[df.index.repeat(df["weight"])]\
           .drop("weight", axis=1).reset_index(drop=True).copy()
    return df


def generate_community_crossing_data(
    comm: pd.DataFrame, network: str, output: pathlib.Path, bc_path: str,
    network_dir: str,
    run_range: range, resolution_range: np.ndarray
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not output.exists():
        output.mkdir(parents=True, exist_ok=True)
    nw = read_network(network, network_dir)

    m = merge_network_with_barrier_data(nw, network, bc_path)
    inter, intra = merge_with_communities(m, comm, run_range, resolution_range)

    intra.reset_index(drop=True, inplace=True)
    inter.reset_index(drop=True, inplace=True)

    intra.to_csv(f"{str(output)}/intra.csv", index=False)
    inter.to_csv(f"{str(output)}/inter.csv", index=False)
    return intra, inter


def load_community_crossing_data(
    comm: pd.DataFrame, network: str, bc_path: str, network_dir: str,
    run_range: range, resolution_range: np.ndarray
) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = pathlib.Path(f"output/community/{network}")
    try:
        intra = pd.read_csv(f"{str(path)}/intra.csv")
        inter = pd.read_csv(f"{str(path)}/inter.csv")
    except FileNotFoundError:
        # takes about 1m to generate
        intra, inter = generate_community_crossing_data(
            comm, network, path, bc_path,
            network_dir, run_range, resolution_range)
    return intra, inter


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=str, required=True)
    parser.add_argument("--network-dir", type=str, required=False,
                        default="output/network",
                        help="directory where the networks are")
    parser.add_argument("--communities", type=str, required=False,
                        default="output/place_communities/louvain",
                        help="directory with community data")
    parser.add_argument("--barrier-crossing", type=str, required=False,
                        default="output/barrier_crossing",
                        help="directory with barrier crossing data")
    parser.add_argument("--output", type=str, required=False,
                        default="output/community_crossing",
                        help="output directory")
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
    parser.add_argument("--run-start", type=int, required=False,
                        default=0)
    parser.add_argument("--run-stop", type=int, required=False,
                        default=20, help="excluded")
    opts = parser.parse_args()

    run_range = range(opts.run_start, opts.run_stop)
    resolution_range = np.arange(
            opts.resolution_start,
            opts.resolution_stop,
            opts.resolution_step
    )
    comm = read_community_data(
        opts.communities,
        run_range,
        resolution_range
    )

    directory = pathlib.Path(f"{opts.output}/{opts.network}")
    intra_p = pathlib.Path(f"{directory}/intra.csv")
    inter_p = pathlib.Path(f"{directory}/inter.csv")
    if not intra_p.exists() and not inter_p.exists():
        # bc_path = "../12_count_barrier_crossing/output/barrier_crossing"
        generate_community_crossing_data(
            comm, opts.network, directory, opts.barrier_crossing,
            opts.network_dir, run_range, resolution_range)
