from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly via: python tools/smoke_load_words.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import load_words


def main() -> None:
    df = load_words()
    print("shape", df.shape)

    quote_count = int(df["word"].astype(str).str.contains('"', na=False).sum())
    print("words_with_quotes", quote_count)

    if quote_count:
        print(
            df[df["word"].astype(str).str.contains('"', na=False)]
            .head(10)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
