import streamlit as st

st.set_page_config(
    page_title="Word Guess Trainer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎯 Word Guess Training")

st.write("Practice guessing words and track your accuracy over time.")

st.subheader("Quick actions")
col1, col2, col3, col4 = st.columns(4)


def _page_link(path: str, label: str) -> None:
    if hasattr(st, "page_link"):
        st.page_link(path, label=label, use_container_width=True)
    else:
        # Fallback for older Streamlit versions.
        st.write(label)


with col1:
    _page_link("pages/play_game.py", "🎮 Play Game")

with col2:
    _page_link("pages/word_manager.py", "📝 Manage Words")

with col3:
    _page_link("pages/statistics.py", "📊 Statistics")

with col4:
    _page_link("pages/history.py", "📜 History")

st.divider()
