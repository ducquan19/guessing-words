import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import delete_history_row, load_history
from src.utils import add_activity_log

from datetime import datetime, timedelta, timezone


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

history = load_history(include_row_id=True)

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


def _split_words(value: object) -> list[str]:
    s = "" if value is None else str(value)
    if not s.strip():
        return []
    return [w for w in s.split("|") if w]


def _parse_ts(value: object) -> datetime | None:
    s = "" if value is None else str(value).strip()
    if not s:
        return None
    # Handle common 'Z' suffix.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _fmt_ts_gmt7(value: object) -> str:
    dt = _parse_ts(value)
    if dt is None:
        return "" if value is None else str(value)
    tz7 = timezone(timedelta(hours=7))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt7 = dt.astimezone(tz7)
    return dt7.strftime("%Y-%m-%d %H:%M:%S")


history2 = history.copy()
history2["_ts"] = history2["timestamp_utc"].map(_parse_ts)
sorted_history = history2.sort_values("_ts", ascending=False, na_position="last")

tail = sorted_history.head(200).reset_index(drop=True)
table_view = tail.drop(
    columns=["correct_words", "wrong_words", "ended_reason", "_row_id", "_ts"],
    errors="ignore",
)
# Show local time (GMT+7)
if "timestamp_utc" in table_view.columns:
    table_view = table_view.copy()
    table_view["timestamp_utc"] = table_view["timestamp_utc"].map(_fmt_ts_gmt7)
st.dataframe(table_view, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Game details")


def _label(idx: int) -> str:
    try:
        row = tail.iloc[int(idx)]
        ts = _fmt_ts_gmt7(row.get("timestamp_utc", ""))
        acc = row.get("accuracy", "")
        try:
            acc_s = f"{float(acc) * 100:.1f}%"
        except Exception:
            acc_s = str(acc)
        correct = row.get("correct", "")
        n_words = row.get("n_words", "")
        return f"{ts} • score {correct}/{n_words} • acc {acc_s}"
    except Exception:
        return str(idx)


selected_idx = st.selectbox(
    "Chọn 1 game để xem từ đúng/sai",
    options=list(range(len(tail))),
    format_func=_label,
    index=0,
)

row = tail.iloc[int(selected_idx)]
correct_words = _split_words(row.get("correct_words", ""))
wrong_words = _split_words(row.get("wrong_words", ""))

st.divider()
st.subheader("Delete one game")
confirm_delete = st.checkbox(
    "I understand this will delete the selected game from history",
    value=False,
)
selected_row_id = row.get("_row_id")
delete_disabled = (not confirm_delete) or (selected_row_id is None)
if st.button(
    "Delete selected game",
    type="primary",
    use_container_width=True,
    disabled=delete_disabled,
):
    try:
        ok = delete_history_row(row_id=int(selected_row_id))
    except Exception:
        ok = False

    if ok:
        add_activity_log("Đã xóa 1 game khỏi lịch sử.", level="warning")
        st.success("Deleted.")
    else:
        st.error("Delete failed.")
    st.rerun()

c1, c2 = st.columns(2)
with c1:
    st.markdown("### ✅ Correct")
    if correct_words:
        st.write(correct_words)
    else:
        st.caption("(none)")

with c2:
    st.markdown("### ❌ Not correct")
    if wrong_words:
        st.write(wrong_words)
    else:
        st.caption("(none)")

st.subheader("Accuracy over time")
try:
    chart_df = history.copy()
    chart_df["timestamp_utc"] = chart_df["timestamp_utc"].astype(str)
    st.line_chart(chart_df.set_index("timestamp_utc")["accuracy"])
except Exception:
    st.caption("Chart unavailable for current history format.")
