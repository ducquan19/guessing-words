import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import load_history, load_words
from src.statistics import compute_statistics


st.title("📊 Statistics")

df = load_words()

stats = compute_statistics(df)

total_words = len(df)
total_appear = int(df["count_appear"].sum())
total_correct = int(df["count_correct"].sum())
total_incorrect = int(df["count_incorrect"].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Words", total_words)
col2.metric("Appearances", total_appear)
col3.metric("Correct", total_correct)
col4.metric("Not correct", total_incorrect)

st.subheader("Hardest Words")
top_n = st.slider("Show top N", min_value=10, max_value=200, value=30, step=10)
st.dataframe(stats.head(top_n), use_container_width=True, hide_index=True)


st.divider()
st.subheader("Score history")

history = load_history()
if len(history) == 0:
    st.caption("No games recorded yet. Play a game to generate history.")
else:
    st.dataframe(history.tail(100), use_container_width=True, hide_index=True)

    # Basic trend: accuracy over time.
    try:
        chart_df = history.copy()
        chart_df["timestamp_utc"] = chart_df["timestamp_utc"].astype(str)
        st.line_chart(chart_df.set_index("timestamp_utc")["accuracy"])
    except Exception:
        pass
