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
import matplotlib.pyplot as plt
import seaborn as sns
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
    bc_cfg: pd.DataFrame,
    cc_obs: pd.DataFrame,
    cc_cfg: pd.DataFrame,
    barrier: str
) -> pd.DataFrame:
    qrb = cc_cfg[cc_cfg["barrier"] == barrier][["res", "network", "count"]]\
        .reset_index(drop=True)
    qrb.columns = ["res", "network", "cc_cfg"]
    qru = cc_obs[cc_obs["barrier"] == barrier].groupby("res")["count"].mean()\
        .reset_index()
    qru.columns = ["res", "cc_obs"]

    qrx = bc_cfg[bc_cfg["barrier"] == barrier][["network", "count"]]\
        .reset_index(drop=True)
    qrx.columns = ["network", "bc_cfg"]
    q = qrb.merge(qru, on="res").merge(qrx, on="network")

    q["bc_obs"] = bc_obs[barrier]["count"].mean()
    q = calculate_crossing_ratio(q)
    q = calculate_alternative_crossing_ratio(q)

    return q


def calculate_crossing_ratio(x: pd.DataFrame) -> pd.DataFrame:
    y = x.copy()
    y["bc_ratio"] = y["bc_obs"] / y["bc_cfg"]

    y["cc_ratio"] = (y["cc_obs"] / y["cc_cfg"])
    y["pi"] = y["bc_ratio"] / y["cc_ratio"]

    return y

def calculate_alternative_crossing_ratio(x: pd.DataFrame) -> pd.DataFrame:
    y = x.copy()
    y["obs_ratio"] = y["bc_obs"] / y["cc_obs"]
    y["cfg_ratio"] = y["bc_cfg"] / y["cc_cfg"]
    y["pi2"] = y["obs_ratio"] / y["cfg_ratio"]

    return y


def plot_single(
    df: pd.DataFrame,
    axes: Optional[plt.Axes] = None,
    figsize: tuple[int, int] = (5, 5)
) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=figsize)
    if axes:
        ax = axes
        fig = axes.get_figure()

    sns.lineplot(
        x="res",
        y="pi",
        data=df[["res", "network", "pi"]],
        ax=ax
    )

    return fig, ax


def plot(q_road1, q_road2, q_railways, q_river, q_districts, q_neighborhoods):
    fig, axs = plt.subplots(nrows=1, ncols=6, figsize=(36, 5))
    plot_single(q_road1, axs[0])
    axs[0].set_title("road1")
    plot_single(q_road2, axs[1])
    axs[1].set_title("road2")
    plot_single(q_railways, axs[2])
    axs[2].set_title("railways")
    plot_single(q_river, axs[3])
    # sns.lineplot(
    #     x="res",
    #     y="pi",
    #     data=q_river[["res", "network", "pi"]],
    #     # hue="network",
    #     # data=q_river,
    #     # palette="viridis"
    #     ax=axs[3],
    # )
    axs[3].set_title("river")
    plot_single(q_districts, axs[4])
    axs[4].set_title("districts")
    plot_single(q_neighborhoods, axs[5])
    axs[5].set_title("neighborhoods")
    fig.savefig("figures/null_model.png",
                dpi=120, facecolor="white", bbox_inches="tight")


def get_cc_cfg(
    network_ids: list[str],
    community_crossing_dir: str,
    output: str
) -> pd.DataFrame:
    try:
        cc_cfg = pd.read_csv(f"{output}/cc_cfg.csv")
    except FileNotFoundError:
        cc_cfg = read_cross_community_data(
            network_ids,
            community_crossing_dir,
            groupby=["res", "barrier", "network"])
        cc_cfg.to_csv(f"{output}/cc_cfg.csv", index=False)
    return cc_cfg


def get_random_networks_barrier_crossing(
    rewired_networks: list[str],
    barriers: list[str],
    barrier_crossing_dir: str,
    output: str
) -> dict[str, float]:
    try:
        bc_cfg =  pd.read_csv(f"{output}/bc_cfg.csv")
    except FileNotFoundError:
        bc_cfg = read_cross_barrier_data(
            rewired_networks,
            barriers,
            barrier_crossing_dir
        )
        bc_cfg.to_csv(f"{output}/bc_cfg.csv", index=False)
    return bc_cfg


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
                        default="output/barrier_crossing",
                        help="directory where barrier crossing data is")
    parser.add_argument("--community-crossing", type=str, required=False,
                        default="output/community_crossing",
                        help="directory where community crossing data is")
    parser.add_argument("--output", type=str, required=False,
                        default="output/null_model", help="output directory")
    opts = parser.parse_args()
    Path(opts.output).mkdir(parents=True, exist_ok=True)

    barriers = [
        "road1", "road2", "railways", "river", "districts", "neighborhoods"]

    bc_obs = {}
    for i in barriers:
        bc_obs[i] = pd.DataFrame()
        t = pd.read_csv(f"{opts.barrier_crossing}/observed/{i}.csv.gz")
        t["network"] = "observed"
        bc_obs[i] = pd.concat([bc_obs[i], t])
    logger.info("bc_obs OK")

    rewired_networks = [f"seed{s}_{i}" for s in range(10) for i in range(10)]

    bc_cgf = get_random_networks_barrier_crossing(
        rewired_networks, barriers,
        opts.barrier_crossing, opts.output)
    logger.info("bc_cfg OK")

    cc_obs = pd.read_csv(f"{opts.community_crossing}/observed/inter.csv")
    cc_obs["barrier"] = cc_obs["barrier"].apply(lambda x: x.split("_")[0])
    logger.info("cc_obs OK")

    cc_cfg = get_cc_cfg(
        rewired_networks,
        opts.community_crossing,
        opts.output)
    logger.info("cc_cfg OK")

    q_road1 = merge_eq_parts(bc_obs, bc_cgf, cc_obs, cc_cfg, "road1")
    q_road2 = merge_eq_parts(bc_obs, bc_cgf, cc_obs, cc_cfg, "road2")
    q_railways = merge_eq_parts(bc_obs, bc_cgf, cc_obs, cc_cfg, "railways")
    q_river = merge_eq_parts(bc_obs, bc_cgf, cc_obs, cc_cfg, "river")
    q_districts = merge_eq_parts(bc_obs, bc_cgf, cc_obs, cc_cfg, "districts")
    q_neighborhoods = merge_eq_parts(bc_obs, bc_cgf, cc_obs, cc_cfg,
                                     "neighborhoods")

    q_road1.to_csv(f"{opts.output}/q_road1.csv", index=False)
    q_road2.to_csv(f"{opts.output}/q_road2.csv", index=False)
    q_railways.to_csv(f"{opts.output}/q_railways.csv", index=False)
    q_river.to_csv(f"{opts.output}/q_river.csv", index=False)
    q_districts.to_csv(f"{opts.output}/q_districts.csv", index=False)
    q_neighborhoods.to_csv(f"{opts.output}/q_neighborhoods.csv", index=False)

    plot(q_road1, q_road2, q_railways, q_river, q_districts, q_neighborhoods)
