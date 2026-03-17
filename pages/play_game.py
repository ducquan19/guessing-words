import time
from datetime import datetime, timedelta, timezone

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.database import append_history, load_history, load_words, save_words
from src.game_engine import select_words
from src.hotkeys import hotkeys
from src.utils import add_activity_log, render_activity_log

GAME_SECONDS = 120
DEFAULT_N_WORDS = 10


st.title("🎮 Play Game")


def _parse_ts(value: object) -> datetime | None:
    s = "" if value is None else str(value).strip()
    if not s:
        return None
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
    return dt.astimezone(tz7).strftime("%Y-%m-%d %H:%M:%S")


def _get_words_cache() -> tuple[object, dict[str, int]]:
    """Return (df, word_to_row_index) cached in session_state.

    This avoids re-reading and re-parsing the CSV on every rerun (the page
    reruns every second because of st_autorefresh).
    """

    if (
        "_words_df_cache" not in st.session_state
        or st.session_state._words_df_cache is None
    ):
        df0 = load_words()
        st.session_state._words_df_cache = df0
        st.session_state._words_dirty = False

        # load_words() enforces unique words. Build a fast lookup once.
        st.session_state._words_row_index = {
            str(w): int(i) for i, w in enumerate(df0["word"].astype(str).tolist())
        }

    return st.session_state._words_df_cache, st.session_state._words_row_index


def _mark_words_dirty() -> None:
    st.session_state._words_dirty = True


def _flush_words_cache(*, reason: str) -> None:
    """Persist cached words dataframe to CSV if modified."""
    if not st.session_state.get("_words_dirty", False):
        return
    df0 = st.session_state.get("_words_df_cache")
    if df0 is None:
        return

    # Skip expensive schema normalization on every flush; load_words() already
    # guarantees the schema and uniqueness, and in-game updates only increment
    # counters.
    save_words(df0, ensure_schema=False)
    st.session_state._words_dirty = False
    add_activity_log(f"Đã lưu thống kê từ ({reason}).", level="info", toast=False)


def _reset_game_state() -> None:
    for k in (
        "game_words",
        "index",
        "start_time",
        "duration_sec",
        "appear_logged_indices",
        "answered_logged_indices",
        "game_correct",
        "game_wrong",
        "game_correct_words",
        "game_wrong_words",
        "game_id",
    ):
        if k in st.session_state:
            del st.session_state[k]


if "game_words" not in st.session_state:
    st.session_state.game_words = None  # list[str]
    st.session_state.index = 0
    st.session_state.start_time = 0.0
    st.session_state.duration_sec = GAME_SECONDS
    st.session_state.appear_logged_indices = set()
    st.session_state.answered_logged_indices = set()
    st.session_state.game_correct = 0
    st.session_state.game_wrong = 0
    st.session_state.game_correct_words = []
    st.session_state.game_wrong_words = []
    st.session_state.game_id = ""
    st.session_state.game_n_words = DEFAULT_N_WORDS
    st.session_state.game_duration_sec = GAME_SECONDS

if "last_game_result" not in st.session_state:
    st.session_state.last_game_result = None

if "last_history_saved_game_id" not in st.session_state:
    st.session_state.last_history_saved_game_id = ""


# Cache words CSV in session_state to prevent heavy I/O on every autorefresh.
df, _word_to_row = _get_words_cache()

controls_left, controls_right = st.columns([1, 1])

with controls_left:
    start_clicked = st.button("▶️ Start Game", use_container_width=True)

with controls_right:
    reset_clicked = st.button("🔄 Reset", use_container_width=True)

# Settings
st.session_state.setdefault("n_words_setting", DEFAULT_N_WORDS)
st.session_state.setdefault("duration_setting", GAME_SECONDS)
game_active = st.session_state.get("game_words") is not None
st.session_state.n_words_setting = int(
    st.number_input(
        "Số từ mỗi game",
        min_value=1,
        max_value=200,
        value=int(st.session_state.n_words_setting),
        step=1,
        disabled=bool(game_active),
    )
)

st.session_state.duration_setting = int(
    st.number_input(
        "Thời gian (giây)",
        min_value=10,
        max_value=3600,
        value=int(st.session_state.duration_setting),
        step=10,
        disabled=bool(game_active),
    )
)

if reset_clicked:
    add_activity_log("Đã reset game.", level="info")
    _flush_words_cache(reason="reset")
    _reset_game_state()
    st.rerun()

if start_clicked:
    _flush_words_cache(reason="start_new_game")
    # Reload fresh from disk in case other pages updated words.csv.
    if "_words_df_cache" in st.session_state:
        del st.session_state["_words_df_cache"]
    if "_words_row_index" in st.session_state:
        del st.session_state["_words_row_index"]
    df, _word_to_row = _get_words_cache()

    # Fresh start every time Start is pressed.
    n_words = int(st.session_state.get("n_words_setting", DEFAULT_N_WORDS))
    duration_sec = int(st.session_state.get("duration_setting", GAME_SECONDS))
    selected = select_words(df, n_words)
    st.session_state.game_words = selected["word"].tolist()
    st.session_state.game_n_words = int(n_words)
    st.session_state.index = 0
    st.session_state.start_time = time.time()
    st.session_state.duration_sec = duration_sec
    st.session_state.game_duration_sec = duration_sec
    st.session_state.appear_logged_indices = set()
    st.session_state.answered_logged_indices = set()
    st.session_state.game_correct = 0
    st.session_state.game_wrong = 0
    st.session_state.game_correct_words = []
    st.session_state.game_wrong_words = []
    st.session_state.game_id = str(int(time.time() * 1000))
    add_activity_log(f"Bắt đầu game: {n_words} từ — {duration_sec}s.", level="info")
    st.rerun()


game_words = st.session_state.game_words
if game_words is None:
    last = st.session_state.get("last_game_result")
    if last:
        st.subheader("🏁 Last game")
        c1, c2, c3, c4 = st.columns(4)
        correct_v = int(last.get("correct", 0))
        wrong_v = int(last.get("wrong", 0))
        answered_v = int(last.get("answered", 0))
        total_v = int(last.get("n_words", answered_v))

        c1.metric("Score", f"{correct_v}/{total_v}")
        c2.metric("✅ Correct", correct_v)
        c3.metric("❌ Wrong", wrong_v)
        c4.metric("Accuracy", f"{float(last.get('accuracy', 0.0)) * 100:.1f}%")

        st.caption(f"Time: {int(last.get('elapsed_sec', 0))}s")

        cc, ww = st.columns(2)
        with cc:
            st.markdown("### ✅ Correct words")
            correct_words = list(last.get("correct_words", []) or [])
            if correct_words:
                st.write(correct_words)
            else:
                st.caption("(none)")

        with ww:
            st.markdown("### ❌ Wrong words")
            wrong_words = list(last.get("wrong_words", []) or [])
            if wrong_words:
                st.write(wrong_words)
            else:
                st.caption("(none)")

        st.divider()
        st.markdown("### 📜 Score history")
        hist = load_history()
        if len(hist) == 0:
            st.caption("No games recorded yet.")
        else:
            hist2 = hist.copy()
            hist2["_ts"] = hist2["timestamp_utc"].map(_parse_ts)
            hist2 = hist2.sort_values("_ts", ascending=False, na_position="last")

            # Display a compact, readable table.
            view_cols = [
                "timestamp_utc",
                "n_words",
                "correct",
                "wrong",
                "accuracy",
                "elapsed_sec",
            ]
            view = hist2[[c for c in view_cols if c in hist2.columns]].head(50)
            view = view.copy()
            if "timestamp_utc" in view.columns:
                view["timestamp_utc"] = view["timestamp_utc"].map(_fmt_ts_gmt7)
            st.dataframe(view, use_container_width=True, hide_index=True)

        st.divider()

    st.info("Press **Start Game** to begin.")
    st.stop()

start_time: float
try:
    start_time = float(st.session_state.start_time)
except Exception:
    start_time = time.time()
    st.session_state.start_time = start_time


# Real-time timer: rerun every second while game is active.
st_autorefresh(interval=1000, key="game_timer_tick")

elapsed = time.time() - float(start_time)
remaining = int(max(0, st.session_state.duration_sec - elapsed))

timer_left, timer_right = st.columns([2, 1])
with timer_left:
    st.progress(remaining / st.session_state.duration_sec)
with timer_right:
    st.metric("⏱ Time left", f"{remaining} s")

if remaining <= 0:
    st.error("Time up!")

    _flush_words_cache(reason="time_up")

    correct = int(st.session_state.get("game_correct", 0))
    wrong = int(st.session_state.get("game_wrong", 0))
    elapsed_sec = int(min(st.session_state.duration_sec, elapsed))
    answered = correct + wrong
    accuracy = (correct / answered) if answered > 0 else 0.0

    expected_n_words = int(st.session_state.get("game_n_words", len(game_words)))

    st.session_state.last_game_result = {
        "ended_reason": "time_up",
        "n_words": expected_n_words,
        "duration_sec": int(st.session_state.duration_sec),
        "correct": correct,
        "wrong": wrong,
        "answered": answered,
        "accuracy": accuracy,
        "elapsed_sec": elapsed_sec,
        "correct_words": list(st.session_state.get("game_correct_words", [])),
        "wrong_words": list(st.session_state.get("game_wrong_words", [])),
    }

    add_activity_log(
        f"Hết giờ! Kết quả: đúng={correct}, sai={wrong}.",
        level="warning",
    )

    # Do NOT persist time-up games into history (only completed games).

    _reset_game_state()
    st.rerun()


i = int(st.session_state.index)
if i >= len(game_words):
    st.success("Game Finished!")

    _flush_words_cache(reason="finished")

    correct = int(st.session_state.get("game_correct", 0))
    wrong = int(st.session_state.get("game_wrong", 0))
    elapsed_sec = int(min(st.session_state.duration_sec, elapsed))
    answered = correct + wrong
    accuracy = (correct / answered) if answered > 0 else 0.0

    expected_n_words = int(st.session_state.get("game_n_words", len(game_words)))

    st.session_state.last_game_result = {
        "ended_reason": "finished",
        "n_words": expected_n_words,
        "duration_sec": int(st.session_state.duration_sec),
        "correct": correct,
        "wrong": wrong,
        "answered": answered,
        "accuracy": accuracy,
        "elapsed_sec": elapsed_sec,
        "correct_words": list(st.session_state.get("game_correct_words", [])),
        "wrong_words": list(st.session_state.get("game_wrong_words", [])),
    }

    add_activity_log(
        f"Hoàn thành game! Kết quả: đúng={correct}, sai={wrong}.",
        level="success",
    )

    # Only save games that fully completed the configured word count.
    if (
        answered == int(expected_n_words)
        and len(game_words) == int(expected_n_words)
        and st.session_state.get("last_history_saved_game_id")
        != st.session_state.get("game_id")
    ):
        append_history(
            n_words=len(game_words),
            duration_sec=int(st.session_state.duration_sec),
            elapsed_sec=elapsed_sec,
            correct=correct,
            wrong=wrong,
            correct_words=list(st.session_state.get("game_correct_words", [])),
            wrong_words=list(st.session_state.get("game_wrong_words", [])),
        )
        st.session_state.last_history_saved_game_id = st.session_state.get("game_id")

    _reset_game_state()
    st.rerun()


current_word = game_words[i]


def _inc_counter(df, word: str, col: str) -> None:
    # Fast O(1) update using the cached word->row mapping.
    row_i = _word_to_row.get(str(word))
    if row_i is None:
        return
    df.at[row_i, col] = int(df.at[row_i, col]) + 1
    _mark_words_dirty()


# Count appearance once per index (prevents inflation caused by reruns/autorefresh).
if i not in st.session_state.appear_logged_indices:
    _inc_counter(df, current_word, "count_appear")
    st.session_state.appear_logged_indices.add(i)


st.caption(f"Progress: {i + 1}/{len(game_words)}")
st.header(current_word)

st.caption("Hotkeys: ← đúng • → sai")

btn1, btn2 = st.columns(2)

with btn1:
    correct_clicked = st.button(
        "✅ Correct", use_container_width=True, key=f"correct_{i}"
    )
with btn2:
    wrong_clicked = st.button(
        "❌ Not correct", use_container_width=True, key=f"wrong_{i}"
    )


def _handle_answer(*, is_correct: bool) -> None:
    # Guard against rare double-processing due to reruns/autorefresh: each index can
    # only be answered once.
    if i in st.session_state.get("answered_logged_indices", set()):
        st.session_state.index = max(int(st.session_state.get("index", i)), i + 1)
        st.rerun()

    if is_correct:
        _inc_counter(df, current_word, "count_correct")
        st.session_state.game_correct = int(st.session_state.get("game_correct", 0)) + 1
        st.session_state.game_correct_words = list(
            st.session_state.get("game_correct_words", [])
        ) + [current_word]
    else:
        _inc_counter(df, current_word, "count_incorrect")
        st.session_state.game_wrong = int(st.session_state.get("game_wrong", 0)) + 1
        st.session_state.game_wrong_words = list(
            st.session_state.get("game_wrong_words", [])
        ) + [current_word]

    st.session_state.answered_logged_indices.add(i)
    st.session_state.index = i + 1
    st.rerun()


if correct_clicked:
    _handle_answer(is_correct=True)

if wrong_clicked:
    _handle_answer(is_correct=False)


# Keyboard shortcuts (ArrowLeft=correct, ArrowRight=wrong).
payload = hotkeys(keys=["ArrowLeft", "ArrowRight"], component_key="game_hotkeys")
if payload and isinstance(payload, dict):
    key_name = str(payload.get("key", ""))
    ts = payload.get("ts")

    # One-shot per timestamp to avoid repeated triggers on autorefresh.
    last_ts = st.session_state.get("_last_hotkey_ts")
    if ts is not None and ts != last_ts:
        st.session_state["_last_hotkey_ts"] = ts
        add_activity_log(f"Hotkey: {key_name}", level="info", toast=False)
        if key_name == "ArrowLeft":
            _handle_answer(is_correct=True)
        elif key_name == "ArrowRight":
            _handle_answer(is_correct=False)


st.divider()
render_activity_log(max_items=20)
