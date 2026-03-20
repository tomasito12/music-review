from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import resolve_data_path


@st.cache_data(ttl=3600)
def _load_communities_res_10() -> list[dict[str, Any]]:
    """Load resolution-10 communities."""
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


@st.cache_data(ttl=3600)
def _load_genre_labels_res_10() -> dict[str, str]:
    """Load LLM-basiert vergebene Genre-Labels für Communities (res_10)."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "community_genre_labels_res_10.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    labels = data.get("labels")
    if not isinstance(labels, list):
        return {}
    mapping: dict[str, str] = {}
    for item in labels:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        label = item.get("genre_label")
        if cid is None or not label:
            continue
        mapping[str(cid)] = str(label)
    return mapping


def _ensure_session_state() -> None:
    if "genre_flow_selected_communities" not in st.session_state:
        st.session_state["genre_flow_selected_communities"] = set()


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Genre/Mood Flow",
        page_icon="🎵",
        layout="wide",
    )

    _ensure_session_state()

    st.title("🎼 Genre- / Mood-basierter Empfehlungs-Flow")
    st.markdown(
        "Wähle hier Communities über ihre Genre-/Mood-Labels. "
        "Die Auswahl der Community-IDs wird im Session State gespeichert und kann "
        "in späteren Schritten mit RAG und weiteren Filtern kombiniert werden.",
    )

    communities = _load_communities_res_10()
    genre_labels = _load_genre_labels_res_10()

    if not communities:
        st.warning(
            "Keine Communities für Auflösung 10 gefunden. Bitte zuerst den "
            "Graph-Build-Pipeline-Lauf ausführen "
            '(z. B. `hatch run graph-build -- --export-communities "10"`).',
        )
    else:
        # Communities nach Genre-Label sortieren; wenn kein Label vorhanden,
        # Fallback auf Centroid-/ID-Namen.
        labeled_comms: list[tuple[str, str, int]] = []
        for c in communities:
            cid = str(c.get("id"))
            size = int(c.get("size", 0))
            label = genre_labels.get(cid) or str(c.get("centroid") or cid)
            labeled_comms.append((cid, label, size))

        labeled_comms.sort(key=lambda x: x[1].lower())

        st.subheader("Communities nach Genre-/Mood-Label (klickbar)")
        st.caption(
            "Klicke auf Communities mit passenden Genre-/Mood-Beschreibungen. "
            "Die Auswahl bleibt im aktuellen Browser-Tab bestehen.",
        )

        num_cols = 4
        cols = st.columns(num_cols)
        selected: set[str] = set(
            st.session_state["genre_flow_selected_communities"],
        )

        for idx, (cid, label, size) in enumerate(labeled_comms):
            col = cols[idx % num_cols]
            key = f"genre_flow_comm_{cid}"
            display = f"{label} (ID {cid}, n={size})"
            with col:
                checked = st.checkbox(display, key=key, value=(cid in selected))
            if checked:
                selected.add(cid)
            else:
                selected.discard(cid)

        st.session_state["genre_flow_selected_communities"] = selected

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
            st.switch_page("pages/5_Filter_Flow.py")


if __name__ == "__main__":
    main()
