import streamlit as st

from src.database import load_history
from src.utils import add_activity_log


st.title("📜 History")

with st.expander("⚠️ Danger zone", expanded=False):
    confirm_clear = st.checkbox(
        "I understand this will delete all history", value=False
    )
    if st.button(
        "Clear history",
        type="primary",
        use_container_width=True,
        disabled=not confirm_clear,
    ):
        # Truncate the file; load_history() treats empty as no history.
        try:
            with open("data/raw/history.csv", "w", encoding="utf-8", newline=""):
                pass
            add_activity_log("Đã xóa lịch sử điểm (history.csv).", level="warning")
            st.success("History cleared.")
        except Exception as e:
            st.error(f"Failed to clear history: {e}")
        st.rerun()

history = load_history()

if len(history) == 0:
    st.info("No games recorded yet. Play a game to generate history.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Games", int(len(history)))

try:
    col2.metric(
        "Avg accuracy", f"{float(history['accuracy'].astype(float).mean()) * 100:.1f}%"
    )
except Exception:
    col2.metric("Avg accuracy", "—")

try:
    col3.metric(
        "Last accuracy", f"{float(history.tail(1)['accuracy'].iloc[0]) * 100:.1f}%"
    )
except Exception:
    col3.metric("Last accuracy", "—")

st.subheader("Results")
st.dataframe(history.tail(200), use_container_width=True, hide_index=True)

st.subheader("Accuracy over time")
try:
    chart_df = history.copy()
    chart_df["timestamp_utc"] = chart_df["timestamp_utc"].astype(str)
    st.line_chart(chart_df.set_index("timestamp_utc")["accuracy"])
except Exception:
    st.caption("Chart unavailable for current history format.")
