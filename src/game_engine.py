import pandas as pd
import numpy as np


def select_words(df, n=10):

    unseen = df[df["count_appear"] == 0]

    if len(unseen) >= n:
        selected = unseen.sample(n)

    else:
        remain = n - len(unseen)

        others = df[df["count_appear"] > 0]

        selected = pd.concat([
            unseen,
            others.sample(remain)
        ])

    return selected.sample(frac=1).reset_index(drop=True)
