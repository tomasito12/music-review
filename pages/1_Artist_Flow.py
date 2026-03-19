from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import resolve_data_path


@st.cache_data(ttl=3600)
def _load_communities_res_10() -> list[dict[str, Any]]:
    """Load resolution-10 communities with top artists."""
    data_dir = resolve_data_path("data")
    res_name = "10"
    path = Path(data_dir) / f"communities_res_{res_name}.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    comms = data.get("communities")
    if not isinstance(comms, list):
        return []
    return [c for c in comms if isinstance(c, dict) and c.get("id")]


def _ensure_session_state() -> None:
    if "artist_flow_selected_communities" not in st.session_state:
        st.session_state["artist_flow_selected_communities"] = set()


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Artist Flow",
        page_icon="🎵",
        layout="wide",
    )

    _ensure_session_state()

    st.title("🎤 Artist-basierter Empfehlungs-Flow")
    st.markdown(
        "Wähle hier Communities auf Basis ihrer repräsentativen Artists. "
        "Die Auswahl der Community-IDs wird im Session State gespeichert "
        "und kann in späteren Schritten für Empfehlungen weiterverwendet werden.",
    )

    communities = _load_communities_res_10()
    if not communities:
        st.warning(
            "Keine Communities für Auflösung 10 gefunden. Bitte zuerst den "
            "Graph-Build-Pipeline-Lauf ausführen "
            '(z. B. `hatch run graph-build -- --export-communities "10"`).',
        )
    else:
        st.subheader("Communities nach Top-Artists (klickbar)")
        st.caption(
            "Klicke auf Communities, die deinem Geschmack entsprechen. "
            "Die Auswahl bleibt im aktuellen Browser-Tab bestehen.",
        )

        num_cols = 4
        cols = st.columns(num_cols)
        selected: set[str] = set(
            st.session_state["artist_flow_selected_communities"],
        )

        for idx, c in enumerate(communities):
            cid = str(c.get("id"))
            size = int(c.get("size", 0))
            top_artists = c.get("top_artists") or []
            if not isinstance(top_artists, list):
                top_artists = []
            top_artists_str = ", ".join(str(a) for a in top_artists[:3])

            col = cols[idx % num_cols]
            key = f"artist_flow_comm_{cid}"
            label = f"{cid}: {top_artists_str} (n={size})"
            with col:
                checked = st.checkbox(label, key=key, value=(cid in selected))
            if checked:
                selected.add(cid)
            else:
                selected.discard(cid)

        st.session_state["artist_flow_selected_communities"] = selected

        if selected:
            st.markdown(
                f"**Aktuell gewählte Communities ({len(selected)}):** "
                + ", ".join(sorted(selected)),
            )
        else:
            st.info("Noch keine Communities ausgewählt.")

    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("Zur Startseite"):
            st.switch_page("streamlit_app.py")
    with col_next:
        if st.button("Weiter"):
            mode = st.session_state.get("flow_mode")
            if mode == "combined":
                st.switch_page("pages/2_Genre_Flow.py")
            else:
                st.switch_page("pages/4_Text_Flow.py")


if __name__ == "__main__":
    main()
