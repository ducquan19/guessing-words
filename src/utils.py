from __future__ import annotations

import time
from typing import Literal

import streamlit as st


def clean_word(word: str) -> str:
    """
    Clean a word by stripping whitespace and converting to lowercase.
    Args:        word (str): The word to clean.
    Returns:        str: The cleaned word.
    """
    return word.strip().lower()


LogLevel = Literal["info", "success", "warning", "error"]


def init_activity_log() -> None:
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []


def add_activity_log(
    message: str, level: LogLevel = "info", *, toast: bool = True
) -> None:
    init_activity_log()

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.activity_log.append({"ts": ts, "level": level, "message": message})

    # Keep it bounded.
    if len(st.session_state.activity_log) > 200:
        st.session_state.activity_log = st.session_state.activity_log[-200:]

    if toast and hasattr(st, "toast"):
        # Streamlit toast is non-blocking and survives reruns nicely.
        st.toast(message)


def render_activity_log(*, title: str = "🧾 Activity log", max_items: int = 20) -> None:
    init_activity_log()
    items = list(st.session_state.activity_log)[-max_items:]

    with st.expander(title, expanded=False):
        if not items:
            st.caption("No activity yet.")
            return

        for it in reversed(items):
            level = it.get("level", "info")
            prefix = {
                "success": "✅",
                "warning": "⚠️",
                "error": "🛑",
                "info": "ℹ️",
            }.get(level, "ℹ️")
            st.write(f"{prefix} {it.get('ts', '')} — {it.get('message', '')}")
