"""
Rewire network, a custom implementation of configuration model [#cfgm]_.

The script generates *n* networks for the provided seed.
In the paper seeds from 0 to 9 are used with n=10, and the output filenames
follow the schema of ``seed{seed}_{i}.edgelist.gz``.

.. [#cfgm] Sagarra, O., Font-Clos, F., Pérez-Vicente, C. J. & Díaz-Guilera,\
  A. *The configuration multi-edge model: Assessing the effect of fixing node\
  strengths on weighted network magnitudes*. Europhys. Lett. 107, 38002 (2014).
"""
import pandas as pd
import networkx as nx
import numpy as np
import logging
import random
import matplotlib.pyplot as plt
from typing import Any, Optional, Iterable
from collections import Counter

logger = logging.getLogger("network rewiring")
logger.setLevel(logging.DEBUG)


def rewire_network(
    g: dict[Any, int], seed: Optional[int] = None, threshold: int = 10_000
) -> list[tuple[Any, Any]] | float:
    """
    Rewire network.

    :param g: Nodes with degree.

    :return: list of tuples or NaN

    .. note::
        In some cases the rewiring fails as an invalid graph is produced that
        do not macth the input constrains. In these cases a NaN value is
        returned as the algorithm does not try to fix the issue.
        It is the caller's responsibility to handle these cases.

    ###### Examples
    >>> rewire_network({'a': 3, 'b': 1, 'c': 1}, seed=1450)
    nan
    >>> rewire_network({'a': 3, 'b': 2, 'c': 1}, seed=5)
    [('a', 'b'), ('a', 'b'), ('a', 'c')]
    >>> rewire_network({'a': 3, 'b': 2, 'c': 1, 'd': 18, 'e': 4, 'f': 2,\
                        'g': 1, 'h': 4, 'i': 3, 'j': 1, 'k': 2, 'l': 1},\
                       seed=0)
    ... # doctest: +NORMALIZE_WHITESPACE
    [('d', 'a'), ('d', 'l'), ('d', 'h'), ('d', 'c'), ('d', 'j'), ('d', 'g'),\
     ('d', 'f'), ('d', 'a'), ('d', 'k'), ('d', 'i'), ('d', 'e'), ('d', 'k'),\
     ('d', 'b'), ('d', 'e'), ('d', 'e'), ('d', 'a'), ('d', 'b'), ('d', 'f'),\
     ('h', 'e'), ('h', 'i'), ('h', 'i')]
    """
    res = []
    req = {k: v for k, v in g.items() if v > 0}

    while len({k: v for k, v in req.items() if v > 0}) > 0:
        req = dict(sorted(req.items(), key=lambda x: x[1]))
        req = {k: v for k, v in req.items() if v > 0}

        q0 = list(req)[-1]
        q1 = req.pop(q0)

        req = dict(req)

        try:
            lrc = limited_random_choice(list(req.keys()), n=q1, limits=req,
                                        seed=seed)
            if lrc is None:
                continue
            iter, _, _ = lrc
            for i in iter:
                res.append((q0, i))
                req[i] -= 1
        except ValueError:
            return np.NaN
    return res


def generate_networks_from_graph(
    g: nx.Graph, n: int, seed: Optional[int] = None,
    infinite_loop_threshold: int = 10_000
) -> list[tuple[tuple[Any, Any], ...]] | None:
    """
    Generate n new networks keeping the degrees of the input network.

    :param g: source network
    :param n: number of desired networks

    :return: list with n networks

    .. note::
        As the input constraints might not be satisfiable,
        the method terminates with ``None`` if the threshold is reached.

    ###### Example
    >>> g = nx.MultiGraph()
    >>> _ = g.add_edges_from([('a', 'b'), ('a', 'b'), ('a', 'c')])
    >>> generate_networks_from_graph(g, 3, seed=11)
    ... # doctest: +NORMALIZE_WHITESPACE
    [(('a', 'b'), ('a', 'b'), ('a', 'c')),
     (('a', 'c'), ('a', 'b'), ('a', 'b')),
     (('a', 'b'), ('a', 'c'), ('a', 'b'))]
    """
    degrees = dict(g.degree())
    return generate_networks(degrees, n, seed, infinite_loop_threshold)


def generate_networks(
    g: dict[Any, int], n: int, seed: Optional[int] = None,
    infinite_loop_threshold: int = 10_000
) -> list[tuple[tuple[Any, Any], ...]] | None:
    """
    Generate n new networks keeping the degrees of the input network.

    :param g: source network as degree dictionary
    :param n: number of desired networks

    :return: list with n networks

    .. note::
        As the input constraints might not be satisfiable,
        the method terminates with ``None`` if the threshold is reached.

    ###### Examples
    >>> g = {'a': 3, 'b': 1, 'c': 1}
    >>> generate_networks(g, 2, seed=1450, infinite_loop_threshold=10)
    >>> generate_networks({'a': 3, 'b': 2, 'c': 1}, 3, seed=11)
    ... # doctest: +NORMALIZE_WHITESPACE
    [(('a', 'b'), ('a', 'b'), ('a', 'c')),
     (('a', 'c'), ('a', 'b'), ('a', 'b')),
     (('a', 'b'), ('a', 'c'), ('a', 'b'))]
    """
    results = []  # type: list[tuple[tuple[Any, Any], ...]]
    k = 0
    if seed:
        random.seed(seed)
    while len(results) < n:
        res = rewire_network(g)
        if not isinstance(res, float):
            results.append(tuple(res))
        else:
            logger.debug("rewired graph is invalid")
        k += 1
        if k == infinite_loop_threshold:
            return None

    return results


def convert_to_graph(edgelist: Iterable[tuple[Any, Any]]) -> nx.Graph:
    """
    Convert edge list to graph.

    :param edgelist: list of edges (u, v)

    :return: a networkx graph

    ###### Examples
    >>> el = [('a', 'b'), ('a', 'b'), ('a', 'c')]
    >>> G = convert_to_graph(el)
    >>> G.edges.data()
    EdgeDataView([('a', 'b', {'weight': 2}), ('a', 'c', {'weight': 1})])
    """
    res_df = pd.DataFrame.from_records(edgelist, columns=["source", "target"])
    res_df["weight"] = 1
    res_df_weighted = res_df.groupby(["source", "target"])\
                            .count().reset_index()

    G = nx.from_pandas_edgelist(res_df_weighted, edge_attr=["weight"])
    return G


def plot_graph(G: nx.Graph, seed: int = 5) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot network using spring layout with constant seed.

    :param G: graph
    :param seed: seed for spring layout method

    ###### Returns
    - **fig**: figure
    - **ax**: axes
    """
    fig, ax = plt.subplots()
    pos = nx.spring_layout(G, seed=seed)
    labels = {e: G.edges[e]["weight"] for e in G.edges}
    nx.draw_networkx(G, pos=pos, ax=ax)
    nx.draw_networkx_edge_labels(G, pos=pos, edge_labels=labels, ax=ax)
    ax.margins(0)
    ax.axis("off")
    return fig, ax


def limited_random_choice(
    a: list, n: int, limits: dict[Any, int],
    seed: Optional[int] = None, threshold: int = 1_000_000
) -> tuple[list, dict, int] | None:
    """
    Choose *n* elements from a collection with replacement, but respecting the\
        given limits of how many time a given element can be chosen.

    :param a: input list
    :param n: number of elements to choose

    ###### Returns
    - list of the chosen elements
    - counter of the chosen element list
    - number of misses

    :raises ValueError: if *n* is larger than the sum of limits

    ###### Examples
    >>> limited_random_choice([1, 2, 3], 2, {1: 1, 2: 1, 3: 2}, seed=20)
    ([3, 3], {3: 2}, 0)
    >>> limited_random_choice(['a', 'b', 'c'], 2, {'a': 3, 'b': 2, 'c': 1},\
                              seed=20)
    (['c', 'a'], {'c': 1, 'a': 1}, 1)
    >>> limited_random_choice([1, 2, 3], 7, {1: 1, 2: 2, 3: 3}, seed=7)
    Traceback (most recent call last):
    ValueError: n cannot be larger than the sum of limits
    """
    if n > sum(limits.values()):
        raise ValueError("n cannot be larger than the sum of limits")
    counter = {}  # type: dict
    result = []
    k = 0
    miss = 0
    if seed:
        random.seed(seed)
    while sum(counter.values()) < n:
        k += 1
        if k == threshold:
            return None
        s = random.choice(a)
        if s not in counter:
            counter[s] = 1
            result.append(s)
        elif counter[s] < limits[s]:
            counter[s] += 1
            result.append(s)
        else:
            miss += 1
            continue

    return result, counter, miss


def to_d2(edgelist: list, horizontal: bool = False) -> str:
    """
    Convert edgelist to D2 diagram.

    :param edgelist: edgelist
    :param horizontal: if True the diagram is positioned horizontally \
        (default False)

    :return: D2 string

    ###### Examples
    >>> print(to_d2([('a', 'b'), ('a', 'd'), ('b', 'c'), ('c', 'f'),\
                     ('d', 'e'), ('e', 'f'), ('e', 'f'), ('f', 'g'),\
                     ('f', 'h')]))
    ... # doctest: +NORMALIZE_WHITESPACE
    a -- b
    a -- d
    b -- c
    c -- f
    d -- e
    e -- f : 2 {style: {font-size: 24; bold: true}}
    f -- g
    f -- h
    <BLANKLINE>
    """
    result = ""
    if horizontal:
        result += "direction: right\n\n"
    for edge, weight in Counter(edgelist).items():
        if weight == 1:
            result += f"{edge[0]} -- {edge[1]}\n"
        else:
            result += f"{edge[0]} -- {edge[1]} : {weight}"
            result += " {style: {font-size: 24; bold: true}}\n"

    return result


def convert_weighted_to_multigraph(g: nx.Graph) -> nx.MultiGraph:
    """
    Convert weighted graph to multigraph.

    :param g: weighted graph
    :return: multigraph

    ###### Example
    >>> g = nx.Graph()
    >>> _ = g.add_edges_from([('a', 'b', {'weight': 2}), \
                              ('a', 'c', {'weight': 1})])
    >>> h = convert_weighted_to_multigraph(g)
    >>> h.degree()
    MultiDegreeView({'a': 3, 'b': 2, 'c': 1})
    >>> dict(h.degree())
    {'a': 3, 'b': 2, 'c': 1}
    """
    edges = []
    for i in g.edges(data=True):
        for _ in range(i[2]["weight"]):
            edges.append((i[0], i[1]))
    new = nx.MultiGraph()
    new.add_edges_from(edges)
    return new


if __name__ == "__main__":
    import argparse
    import sys
    import pathlib

    logging.basicConfig(stream=sys.stdout)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, required=True,
                        help="observed network in (weighted) edgelist format")
    parser.add_argument("-n", "--number-of-networks", type=int, required=False,
                        default=10)
    parser.add_argument("-s", "--seed", type=int, required=False, default=None)
    parser.add_argument("--output", type=str, required=False,
                        default="output/network", help="output directory")
    opts = parser.parse_args()

    h = nx.read_edgelist(opts.input)
    h_ = convert_weighted_to_multigraph(h)
    networks = generate_networks_from_graph(h_, opts.number_of_networks,
                                            seed=opts.seed)

    path = pathlib.Path(opts.output)
    if networks:
        for i, network in enumerate(networks):
            G = convert_to_graph(network)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            nx.write_edgelist(
                G, f"{str(path)}/seed{opts.seed}_{i}.edgelist.gz"
            )
