import os
import sys
import logging
import pandas as pd

logger = logging.getLogger("movement to empty mesh")
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def calculate_trip_length_stream(path: str, output: str) -> None:
    with pd.read_pickle(path, chunksize=1_000_000) as reader:
        for k, chunk in enumerate(reader):
            logger.info(f"heartbeat: {k}")

            temp = chunk.copy()
            temp.to_crs(23700, inplace=True)
            temp["length"] = temp["geometry"].length
            temp.drop("geometry", axis=1, inplace=True)

            # header inspiration: https://stackoverflow.com/a/17975690/4737417
            temp.to_csv(output, index=False, mode="a",
                        header=not os.path.exists(output))


def calculate_trip_length(path: str, output: str) -> None:
    temp = pd.read_pickle(path)
    temp.to_crs(23700, inplace=True)
    temp["length"] = temp["geometry"].length
    temp.drop("geometry", axis=1, inplace=True)

    temp.to_csv(output, index=False)


if __name__ == "__main__":
    calculate_trip_length("../output/trips/network_observed_beeline.pickle.gz", "../output/trip_length_beeline.csv")
