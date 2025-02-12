import pandas as pd
import json
from pathlib import Path

with open("input/lookup_initial_stops.json", "r") as fp:
    lookup = json.load(fp)

inputs = [
    "place_connections_2019-06-01_2019-06-02.csv",
    "place_connections_2019-06-01_2019-06-02_downtown.csv",
    "place_connections_2019-06-08_2019-06-09.csv",
    "place_connections_2019-06-08_2019-06-09_downtown.csv",
    "place_connections_2019-06-15_2019-06-16.csv",
    "place_connections_2019-06-15_2019-06-16_downtown.csv",
    "place_connections_2019-06-22_2019-06-23.csv",
    "place_connections_2019-06-22_2019-06-23_downtown.csv",
    "place_connections_2019-06-29_2019-06-30.csv",
    "place_connections_2019-06-29_2019-06-30_downtown.csv",
    "place_connections_2019-07-06_2019-07-07.csv",
    "place_connections_2019-07-06_2019-07-07_downtown.csv",
    "place_connections_2019-07-13_2019-07-14.csv",
    "place_connections_2019-07-13_2019-07-14_downtown.csv",
    "place_connections_2019-07-20_2019-07-21.csv",
    "place_connections_2019-07-20_2019-07-21_downtown.csv",
    "place_connections_2019-07-27_2019-07-28.csv",
    "place_connections_2019-07-27_2019-07-28_downtown.csv",
    "place_connections_2019-09-01_2020-02-29.csv",
    "place_connections_2020-11-01_2021-04-31.csv",
    "group/place_connections_2019-09-01_2020-02-29_eastern_pest_inner.csv",
    "group/place_connections_2019-09-01_2020-02-29_eastern_pest_outer.csv",
    "group/place_connections_2019-09-01_2020-02-29_south_buda.csv",
    "group/place_connections_2019-09-01_2020-02-29_inner_pest.csv",
    "group/place_connections_2019-09-01_2020-02-29_north_buda.csv",
    "group/place_connections_2019-09-01_2020-02-29_south_pest.csv",
    "group/place_connections_2019-09-01_2020-02-29_north_pest.csv",
    "group/place_connections_2019-09-01_2020-02-29_northern_sector.csv",
    "group/place_connections_2019-09-01_2020-02-29_south_eastern_sector.csv",
    "group/place_connections_2019-09-01_2020-02-29_eastern_sector.csv",
    "group/place_connections_2019-09-01_2020-02-29_southern_sector.csv",
    "group/place_connections_2019-09-01_2020-02-29_western_sector.csv",
    "group/place_connections_2019-09-01_2020-02-29_north_western_sector.csv",
]

Path("data/group/").mkdir(parents=True, exist_ok=True)

for i in inputs:
    print(i)
    data = pd.read_csv(f"input/{i}")
    data["device_id"] = data["device_id"].map(lookup)
    data.to_csv(f"data/{i}", index=False)
