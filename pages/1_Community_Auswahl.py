"""Zusammengefuehrte Community-Auswahl mit Suchfeld und Kategorie-Expandern."""

from __future__ import annotations

from typing import Any

import streamlit as st
from pages.page_helpers import (
    load_broad_categories_res_10,
    load_communities_res_10,
    load_genre_labels_res_10,
    render_toolbar,
)


def _ensure_session_state() -> None:
    if "selected_communities" not in st.session_state:
        st.session_state["selected_communities"] = set()
    if "selected_broad_categories" not in st.session_state:
        st.session_state["selected_broad_categories"] = set()


def _community_matches_search(
    query: str,
    genre_label: str,
    top_artists: list[str],
) -> bool:
    """Check if a community matches the search query (case-insensitive)."""
    q = query.lower()
    if q in genre_label.lower():
        return True
    return any(q in a.lower() for a in top_artists)


def _build_community_index(
    communities: list[dict[str, Any]],
    genre_labels: dict[str, str],
    category_mappings: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Group communities by broad category.

    Returns {category_name: [community_info_dicts]}.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for comm in communities:
        cid = str(comm.get("id", ""))
        if not cid:
            continue
        genre_label = genre_labels.get(cid, str(comm.get("centroid", cid)))
        top_artists = comm.get("top_artists") or []
        if not isinstance(top_artists, list):
            top_artists = []
        size = int(comm.get("size", 0))
        cats = category_mappings.get(cid, [])
        info = {
            "id": cid,
            "genre_label": genre_label,
            "top_artists": [str(a) for a in top_artists[:3]],
            "size": size,
        }
        if not cats:
            cats = ["Sonstige"]
        for cat in cats:
            index.setdefault(cat, []).append(info)
    for items in index.values():
        items.sort(key=lambda x: x["genre_label"].lower())
    return index


def _render_community_list(
    category: str,
    items: list[dict[str, Any]],
    search_query: str,
    selected: set[str],
    rendered_ids: set[str],
) -> set[str]:
    """Render communities within one category expander. Returns updated set.

    Communities already in *rendered_ids* are skipped (they appeared in
    a previous category due to overlapping broad-category mappings).
    """
    visible = [
        item
        for item in items
        if item["id"] not in rendered_ids
        and (
            not search_query
            or _community_matches_search(
                search_query,
                item["genre_label"],
                item["top_artists"],
            )
        )
    ]
    if not visible:
        return selected

    with st.expander(
        f"{category} ({len(visible)} Communities)",
        expanded=False,
    ):
        for item in visible:
            cid = item["id"]
            rendered_ids.add(cid)
            artists_str = ", ".join(item["top_artists"])
            label = f"**{item['genre_label']}** -- {artists_str} (n={item['size']})"
            key = f"comm_sel_{cid}"
            checked = st.checkbox(
                label,
                key=key,
                value=(cid in selected),
            )
            if checked:
                selected.add(cid)
            else:
                selected.discard(cid)
    return selected


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar -- Communities",
        page_icon=None,
        layout="wide",
    )

    _ensure_session_state()
    render_toolbar("community_auswahl")

    st.title("Communities auswählen")
    st.markdown(
        "Wähle die Communities aus, die deinem Musikgeschmack entsprechen. "
        "Jede Community steht für eine Gruppe verwandter Künstler.",
    )

    search_query = st.text_input(
        "Suche nach Genre, Künstler oder Stimmung",
        value="",
        placeholder='z.B. "Shoegaze", "Radiohead", "melancholisch"',
        key="community_search",
    )

    communities = load_communities_res_10()
    genre_labels = load_genre_labels_res_10()
    _broad_cats, category_mappings = load_broad_categories_res_10()

    if not communities:
        st.warning(
            "Keine Communities gefunden. Bitte zuerst "
            "`hatch run graph-build -- --export-communities 10` ausführen.",
        )
    else:
        selected_broad = st.session_state.get(
            "selected_broad_categories",
            set(),
        )
        community_index = _build_community_index(
            communities,
            genre_labels,
            category_mappings,
        )

        selected: set[str] = set(
            st.session_state["selected_communities"],
        )

        if selected_broad:
            active_cats = sorted(
                cat for cat in community_index if cat in selected_broad
            )
        else:
            active_cats = sorted(community_index.keys())

        rendered_ids: set[str] = set()
        for cat in active_cats:
            items = community_index.get(cat, [])
            selected = _render_community_list(
                cat,
                items,
                search_query,
                selected,
                rendered_ids,
            )

        st.session_state["selected_communities"] = selected

        if selected:
            st.success(
                f"**{len(selected)} Communities ausgewählt:** "
                + ", ".join(sorted(selected)),
            )
        else:
            st.info("Noch keine Communities ausgewählt.")

    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("Zurück zu den Kategorien"):
            st.switch_page("pages/0b_Einstieg.py")
    with col_next:
        if st.button("Weiter", type="primary"):
            st.switch_page("pages/5_Filter_Flow.py")


if __name__ == "__main__":
    main()
