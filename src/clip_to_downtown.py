import geopandas as gpd
import pandas as pd

downtown = gpd.read_file("../data/downtown.geojson").set_crs(4326).to_crs(23700)
downtown_poly = downtown.geometry[0]
blocks = gpd.read_file("../data/house_blocks.geojson").set_crs(4326).to_crs(23700)

targets = [
    "2019-06-01_2019-06-02",
    "2019-06-08_2019-06-09",
    "2019-06-15_2019-06-16",
    "2019-06-22_2019-06-23",
    "2019-06-29_2019-06-30",
    "2019-07-06_2019-07-07",
    "2019-07-13_2019-07-14",
    "2019-07-20_2019-07-21",
    "2019-07-27_2019-07-28",
]
for target in targets:
    data = pd.read_csv(f"../data/place_connections_{target}.csv")
    in_area = blocks[blocks.geometry.intersects(downtown_poly)].copy()
    data[
        (data["target"].isin(in_area["id"])) & (data["source"].isin(in_area["id"]))
    ].to_csv(f"../data/place_connections_{target}_downtown.csv", index=False)
