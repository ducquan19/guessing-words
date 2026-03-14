import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.database import append_history, load_history, load_words, save_words
from src.game_engine import select_words
from src.utils import add_activity_log, render_activity_log

GAME_SECONDS = 120
N_WORDS = 10


st.title("🎮 Play Game")


def _reset_game_state() -> None:
    for k in (
        "game_words",
        "index",
        "start_time",
        "duration_sec",
        "appear_logged_indices",
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
    st.session_state.game_correct = 0
    st.session_state.game_wrong = 0
    st.session_state.game_correct_words = []
    st.session_state.game_wrong_words = []
    st.session_state.game_id = ""

if "last_game_result" not in st.session_state:
    st.session_state.last_game_result = None

if "last_history_saved_game_id" not in st.session_state:
    st.session_state.last_history_saved_game_id = ""


df = load_words()

controls_left, controls_right = st.columns([1, 1])

with controls_left:
    start_clicked = st.button("▶️ Start Game", use_container_width=True)

with controls_right:
    reset_clicked = st.button("🔄 Reset", use_container_width=True)

if reset_clicked:
    add_activity_log("Đã reset game.", level="info")
    _reset_game_state()
    st.rerun()

if start_clicked:
    # Fresh start every time Start is pressed.
    selected = select_words(df, N_WORDS)
    st.session_state.game_words = selected["word"].tolist()
    st.session_state.index = 0
    st.session_state.start_time = time.time()
    st.session_state.duration_sec = GAME_SECONDS
    st.session_state.appear_logged_indices = set()
    st.session_state.game_correct = 0
    st.session_state.game_wrong = 0
    st.session_state.game_correct_words = []
    st.session_state.game_wrong_words = []
    st.session_state.game_id = str(int(time.time() * 1000))
    add_activity_log(f"Bắt đầu game: {N_WORDS} từ — {GAME_SECONDS}s.", level="info")
    st.rerun()


game_words = st.session_state.game_words
if game_words is None:
    last = st.session_state.get("last_game_result")
    if last:
        st.subheader("🏁 Last game")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Correct", int(last.get("correct", 0)))
        c2.metric("Wrong", int(last.get("wrong", 0)))
        c3.metric("Answered", int(last.get("answered", 0)))
        c4.metric("Accuracy", f"{float(last.get('accuracy', 0.0)) * 100:.1f}%")

        st.caption(
            f"Ended: {last.get('ended_reason', '')} • {last.get('elapsed_sec', 0)}s"
        )

        tabs = st.tabs(["✅ Correct words", "❌ Wrong words", "📜 Score history"])
        with tabs[0]:
            st.write(last.get("correct_words", []) or [])
        with tabs[1]:
            st.write(last.get("wrong_words", []) or [])
        with tabs[2]:
            hist = load_history()
            st.dataframe(hist.tail(50), use_container_width=True, hide_index=True)

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

    correct = int(st.session_state.get("game_correct", 0))
    wrong = int(st.session_state.get("game_wrong", 0))
    elapsed_sec = int(min(st.session_state.duration_sec, elapsed))
    answered = correct + wrong
    accuracy = (correct / answered) if answered > 0 else 0.0

    st.session_state.last_game_result = {
        "ended_reason": "time_up",
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

    if st.session_state.get("last_history_saved_game_id") != st.session_state.get(
        "game_id"
    ):
        append_history(
            ended_reason="time_up",
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


i = int(st.session_state.index)
if i >= len(game_words):
    st.success("Game Finished!")

    correct = int(st.session_state.get("game_correct", 0))
    wrong = int(st.session_state.get("game_wrong", 0))
    elapsed_sec = int(min(st.session_state.duration_sec, elapsed))
    answered = correct + wrong
    accuracy = (correct / answered) if answered > 0 else 0.0

    st.session_state.last_game_result = {
        "ended_reason": "finished",
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

    if st.session_state.get("last_history_saved_game_id") != st.session_state.get(
        "game_id"
    ):
        append_history(
            ended_reason="finished",
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
    idx = df.index[df["word"] == word]
    if len(idx) == 0:
        return
    row_i = idx[0]
    df.at[row_i, col] = int(df.at[row_i, col]) + 1


# Count appearance once per index (prevents inflation caused by reruns/autorefresh).
if i not in st.session_state.appear_logged_indices:
    _inc_counter(df, current_word, "count_appear")
    save_words(df)
    st.session_state.appear_logged_indices.add(i)


st.caption(f"Progress: {i + 1}/{len(game_words)}")
st.header(current_word)

btn1, btn2 = st.columns(2)

with btn1:
    correct_clicked = st.button(
        "✅ Correct", use_container_width=True, key=f"correct_{i}"
    )
with btn2:
    wrong_clicked = st.button(
        "❌ Not correct", use_container_width=True, key=f"wrong_{i}"
    )

if correct_clicked or wrong_clicked:
    # Reload to avoid any stale in-memory df in case of concurrent edits.
    df = load_words()
    if correct_clicked:
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

    save_words(df)
    st.session_state.index = i + 1
    st.rerun()


st.divider()
render_activity_log(max_items=20)
