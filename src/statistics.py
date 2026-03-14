import pandas as pd


def compute_statistics(df):

    df = df.copy()
    denom = df["count_appear"].replace(0, 1)
    df["error_rate"] = (df["count_incorrect"] / denom).round(4)

    hardest = df.sort_values(
        ["error_rate", "count_incorrect", "count_appear"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return hardest
