r"""
Evaluate null model.

$$
\Pi = \frac{\frac{BC^{obs}}{BC^{config}}}{\frac{CC^{obs}}{CC^{config}}}
$$
"""
from pathlib import Path
import logging
import sys
import json
import pandas as pd
from typing import Optional

logger = logging.Logger("null model")
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def read_cross_community_data(
    networks: list[str],
    path: str,
    groupby: list[str] = ["res", "barrier"]
) -> pd.DataFrame:
    cc_cfg_raw = pd.DataFrame()
    for network in networks:
        t = pd.read_csv(f"{path}/{network}/inter.csv")
        t["network"] = network
        cc_cfg_raw = pd.concat([cc_cfg_raw, t])

    cc_cfg = cc_cfg_raw.groupby(groupby)["count"].mean().reset_index()
    cc_cfg["barrier"] = cc_cfg["barrier"].apply(lambda x: x.split("_")[0])
    return cc_cfg


def merge_eq_parts(
    bc_obs: dict,
    cc_obs: pd.DataFrame,
    barrier: str
) -> pd.DataFrame:
    q = cc_obs[cc_obs["barrier"] == barrier].groupby("res")["count"].mean()\
        .reset_index()
    q.columns = ["res", "cc_obs"]

    q["bc_obs"] = bc_obs[barrier]["count"].sum()
    q = calculate_crossing_ratio(q)

    return q


def calculate_crossing_ratio(x: pd.DataFrame) -> pd.DataFrame:
    y = x.copy()
    y["ratio"] = y["bc_obs"] / y["cc_obs"]

    return y


def read_cross_barrier_data(
    rewired_networks: list[str],
    barriers: list[str],
    barrier_crossing_dir: str
) -> pd.DataFrame:
    bc_cfg = pd.DataFrame()
    for i in barriers:
        logger.info(f"bc_cfg {i} doing")
        for network in rewired_networks:
            t = pd.read_csv(f"{barrier_crossing_dir}/{network}/{i}.csv.gz")
            t["network"] = network
            t = t.groupby("network")["count"].mean().reset_index()
            t["barrier"] = i
            bc_cfg = pd.concat([bc_cfg, t])
    return bc_cfg


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--barrier-crossing", type=str, required=False,
                        default="output/barrier_crossing/observed",
                        help="directory where barrier crossing data is")
    parser.add_argument("--community-crossing", type=str, required=False,
                        default="output/community_crossing",
                        help="directory where community crossing data is")
    parser.add_argument("--output", type=str, required=False,
                        default="output/obs_ratio/observed", help="output directory")
    opts = parser.parse_args()
    Path(opts.output).mkdir(parents=True, exist_ok=True)

    barriers = [
        "road1", "road2", "railways", "river", "districts", "neighborhoods"]

    bc_obs = {}
    for i in barriers:
        bc_obs[i] = pd.DataFrame()
        t = pd.read_csv(f"{opts.barrier_crossing}/{i}.csv.gz")
        t["network"] = "observed"
        bc_obs[i] = pd.concat([bc_obs[i], t])
    logger.info("bc_obs OK")

    cc_obs = pd.read_csv(f"{opts.community_crossing}/inter.csv")
    cc_obs["barrier"] = cc_obs["barrier"].apply(lambda x: x.split("_")[0])
    logger.info("cc_obs OK")

    q_road1 = merge_eq_parts(bc_obs, cc_obs, "road1")
    q_road2 = merge_eq_parts(bc_obs, cc_obs, "road2")
    q_railways = merge_eq_parts(bc_obs, cc_obs, "railways")
    q_river = merge_eq_parts(bc_obs, cc_obs, "river")
    q_districts = merge_eq_parts(bc_obs, cc_obs, "districts")
    q_neighborhoods = merge_eq_parts(bc_obs, cc_obs, "neighborhoods")

    q_road1.to_csv(f"{opts.output}/q_road1.csv", index=False)
    q_road2.to_csv(f"{opts.output}/q_road2.csv", index=False)
    q_railways.to_csv(f"{opts.output}/q_railways.csv", index=False)
    q_river.to_csv(f"{opts.output}/q_river.csv", index=False)
    q_districts.to_csv(f"{opts.output}/q_districts.csv", index=False)
    q_neighborhoods.to_csv(f"{opts.output}/q_neighborhoods.csv", index=False)
