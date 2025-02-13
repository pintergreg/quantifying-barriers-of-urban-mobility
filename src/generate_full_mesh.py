"""Generate empty full mesh for gravity model."""
import geopandas as gpd
import numpy as np
import logging
from haversine import haversine, Unit
from itertools import product


logger = logging.getLogger("full mesh generator")
logger.setLevel(logging.DEBUG)


def prepare_house_blocks(filename: str) -> gpd.GeoDataFrame:
    """
    Load the house block shapefile into a GeoDataFrame, and provides the \
    location data in a tuple (lat, lon) required fo haversine calculation.

    :param filename: the path of the house block GeoJSON
    :return: GeoDataFrame with a point column containing a tuple (lat, lon)
    """
    hb = gpd.read_file(filename)
    hb.to_crs(23700, inplace=True)
    hb["geometry"] = hb.centroid
    hb.to_crs(4326, inplace=True)

    hb["point"] = np.array(zip(hb["geometry"].y, hb["geometry"].x))
    return hb


def generate(output: str, hb: gpd.GeoDataFrame,
             heartbeat: int = 1_000_000) -> None:
    """
    Generate a full mesh network from house blocks and calculate the distance \
    between the block centroids.

    The result is directly written into a file.

    :param output: the path of the output file (CSV)
    :param hb: GeoDataFrame containing the house blocks
    """
    with open(output, "w") as fp:
        print("source,target,distance_ij,p_i,p_j", file=fp)
        temp = hb[["id", "point"]].copy()
        k = 0
        for i, j in product(temp.itertuples(), temp.itertuples()):
            k += 1
            distance = np.round(haversine(i.point, j.point,
                                unit=Unit.KILOMETERS), 3)
            print(f"{i.id},{j.id},{distance},0,0", file=fp)
            if k % heartbeat == 0:
                logger.info(f"heartbeat: {k}")


if __name__ == "__main__":
    from os.path import exists
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--blocks",
        type=str,
        required=False,
        default="data/house_blocks.geojson",
        help="blocks GeoJSON")
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default="output/mesh.csv",
        help="result file")
    opts = parser.parse_args()

    if not exists(opts.output):
        hb = prepare_house_blocks(opts.blocks)
        # runs 24m
        generate(opts.output, hb)
    else:
        logger.info(f"{opts.output} exists, exiting.")
