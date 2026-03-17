from __future__ import annotations

from pathlib import Path
from typing import Iterable, TypedDict

import streamlit.components.v1 as components

_COMPONENT_PATH = Path(__file__).parent / "hotkeys_component"

_hotkeys_component = components.declare_component(
    "hotkeys_component",
    path=str(_COMPONENT_PATH),
)


class HotkeyPayload(TypedDict):
    key: str
    ts: int


def hotkeys(*, keys: Iterable[str], component_key: str) -> HotkeyPayload | None:
    """Capture keyboard shortcuts and return the last pressed key.

    Notes:
        - The returned value can persist across reruns; callers should de-duplicate
          with session_state if they need one-shot behavior.
        - Only keys passed in `keys` will be returned.

    Args:
        keys: Iterable of JS KeyboardEvent.key values (e.g. "ArrowLeft").
        component_key: Streamlit component key.

    Returns:
        A dict like {'key': 'ArrowLeft', 'ts': 1710000000000} or None.
    """

    keys_list = [str(k) for k in keys]

    return _hotkeys_component(keys=keys_list, key=component_key, default=None)  # type: ignore[return-value]
