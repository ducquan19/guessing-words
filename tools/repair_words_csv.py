from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly via: python tools/repair_words_csv.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import load_words, save_words


def main() -> None:
    df = load_words()
    save_words(df)
    print(f"Rewrote {Path('data/processed/words.csv')} with {len(df)} words")


if __name__ == "__main__":
    main()
