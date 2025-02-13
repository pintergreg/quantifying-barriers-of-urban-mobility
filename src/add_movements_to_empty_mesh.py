"""
Fill empty full mesh with movements.

If the empty full mesh does not exists yet, it generates first.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import geopandas as gpd
from sklearn.preprocessing import minmax_scale, StandardScaler
from sklearn.compose import ColumnTransformer
from generate_full_mesh import generate, prepare_house_blocks
from typing import Optional, Literal

logger = logging.getLogger("movement to empty mesh")
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def get_mobility(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate dataframe with mobility between the blocks.

    :param df: place connections data with the following columns
    - device_id, day, source, target, weight, distance

    :return: DataFrame with three columns: source, target and the number of\
        mobility between the two blocks.

    ###### Example
    >>> df = pd.DataFrame({'device_id': [1, 1, 1], 'day': ['2019-09-01', \
        '2019-09-02', '2019-09-02'], 'source': [1, 1, 1], 'target': [2, 2, 3],\
        'weight': [1, 1, 1], 'distance': [10, 10, 25]})
    >>> get_mobility(df)
    ... # doctest: +NORMALIZE_WHITESPACE
           source  target  mob_ij
    0       1       2       2
    1       1       3       1
    """
    mob = df.groupby(["source", "target"])["weight"].sum().reset_index()
    mob.columns = ["source", "target", "mob_ij"]
    return mob


def get_pi_pj(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate two dataframes with the number of unique visitors.

    :param df: place connections data with the following schema
    - device_id, day, source, target, weight, distance

    ###### Returns
    - pi (DataFrame) with two columns: source, number of visitors
    - pj (DataFrame) with two columns: target, number of visitors

    ###### Example
    >>> df = pd.DataFrame({'device_id': [1, 1, 1], 'day': ['2019-09-01', \
        '2019-09-02', '2019-09-02'], 'source': [1, 1, 1], 'target': [2, 2, 3],\
        'weight': [1, 1, 1], 'distance': [10, 10, 25]})
    >>> pi, pj = get_pi_pj(df)
    ... # doctest: +NORMALIZE_WHITESPACE
    >>> pi.reset_index()
       source  count
    0       1      1
    >>> pj.reset_index()
       target  count
    0       2      1
    1       3      1
    """
    pi = df.groupby(["source"]).agg(count=pd.NamedAgg("device_id", "nunique"))
    pj = df.groupby(["target"]).agg(count=pd.NamedAgg("device_id", "nunique"))
    return pi, pj


def get_movement_data(
    df: pd.DataFrame, distances: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate movement dataframe.

    :param df: place connections data with the following schema
    - device_id, day, source, target, weight, distance
    :param distances: DataFrame with the distances between *i* and *j*.
    - it has the columns of *source*, *target* and *distance* (in km).

    :return: DataFrame with the columns of\
        *source*, *target*, *distance_ij*, *p_i*, *p_j* and *mob_ij*. Where\
        *distance_ij* is the haversine distance between the source (i) and
        the target block (j). The *p_i* is the number of unique visitors of the
        source, whereas the *p_j* is the number of unique visitors of the
        target. The *mob_ij* is the number of mobility between the two blocks.
    """
    pi, pj = get_pi_pj(df)
    data = distances.merge(pi.rename({"count": "pi"}, axis=1), on="source")\
                    .merge(pj.rename({"count": "pj"}, axis=1), on="target")
    data.columns = ["source", "target", "distance_ij", "p_i", "p_j"]
    data = data.query("distance_ij > 0").reset_index(drop=True).copy()

    mob = get_mobility(df)
    data = data.merge(mob, on=["source", "target"], how="left")
    return data


def get_empty_mesh(hb: gpd.GeoDataFrame, mesh_dir: str) -> pd.DataFrame:
    """
    Read empty mesh dataframe or generate if not exists.

    :param hb: blocks in GeoPandas GeoDataFrame format.
    - It is only used if the mesh.csv is not exist.
    :param mesh_dir: directory where the mesh.csv is.

    :return: the empty mesh in Pandas DataFrame.
    """
    filename = f"{mesh_dir}/mesh.csv"
    ungzipped_exist = os.path.exists(filename)
    gzipped_exist = os.path.exists(f"{filename}.gz")
    if not ungzipped_exist and not gzipped_exist:
        # runs 24m
        generate(filename, hb)
    elif gzipped_exist:
        filename += ".gz"
    return pd.read_csv(filename, engine="pyarrow")


def update_full_mesh_with_movements(
    empty_mesh: pd.DataFrame, data: pd.DataFrame, output: str
) -> pd.DataFrame:
    """
    Update empty edges with movement edges.

    :param empty_mesh: DataFrame containing the empty mesh
    :param data: DataFrame that contains movement edges
    - output of :py:func:`get_movement_data`
    :param output:

    :return: full mesh with movements edges, contains NAs
    """
    try:
        mesh = pd.read_csv(f"{output}/mesh_updated.csv", engine="pyarrow")
    except FileNotFoundError:
        logger.info(f"{output}/mesh_updated.csv was not found. Generating it.")
        # 10m
        mesh = pd.concat([empty_mesh, data])
        mesh.drop_duplicates(subset=["source", "target"], keep="last",
                             inplace=True)
        mesh.to_csv(f"{output}/mesh_updated.csv", index=False)
    return mesh


def load_barrier_crossings(bc_path: str) -> tuple[pd.DataFrame, pd.DataFrame,
                                                  pd.DataFrame, pd.DataFrame,
                                                  pd.DataFrame, pd.DataFrame]:
    """
    Load the barrier crossing DataFrames.

    :param bc_path: path for the barrier crossing data.

    :return: six DataFrames for the six different kind of barriers.
    """
    bc_road2 = pd.read_csv(f"{bc_path}/road2.csv.gz", engine="pyarrow")
    bc_road2.columns = ["source", "target", "secondary_count"]

    bc_road1 = pd.read_csv(f"{bc_path}/road1.csv.gz", engine="pyarrow")
    bc_road1.columns = ["source", "target", "primary_count"]

    bc_river = pd.read_csv(f"{bc_path}/river.csv.gz", engine="pyarrow")
    bc_river.columns = ["source", "target", "river_count"]

    bc_railways = pd.read_csv(f"{bc_path}/railways.csv.gz", engine="pyarrow")
    bc_railways.columns = ["source", "target", "railway_count"]

    bc_districts = pd.read_csv(f"{bc_path}/districts.csv.gz", engine="pyarrow")
    bc_districts.columns = ["source", "target", "districts_count"]

    bc_adm10 = pd.read_csv(f"{bc_path}/neighborhoods.csv.gz", engine="pyarrow")
    bc_adm10.columns = ["source", "target", "neighborhoods_count"]

    return bc_road1, bc_road2, bc_river, bc_railways, bc_districts, bc_adm10


def generate_distances(trips_path: str) -> pd.DataFrame:
    """
    Generate distances DataFrame.

    The method reprojects the geometry to a meter-unit projection, EPSG:23700\
    as the study works with Hungarian data.
    Distance is in meter.

    :param trips_path: path to trips shapefile.

    :return: DataFrame with three columns (source, target, distance)
    """
    trips = pd.read_pickle(trips_path)
    trips = gpd.GeoDataFrame(trips, geometry="geometry", crs=4326)
    trips.to_crs(23700, inplace=True)
    trips["distance"] = trips.geometry.length
    trips["distance"] = trips["distance"].apply(np.round)
    distances = trips[["source", "target", "distance"]].copy()
    return distances


def add_one_to_prevent_log_zero(df: pd.DataFrame) -> pd.DataFrame:
    """
    Increase the zero values with one to prevent log(0).

    This should affect the following column:
    - p_i
    - p_j
    - mob_ij
    - primary_count
    - secondary_count
    - river_count
    - railway_count
    - districts_count
    - neighborhoods_count

    :param df: import DataFrame with the previous column.

    :return: DataFrame in which the values are increased by one.

    >>> df = pd.DataFrame({'p_i': [0], 'p_j': [0], 'mob_ij': [0],\
                           'primary_count': [0], 'secondary_count': [0],\
                           'river_count': [0], 'railway_count': [0],\
                           'districts_count': [0], 'neighborhoods_count': [0]})
    >>> df.iloc[0].sum()
    0
    >>> df2 = add_one_to_prevent_log_zero(df)
    >>> df2.iloc[0].sum()
    9
    """
    temp = df.copy()
    for i in ["p_i", "p_j", "mob_ij", "primary_count", "secondary_count",
              "river_count", "railway_count", "districts_count",
              "neighborhoods_count"]:
        temp[i] = temp[i] + 1
    return temp


def take_logarithm(
    df: pd.DataFrame,
    transform: Optional[Literal["minmax_scale", "standard_scale"]] = None
) -> pd.DataFrame:
    """
    Take the logarithm of the values before appling the OLS model.

    .. note::
        One is added to counts to prevent log(0)

    .. warning::
        As the logarithm is taken here, the model applied to the output\
        should not contain logarithm again.

    This should affect the following column:
    - p_i
    - p_j
    - mob_ij
    - primary_count
    - secondary_count
    - river_count
    - railway_count
    - districts_count
    - neighborhoods_count

    :param df: import DataFrame with the previous column.

    :return: DataFrame in which the logarithm of the values may be transformed.
    >>> data = [1, 2, 4, 0, 2, 3, 6, 1, 0, 2, 5, 4, 3, 6, 2, 1, 2, 2, 3, 3, 2]
    >>> df = pd.DataFrame({'p_i': data, 'p_j': data, 'mob_ij': data,\
                           'primary_count': data, 'secondary_count': data,\
                           'river_count': data, 'railway_count': data,\
                           'districts_count': data, 'neighborhoods_count': data})
    >>> res = take_logarithm(df, transform="standard_scale")
    >>> res["primary_count"].round(6).tolist()
    ... # doctest: +NORMALIZE_WHITESPACE
    [-0.889814, -0.105594,  0.882406, -2.230446, -0.105594,  0.450819,\
     1.533185, -0.889814, -2.230446, -0.105594,  1.235038,  0.882406,\
     0.450819,  1.533185, -0.105594, -0.889814, -0.105594, -0.105594,\
     0.450819,  0.450819, -0.105594]
    """
    temp = df.copy()
    for i in ["p_i", "p_j", "mob_ij", "primary_count", "secondary_count",
              "river_count", "railway_count", "districts_count",
              "neighborhoods_count"]:
        log_ = np.log(temp[i] + 1)
        if transform == "minmax_scale":
            temp[i] = minmax_scale(log_)
        elif transform == "standard_scale":
            scaler = StandardScaler()
            temp[i] = scaler.fit_transform(np.reshape(log_, (-1, 1)))
        elif transform is None:
            temp[i] = log_
    return temp


def update_empty_mesh_with_movements_brute_force(
    empty_mesh: pd.DataFrame, data: pd.DataFrame, pre: pd.DataFrame,
    output: str
) -> None:
    """
    Update empty mesh with movements, in a memory consuming way.

    .. warning::
        This method requires a massive amount of memory. 25 GiB at least.

    :param empty_mesh: empty full mesh
    - loaded by :py:func:`get_empty_mesh`
    :param data: movement data
    - loaded by :py:func:`get_movement_data`
    :param pre: merged barrier crossing data
    :param output: directory where to save the output
    """
    mesh = update_full_mesh_with_movements(empty_mesh, data, output=output)

    mesh = mesh.merge(pre, on=["source", "target"], how="left")
    mesh.fillna(0, inplace=True)

    mesh = add_one_to_prevent_log_zero(mesh)

    mesh.to_csv(f"{output}/mesh_final.csv.gz", index=False)


def update_empty_mesh_with_movements_stream(
    data: pd.DataFrame, pre: pd.DataFrame,
    mesh: str,
    output: str,
    keep_self_loops: bool = True,
    transform: Optional[Literal["minmax_scale", "standard_scale"]] = None
) -> None:
    """
    Update empty mesh with movements, using stream processing.

    Functionally it is equivalent to \
    py:func:`update_empty_mesh_with_movements_brute_force`, but works memory
    efficiently as does not read the full CSV into memory, but only a small
    chunk at a time and the transformations are executed on the chunks.
    The movement data is also filtered to the chunk before the values are\
    updated.
    The former is kept for documentation purposes.

    :param data: movement data
    - loaded by :py:func:`get_movement_data`
    :param pre: merged barrier crossing data
    :param output: directory where to save the output
    :param normalize_also: if True, the count columns are also normalized\
        using MinMax scaling
    :param keep_self_loops: if True, edges with the same source and target\
        nodes are kept in the dataframe
    """
    with pd.read_csv(mesh, chunksize=1_000_000) as reader:
        for k, chunk in enumerate(reader):
            logger.info(f"heartbeat: {k}")

            # data_chunk based on: https://stackoverflow.com/a/33282617/4737417
            idx_chunk = chunk.set_index(["source", "target"]).index
            idx_data = data.set_index(["source", "target"]).index
            data_chunk = data[idx_data.isin(idx_chunk)].copy()

            temp = pd.concat([chunk, data_chunk])
            temp.drop_duplicates(subset=["source", "target"], keep="last",
                                 inplace=True)

            temp = temp.merge(pre, on=["source", "target"], how="left")
            temp.fillna(0, inplace=True)

            temp = take_logarithm(temp, transform=transform)

            if not keep_self_loops:
                temp = remove_self_loops(temp)

            # header inspiration: https://stackoverflow.com/a/17975690/4737417
            temp.to_csv(output, index=False, mode="a",
                        header=not os.path.exists(output))


def remove_self_loops(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove self loops.

    :param df: mesh as DataFrame

    :return: copy of input DataFrame without rows where source equals target.
    """
    return df[df["source"] != df["target"]].copy()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=str, required=False,
        default="data/place_connections_2019-09-01_2020-02-29.csv",
        help="place connections")
    parser.add_argument(
        "--mesh",
        type=str,
        required=False,
        default="output/mesh.csv",
        help="empty mesh")
    parser.add_argument(
        "--blocks",
        type=str,
        required=False,
        default="data/house_blocks.geojson",
        help="blocks GeoJSON")
    parser.add_argument(
        "--observed-trips",
        type=str,
        required=False,
        default="output/trips/network_observed_beeline.pickle.gz",
        help="blocks GeoJSON")
    parser.add_argument(
        "--observed-barrier-crossing-dir",
        type=str,
        required=False,
        default="output/barrier_crossing/observed",
        help="blocks GeoJSON")
    parser.add_argument(
        "--transform",
        type=str,
        required=False,
        help="standard_scale|minmax_scale")
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="output/mesh_final.csv",
        help="result filename")
    opts = parser.parse_args()

    distances = generate_distances(opts.observed_trips)

    hb = prepare_house_blocks(opts.blocks)

    df = pd.read_csv(opts.input)
    data = get_movement_data(df, distances)

    logger.info("load barrier crossings")
    bc_road1, bc_road2, bc_river, bc_railways, bc_districts, \
        bc_adm10 = load_barrier_crossings(opts.observed_barrier_crossing_dir)

    pre = bc_river.merge(bc_road1, on=["source", "target"], how="left")\
                  .merge(bc_road2, on=["source", "target"], how="left")\
                  .merge(bc_railways, on=["source", "target"], how="left")\
                  .merge(bc_districts, on=["source", "target"], how="left")\
                  .merge(bc_adm10, on=["source", "target"], how="left")

    # required for brute force version
    # logger.info("load empty mesh")
    # mesh = get_empty_mesh(hb, mesh_dir=opts.output)
    logger.info("update mesh")
    update_empty_mesh_with_movements_stream(
        data, pre, opts.mesh,
        output=opts.output, transform=opts.transform)
