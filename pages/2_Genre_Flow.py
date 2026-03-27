from __future__ import annotations

import streamlit as st
from pages.page_helpers import load_communities_res_10, load_genre_labels_res_10


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

    communities = load_communities_res_10()
    genre_labels = load_genre_labels_res_10()

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
