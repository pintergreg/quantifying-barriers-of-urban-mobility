import networkx as nx
import yaml


def density(g: nx.Graph, output: str) -> None:
    d = nx.density(g)
    with open(output, "w") as fp:
        yaml.dump({"density": d}, fp)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        type=str,
        required=False,
        default="output/network/observed.edgelist.gz",
        help="input network in edgelist format",
    )
    parser.add_argument(
        "--filename",
        type=str,
        required=False,
        default="observed",
        help="output filename",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="output/network/stats",
        help="output directory",
    )
    opts = parser.parse_args()

    Path(opts.output).mkdir(parents=True, exist_ok=True)

    g = nx.read_edgelist(opts.network)

    density(g, f"{opts.output}/{opts.filename}.yaml")