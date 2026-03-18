import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import (
    add_word,
    delete_word,
    delete_words,
    append_deleted_words,
    load_words,
    normalize_appear_counts,
    reset_counters,
    rename_word,
    save_words,
)
from src.utils import add_activity_log, clean_word, render_activity_log


st.title("📝 Word Manager")

df = load_words()

st.subheader("Current Words")
st.dataframe(df, use_container_width=True, hide_index=True)


st.divider()
st.subheader("Add a Word")

with st.form("add_word_form", clear_on_submit=True):
    new_word = st.text_input("New word")
    submitted = st.form_submit_button("Add", use_container_width=True)

if submitted:
    df2, added = add_word(df, new_word)
    if added:
        added_word = clean_word(new_word)
        save_words(df2)
        st.success("Word added!")
        add_activity_log(f"Đã thêm từ: {added_word}", level="success")
        st.rerun()
    else:
        st.warning("Word is empty or already exists.")


st.divider()
st.subheader("Edit / Delete")

if len(df) == 0:
    st.info("No words yet.")
    st.stop()

st.markdown("### 🗑️ Bulk delete")
st.caption("Tick the words you want to delete, then click the button.")

bulk_view = df[["word", "count_correct", "count_appear", "count_incorrect"]].copy()
bulk_view.insert(0, "delete", False)

edited = st.data_editor(
    bulk_view,
    hide_index=True,
    use_container_width=True,
    key="bulk_delete_editor",
    column_config={
        "delete": st.column_config.CheckboxColumn(
            "Delete",
            help="Tick to mark this word for deletion",
            default=False,
        )
    },
    disabled=["word", "count_correct", "count_appear", "count_incorrect"],
)

selected_words = (
    edited.loc[edited["delete"] == True, "word"].astype(str).tolist()  # noqa: E712
    if (edited is not None and len(edited) > 0 and "delete" in edited.columns)
    else []
)

confirm_bulk = st.checkbox(
    f"I understand this will delete {len(selected_words)} word(s)",
    value=False,
    key="confirm_bulk_delete",
)

bulk_disabled = (not confirm_bulk) or (len(selected_words) == 0)
if st.button(
    "Delete selected words",
    type="primary",
    use_container_width=True,
    disabled=bulk_disabled,
):
    # Capture current counters for logging/restore before deleting.
    _targets = [clean_word(w) for w in selected_words]
    _targets = [w for w in _targets if w]
    stats_map: dict[str, dict[str, int]] = {}
    if _targets:
        try:
            subset = df[df["word"].isin(_targets)][
                ["word", "count_correct", "count_appear", "count_incorrect"]
            ]
            for r in subset.to_dict("records"):
                w = str(r.get("word", ""))
                if not w:
                    continue
                stats_map[w] = {
                    "count_correct": int(r.get("count_correct", 0)),
                    "count_appear": int(r.get("count_appear", 0)),
                    "count_incorrect": int(r.get("count_incorrect", 0)),
                }
        except Exception:
            stats_map = {}

    df2, deleted_words = delete_words(df, selected_words)
    if deleted_words:
        save_words(df2)
        append_deleted_words(deleted_words, stats=stats_map)
        st.success(f"Deleted {len(deleted_words)} word(s).")
        preview = ", ".join(deleted_words[:20])
        more = "…" if len(deleted_words) > 20 else ""
        add_activity_log(
            f"Đã xóa {len(deleted_words)} từ: {preview}{more}", level="success"
        )
        st.rerun()
    else:
        st.warning("Nothing deleted.")

st.divider()
st.markdown("### ✏️ Single edit / delete")

selected_word = st.selectbox("Select a word", df["word"].tolist())
if selected_word is None:
    st.stop()

with st.form("edit_word_form"):
    new_name = st.text_input("Rename to", value=selected_word) or ""
    col_a, col_b = st.columns(2)
    rename_submit = col_a.form_submit_button("Save rename", use_container_width=True)
    delete_submit = col_b.form_submit_button("Delete word", use_container_width=True)

if rename_submit:
    new_clean = clean_word(new_name)
    old_clean = clean_word(selected_word)
    existed_before = (df["word"] == new_clean).any() and (new_clean != old_clean)
    df2, changed = rename_word(df, selected_word, new_name)
    if changed:
        save_words(df2)
        st.success("Word updated.")
        if existed_before:
            add_activity_log(f"Đã gộp từ: {old_clean} → {new_clean}", level="success")
        else:
            add_activity_log(f"Đã sửa từ: {old_clean} → {new_clean}", level="success")
        st.rerun()
    else:
        st.warning("Nothing changed (check the new name).")

if delete_submit:
    # Capture counters for restore before deleting.
    stats_map: dict[str, dict[str, int]] = {}
    try:
        w0 = clean_word(selected_word)
        row = df.loc[df["word"] == w0].head(1)
        if len(row) > 0:
            r = row.iloc[0].to_dict()
            stats_map[w0] = {
                "count_correct": int(r.get("count_correct", 0)),
                "count_appear": int(r.get("count_appear", 0)),
                "count_incorrect": int(r.get("count_incorrect", 0)),
            }
    except Exception:
        stats_map = {}

    df2, deleted = delete_word(df, selected_word)
    if deleted:
        deleted_word = clean_word(selected_word)
        save_words(df2)
        append_deleted_words([deleted_word], stats=stats_map)
        st.success("Word deleted.")
        add_activity_log(f"Đã xóa từ: {deleted_word}", level="success")
        st.rerun()
    else:
        st.warning("Delete failed.")


st.divider()
st.subheader("Maintenance")
st.caption("Use these tools to clean up stats if they got out of sync.")

if st.button(
    "Normalize appearances (appear = correct + incorrect)", use_container_width=True
):
    df2 = normalize_appear_counts(df)
    save_words(df2)
    st.success("Normalized count_appear.")
    add_activity_log(
        "Đã chuẩn hóa: count_appear = correct + incorrect", level="success"
    )
    st.rerun()

st.divider()
st.subheader("Reset counters")
reset_options = {
    "Correct (count_correct)": "count_correct",
    "Not correct (count_incorrect)": "count_incorrect",
    "Appear (count_appear)": "count_appear",
}

selected_reset = st.multiselect(
    "Choose which counters to reset",
    options=list(reset_options.keys()),
    default=list(reset_options.keys()),
)
reset_cols = [reset_options[k] for k in selected_reset]

confirm_reset = st.checkbox(
    "I understand this will reset the selected counters to 0", value=False
)

if st.button(
    "Reset selected counters",
    use_container_width=True,
    disabled=(not confirm_reset) or (len(reset_cols) == 0),
):
    df2 = reset_counters(df, columns=reset_cols)
    save_words(df2)
    st.success("Selected counters reset to 0.")
    add_activity_log(f"Đã reset bộ đếm về 0: {', '.join(reset_cols)}.", level="warning")
    st.rerun()

# Quick hint for manual cleanup
st.caption(
    f"Tip: words are cleaned to lowercase via clean_word(): '{clean_word('  Example  ')}'"
)

st.divider()
render_activity_log(max_items=30)
