"""
Convert place_connections pickle to NetworkX edgelist.

:param input: path to the output of build_network_from_places.ipynb
:param output: output directory
"""
import argparse
from pathlib import Path
import pandas as pd
import networkx as nx

START_DATE = "2019-09-01"
END_DATE = "2020-02-29"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--input",
    type=str,
    required=False,
    default=(f"../data/place_connections_{START_DATE}_{END_DATE}.csv"),
    help="place connections input")
parser.add_argument(
    "--output",
    type=str,
    required=False,
    default="output/network",
    help="output directory")
parser.add_argument(
    "--suffix",
    type=str,
    required=False,
    default="",
    help="output filename suffix")
opts = parser.parse_args()

Path(opts.output).mkdir(parents=True, exist_ok=True)

observed = pd.read_csv(opts.input)
observed = observed.groupby(["source", "target"])["weight"].sum().reset_index()

G_obs = nx.from_pandas_edgelist(
    observed,
    source="source",
    target="target",
    edge_attr=["weight"]
)
nx.write_edgelist(G_obs, f"{opts.output}/observed{opts.suffix}.edgelist.gz")
