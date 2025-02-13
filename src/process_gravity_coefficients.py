import pandas as pd


def read_gravityjl_output(filename: str) -> pd.DataFrame:
    m = pd.read_csv(
        filename,
        skiprows=[0, 1, 2, 3, 4, 5, 6, 7],
        skipfooter=1,
        sep="\s+",
        names=["log(mob_ij)", "|", "Estimate", "Std.Error", "t value",
               "Pr(>|t|)", "Lower 95%", "Upper 95%"],
        engine="python"
        )
    m.drop("|", axis=1, inplace=True)
    m.rename({"log(mob_ij)": "coefficient"}, axis=1, inplace=True)
    return m


def prepare_data(
    road1: pd.DataFrame,
    road2: pd.DataFrame,
    railw: pd.DataFrame,
    river: pd.DataFrame,
    distr: pd.DataFrame,
    adm10: pd.DataFrame
) -> pd.DataFrame:
    df = pd.DataFrame()
    df = pd.concat([df, road1.query("coefficient == 'primary_count'")])
    df = pd.concat([df, road2.query("coefficient == 'secondary_count'")])
    df = pd.concat([df, railw.query("coefficient == 'railway_count'")])
    df = pd.concat([df, river.query("coefficient == 'river_count'")])
    df = pd.concat([df, distr.query("coefficient == 'districts_count'")])
    df = pd.concat([df, adm10.query("coefficient == 'neighborhoods_count'")])

    df.reset_index(drop=True, inplace=True)
    df = df[["coefficient", "Estimate", "Lower 95%", "Upper 95%"]].copy()
    df.columns = ["label", "coefficient", "lower", "upper"]
    df["error"] = df["coefficient"]-df["lower"]
    df["label"] = df["label"].apply(lambda x: x.split("_count")[0])
    df.set_index("label", inplace=True)
    df = df.reindex(list(label_lookup.keys()))
    df.reset_index(inplace=True)
    df["label"] = df["label"].map(label_lookup)

    return df


def prepare_total(total: pd.DataFrame) -> pd.DataFrame:
    df = total.copy()
    df["coefficient"] = df["coefficient"].apply(lambda x: x.split("_count")[0])
    df = df[["coefficient", "Estimate", "Lower 95%", "Upper 95%"]].copy()
    df.columns = ["label", "coefficient", "lower", "upper"]
    df["error"] = df["coefficient"] - df["lower"]
    df.drop([0, 1, 2, 9], inplace=True)
    df.set_index("label", inplace=True)
    df = df.reindex(list(label_lookup.keys()))
    df.reset_index(inplace=True)
    df["label"] = df["label"].map(label_lookup)
    return df


def provide_error_interval():
    return [(v["lower"], v["upper"]) for k, v in result.items()]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ols-output-folder",
        type=str,
        required=True,
        help="directory where OLS outputs are",
    )
    parser.add_argument(
        "--models",
        type=str,
        required=False,
        nargs="+",
        default=[
            "model2", "model3", "model4", "model5", "model6", "model7",
            "modelb"
        ],
        help="default model 2-7 and b",
    )
    opts = parser.parse_args()

    label_lookup = {
        "districts": "Districts",
        "neighborhoods": "Neighborhoods",
        "primary": "Primary roads",
        "secondary": "Secondary roads",
        "river": "River",
        "railway": "Railways",
    }

    road1 = read_gravityjl_output(f"{opts.ols_output_folder}/model2.txt")
    road2 = read_gravityjl_output(f"{opts.ols_output_folder}/model3.txt")
    railw = read_gravityjl_output(f"{opts.ols_output_folder}/model4.txt")
    river = read_gravityjl_output(f"{opts.ols_output_folder}/model5.txt")
    distr = read_gravityjl_output(f"{opts.ols_output_folder}/model6.txt")
    adm10 = read_gravityjl_output(f"{opts.ols_output_folder}/model7.txt")
    total = read_gravityjl_output(f"{opts.ols_output_folder}/modelb.txt")

    data_sep = prepare_data(road1, road2, railw, river, distr, adm10)
    data_sep.to_csv(
        f"{opts.ols_output_folder}/coefficients_univariate.csv", index=False)
    data = prepare_total(total)
    data.to_csv(
        f"{opts.ols_output_folder}/coefficients_multivariate.csv", index=False)