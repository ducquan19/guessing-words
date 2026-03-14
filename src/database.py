from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from pandas.errors import ParserError

from src.utils import clean_word

DATA_PATH = "data/processed/words.csv"
HISTORY_PATH = "data/raw/history.csv"

WORD_COL = "word"
COUNT_CORRECT_COL = "count_correct"
COUNT_APPEAR_COL = "count_appear"
COUNT_INCORRECT_COL = "count_incorrect"

REQUIRED_COLUMNS: list[str] = [
    WORD_COL,
    COUNT_CORRECT_COL,
    COUNT_APPEAR_COL,
    COUNT_INCORRECT_COL,
]

HISTORY_COLUMNS: list[str] = [
    "timestamp_utc",
    "ended_reason",
    "n_words",
    "duration_sec",
    "elapsed_sec",
    "correct",
    "wrong",
    "answered",
    "accuracy",
    "correct_words",
    "wrong_words",
]


def _ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if WORD_COL not in df.columns:
        df[WORD_COL] = ""

    for col in (COUNT_CORRECT_COL, COUNT_APPEAR_COL, COUNT_INCORRECT_COL):
        if col not in df.columns:
            df[col] = 0

    df[WORD_COL] = df[WORD_COL].astype(str).map(clean_word)

    for col in (COUNT_CORRECT_COL, COUNT_APPEAR_COL, COUNT_INCORRECT_COL):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df = df[df[WORD_COL].ne("")]

    # De-duplicate words by summing counts.
    df = (
        df.groupby(WORD_COL, as_index=False)[
            [COUNT_CORRECT_COL, COUNT_APPEAR_COL, COUNT_INCORRECT_COL]
        ]
        .sum()
        .sort_values(WORD_COL)
        .reset_index(drop=True)
    )

    return df


def load_words() -> pd.DataFrame:
    try:
        df = pd.read_csv(DATA_PATH)
        return _ensure_schema(df)
    except ParserError:
        # Fallback for malformed CSV rows where the "word" field contains commas
        # but is not properly quoted. We recover by splitting from the right:
        # word,<count_correct>,<count_appear>,<count_incorrect>
        rows: list[dict[str, object]] = []
        with open(DATA_PATH, "r", encoding="utf-8", newline="") as f:
            reader = f.read().splitlines()

        if not reader:
            return _ensure_schema(pd.DataFrame(columns=REQUIRED_COLUMNS))

        # Skip header if present.
        start_idx = 1 if reader[0].strip().lower().startswith("word,") else 0
        for line in reader[start_idx:]:
            if not line.strip():
                continue

            parts = line.rsplit(",", 3)
            if len(parts) != 4:
                continue

            word_raw, c_correct, c_appear, c_incorrect = parts
            word_raw = word_raw.strip()
            if len(word_raw) >= 2 and word_raw[0] == '"' and word_raw[-1] == '"':
                word_raw = word_raw[1:-1]

            rows.append(
                {
                    WORD_COL: word_raw,
                    COUNT_CORRECT_COL: c_correct,
                    COUNT_APPEAR_COL: c_appear,
                    COUNT_INCORRECT_COL: c_incorrect,
                }
            )

        df = pd.DataFrame(rows)
        return _ensure_schema(df)


def save_words(df: pd.DataFrame) -> None:
    df2 = _ensure_schema(df)
    # Ensure words containing commas are quoted properly.
    df2.to_csv(
        DATA_PATH,
        index=False,
        quoting=csv.QUOTE_MINIMAL,
        escapechar="\\",
    )


def load_history() -> pd.DataFrame:
    """Load score history from data/raw/history.csv.

    Returns an empty dataframe with expected columns if the file is missing/empty.
    """
    path = Path(HISTORY_PATH)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    df = pd.read_csv(path)
    # Ensure columns exist (tolerate older files).
    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[HISTORY_COLUMNS]


def append_history(
    *,
    ended_reason: str,
    n_words: int,
    duration_sec: int,
    elapsed_sec: int,
    correct: int,
    wrong: int,
    correct_words: list[str] | None = None,
    wrong_words: list[str] | None = None,
) -> None:
    """Append one game result row into data/raw/history.csv."""
    path = Path(HISTORY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    correct_words = correct_words or []
    wrong_words = wrong_words or []

    answered = int(correct) + int(wrong)
    accuracy = round((correct / answered) if answered > 0 else 0.0, 4)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ended_reason": str(ended_reason),
        "n_words": int(n_words),
        "duration_sec": int(duration_sec),
        "elapsed_sec": int(elapsed_sec),
        "correct": int(correct),
        "wrong": int(wrong),
        "answered": int(answered),
        "accuracy": float(accuracy),
        "correct_words": "|".join(correct_words),
        "wrong_words": "|".join(wrong_words),
    }

    df = pd.DataFrame([record], columns=HISTORY_COLUMNS)
    write_header = (not path.exists()) or (path.stat().st_size == 0)
    df.to_csv(
        path,
        mode="a",
        header=write_header,
        index=False,
        quoting=csv.QUOTE_MINIMAL,
        escapechar="\\",
    )


def add_word(df: pd.DataFrame, word: str) -> tuple[pd.DataFrame, bool]:
    """Add a word if it doesn't exist. Returns (df, added)."""
    df = _ensure_schema(df)
    w = clean_word(word)
    if not w:
        return df, False
    if (df[WORD_COL] == w).any():
        return df, False

    new_row = pd.DataFrame(
        [
            {
                WORD_COL: w,
                COUNT_CORRECT_COL: 0,
                COUNT_APPEAR_COL: 0,
                COUNT_INCORRECT_COL: 0,
            }
        ]
    )
    return pd.concat([df, new_row], ignore_index=True), True


def rename_word(
    df: pd.DataFrame, old_word: str, new_word: str
) -> tuple[pd.DataFrame, bool]:
    """Rename a word; merges counts if new_word already exists. Returns (df, changed)."""
    df = _ensure_schema(df)
    old_w = clean_word(old_word)
    new_w = clean_word(new_word)
    if not old_w or not new_w or old_w == new_w:
        return df, False

    if not (df[WORD_COL] == old_w).any():
        return df, False

    if (df[WORD_COL] == new_w).any():
        # Merge counts then drop old.
        old_row = df.loc[df[WORD_COL] == old_w].iloc[0]
        df.loc[df[WORD_COL] == new_w, COUNT_CORRECT_COL] += int(
            old_row[COUNT_CORRECT_COL]
        )
        df.loc[df[WORD_COL] == new_w, COUNT_APPEAR_COL] += int(
            old_row[COUNT_APPEAR_COL]
        )
        df.loc[df[WORD_COL] == new_w, COUNT_INCORRECT_COL] += int(
            old_row[COUNT_INCORRECT_COL]
        )
        df = df[df[WORD_COL] != old_w]
    else:
        df.loc[df[WORD_COL] == old_w, WORD_COL] = new_w

    return _ensure_schema(df), True


def delete_word(df: pd.DataFrame, word: str) -> tuple[pd.DataFrame, bool]:
    """Delete a word. Returns (df, deleted)."""
    df = _ensure_schema(df)
    w = clean_word(word)
    if not w:
        return df, False

    before = len(df)
    df = df[df[WORD_COL] != w]
    return _ensure_schema(df), len(df) != before


def normalize_appear_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Set count_appear = count_correct + count_incorrect."""
    df = _ensure_schema(df)
    df[COUNT_APPEAR_COL] = df[COUNT_CORRECT_COL] + df[COUNT_INCORRECT_COL]
    return _ensure_schema(df)


def reset_counters(
    df: pd.DataFrame,
    *,
    word: str | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Reset counters to 0.

    Args:
        df: Words dataframe.
        word: If provided, reset only for this word; otherwise reset for all words.
        columns: Which counter columns to reset. If None, resets all 3 counters.
    """
    df = _ensure_schema(df)

    allowed = {COUNT_CORRECT_COL, COUNT_APPEAR_COL, COUNT_INCORRECT_COL}
    targets = (
        [COUNT_CORRECT_COL, COUNT_APPEAR_COL, COUNT_INCORRECT_COL]
        if not columns
        else [c for c in columns if c in allowed]
    )
    if not targets:
        return df

    if word is None:
        for c in targets:
            df[c] = 0
        return _ensure_schema(df)

    w = clean_word(word)
    mask = df[WORD_COL] == w
    for c in targets:
        df.loc[mask, c] = 0
    return _ensure_schema(df)
