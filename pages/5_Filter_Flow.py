from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
    RECOMMENDATION_OVERALL_ALPHA,
    RECOMMENDATION_OVERALL_BETA,
    RECOMMENDATION_OVERALL_GAMMA,
    normalize_overall_weights,
    resolve_data_path,
)


@st.cache_data(ttl=3600)
def _load_communities_res_10() -> list[dict[str, Any]]:
    """Load resolution-10 communities for display."""
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
    """Load LLM genre/mood labels for communities (res_10) for nicer display."""
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
    if "filter_settings" not in st.session_state:
        st.session_state["filter_settings"] = {}
    if "community_weights_raw" not in st.session_state:
        st.session_state["community_weights_raw"] = {}


def _get_selected_communities() -> set[str]:
    """Union aller bisher gewählten Communities (Artist- und Genre-Flow)."""
    artist_comms = st.session_state.get("artist_flow_selected_communities") or set()
    genre_comms = st.session_state.get("genre_flow_selected_communities") or set()
    # Beide können als set oder list vorliegen; in Strings umwandeln
    artist_set = {str(c) for c in artist_comms}
    genre_set = {str(c) for c in genre_comms}
    return artist_set.union(genre_set)


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Filter & Gewichte",
        page_icon="🎵",
        layout="wide",
    )

    _ensure_session_state()

    selected_comms = _get_selected_communities()

    st.title("🎛️ Filter & Community-Gewichte")
    st.caption(
        (
            "Hier kannst du deine Vorauswahl noch feiner einstellen: "
            "Veröffentlichungsjahr, Rating, S_a-Bereich und den Grad an Zufall "
            "(Serendipity). Mit dem Regler **Blütenrein <-> Cross-Over** und den "
            "Gewichten **alpha, beta, gamma** steuerst du, wie stark "
            "Community-Reinheit/Breite und Rating neben der Affinität S_a in den "
            "Gesamtscore einfließen "
            "(Rohwerte werden auf Summe 1 normiert). Außerdem kannst du einzelne "
            "Communities unterschiedlich gewichten."
        ),
    )

    with st.expander("Zusammenfassung deiner Auswahl", expanded=True):
        st.markdown(
            f"- **Gewählte Communities:** {len(selected_comms)}\n"
            f"- **Aktueller Freitext:** "
            f"`{(st.session_state.get('free_text_query') or '').strip()}`",
        )

    # --- Basis-Filter ---
    st.subheader("Basis-Filter")
    existing_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}

    year_min_default = int(existing_settings.get("year_min", 1990))
    year_max_default = int(existing_settings.get("year_max", 2030))
    rating_min_default = float(existing_settings.get("rating_min", 0.0))
    rating_max_default = float(existing_settings.get("rating_max", 10.0))
    score_min_default = float(existing_settings.get("score_min", 0.0))
    score_max_default = float(existing_settings.get("score_max", 1.0))

    col_year, col_rating = st.columns(2)
    with col_year:
        year_min, year_max = st.slider(
            "Veröffentlichungsjahr",
            min_value=1990,
            max_value=2030,
            value=(year_min_default, year_max_default),
            step=1,
        )
    with col_rating:
        rating_min, rating_max = st.slider(
            "Rating",
            min_value=0.0,
            max_value=10.0,
            value=(rating_min_default, rating_max_default),
            step=0.5,
        )

    score_min, score_max = st.slider(
        "S_a-Bereich (Community-Affinität, wie bisher)",
        min_value=0.0,
        max_value=1.0,
        value=(score_min_default, score_max_default),
        step=0.05,
        help=(
            "Filter auf die gewichtete Summe der Affinitäten zu deinen gewählten "
            "Communities — nicht auf den linearen Gesamtscore."
        ),
    )

    crossover_default = float(
        existing_settings.get(
            "community_spectrum_crossover",
            RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
        )
    )
    community_spectrum_crossover = st.slider(
        "Bluetenrein (0) <-> Cross-Over (1)",
        min_value=0.0,
        max_value=1.0,
        value=crossover_default,
        step=0.05,
        help=(
            "lambda: 0 = nur **Reinheit** (eine Community dominiert S_a); "
            "1 = nur **Breite** (Referenzen: 1-Gini auf gew. Communities, dann "
            "Perzentil-Rang in der Liste). Reinheit: min-max. "
            "Dann mit lambda mischen. **gamma** bestimmt den Anteil im Gesamtscore."
        ),
    )

    # --- Gesamtscore: alpha, beta, gamma (raw -> normalized to sum 1) ---
    st.subheader("Gesamtscore-Gewichte (alpha, beta, gamma)")
    ow_a_def = float(
        existing_settings.get("overall_weight_alpha", RECOMMENDATION_OVERALL_ALPHA),
    )
    ow_b_def = float(
        existing_settings.get("overall_weight_beta", RECOMMENDATION_OVERALL_BETA),
    )
    ow_g_def = float(
        existing_settings.get("overall_weight_gamma", RECOMMENDATION_OVERALL_GAMMA),
    )
    st.caption(
        "Rohwerte 0-1. Vor der Berechnung werden sie zu normierten Gewichten "
        "mit Summe 1 skaliert. **gamma** steuert den Anteil des Community-Spektrums "
        "(Reinheit/Breite nach Regler) gegenueber **S_a** (alpha) und "
        "**Rating** (beta)."
    )
    col_owa, col_owb, col_owg = st.columns(3)
    with col_owa:
        overall_weight_alpha = st.slider(
            "alpha - Affinitaet S_a",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_a_def)),
            step=0.05,
        )
    with col_owb:
        overall_weight_beta = st.slider(
            "beta - Plattentests-Rating",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_b_def)),
            step=0.05,
        )
    with col_owg:
        overall_weight_gamma = st.slider(
            "gamma - Community-Spektrum (Reinheit/Cross-Over)",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_g_def)),
            step=0.05,
        )
    ah, bh, gh = normalize_overall_weights(
        overall_weight_alpha,
        overall_weight_beta,
        overall_weight_gamma,
    )
    st.caption(
        f"Aktuell normiert: alpha={ah:.3f}, beta={bh:.3f}, gamma={gh:.3f}",
    )

    # --- Sortierung & Serendipity ---
    st.subheader("Sortierung")
    col_sort, col_ser = st.columns(2)
    with col_sort:
        sort_mode_default = str(existing_settings.get("sort_mode", "Deterministisch"))
        sort_mode = st.selectbox(
            "Ranglisten-Modus",
            options=["Deterministisch", "Serendipity"],
            index=0 if sort_mode_default == "Deterministisch" else 1,
        )
    with col_ser:
        serendipity_default = float(existing_settings.get("serendipity", 0.0))
        serendipity = st.slider(
            "Serendipity (0 = stabil, 1 = viel Zufall)",
            min_value=0.0,
            max_value=1.0,
            value=serendipity_default,
            step=0.1,
            disabled=(sort_mode != "Serendipity"),
            help=(
                "Misst, wie stark die finale Reihenfolge von der rein nach Gesamtscore "
                "sortierten Liste abweicht: Sortierschluessel (1-s)*Rang + s*Zufall "
                "(s in [0,1]). s=0: fix; s=1: fast komplett neu gemischt; "
                "Spearman-Rangkorrelation vor/nachher grob 1-s."
            ),
        )

    # --- Freitext-Retrieval-Strategie (A/B/C) ---
    st.subheader("Freitext-Retrieval")
    rag_strategy_default = str(existing_settings.get("rag_query_strategy", "B"))
    strategy_options = ["A", "B", "C"]
    try:
        strategy_index = strategy_options.index(rag_strategy_default)
    except ValueError:
        strategy_index = 1  # default: B

    rag_query_strategy = st.selectbox(
        "RAG-Variante für Freitext",
        options=strategy_options,
        index=strategy_index,
        help=(
            "A: Original-Query, B: regelbasierte Query-Varianten (Default), "
            "C: stärkere Expansion mit zusätzlicher Intent-Variante."
        ),
    )

    # --- Community-Gewichte ---
    st.subheader("Community-Gewichte")
    if not selected_comms:
        st.info(
            "Noch keine Communities ausgewählt. "
            "Bitte gehe zurück und wähle im Artist- oder Genre-Flow zunächst "
            "Communities aus.",
        )
        raw_weights: dict[str, float] = {}
    else:
        # Schönere Labels: Genre/Mood + Top-Artists
        communities = _load_communities_res_10()
        genre_labels = _load_genre_labels_res_10()
        comm_by_id: dict[str, dict[str, Any]] = {
            str(c.get("id")): c for c in communities if c.get("id")
        }

        st.caption(
            "Vergebe pro Community einen Roh-Score zwischen 0 und 1. "
            "Die Werte werden direkt in die Score-Berechnung übernommen "
            "(wie in der Legacy-Ansicht).",
        )
        existing_raw = st.session_state.get("community_weights_raw") or {}
        raw_weights = dict(existing_raw)

        with st.container():
            cols = st.columns(3)
            for idx, cid in enumerate(sorted(selected_comms)):
                c = comm_by_id.get(cid, {})
                size = int(c.get("size", 0)) if isinstance(c, dict) else 0
                top_artists = c.get("top_artists") if isinstance(c, dict) else None
                if not isinstance(top_artists, list):
                    top_artists = []
                top_artists_str = ", ".join(str(a) for a in top_artists[:2])
                genre_label = genre_labels.get(cid)

                if genre_label and top_artists_str:
                    label = f"{genre_label} ({top_artists_str})"
                elif genre_label:
                    label = genre_label
                elif top_artists_str:
                    label = top_artists_str
                else:
                    label = f"Community {cid}"

                display_label = f"{label}  ·  ID {cid}  ·  n={size}"

                col = cols[idx % len(cols)]
                with col:
                    raw_val = float(raw_weights.get(cid, 1.0))
                    raw_weights[cid] = st.slider(
                        display_label,
                        min_value=0.0,
                        max_value=1.0,
                        value=raw_val,
                        step=0.05,
                        key=f"weight_comm_{cid}",
                    )

    # --- Einstellungen im Session State speichern ---
    st.session_state["filter_settings"] = {
        "year_min": year_min,
        "year_max": year_max,
        "rating_min": rating_min,
        "rating_max": rating_max,
        "score_min": score_min,
        "score_max": score_max,
        "community_spectrum_crossover": community_spectrum_crossover,
        "overall_weight_alpha": overall_weight_alpha,
        "overall_weight_beta": overall_weight_beta,
        "overall_weight_gamma": overall_weight_gamma,
        "sort_mode": sort_mode,
        "serendipity": serendipity,
        "rag_query_strategy": rag_query_strategy,
    }
    st.session_state["community_weights_raw"] = raw_weights

    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("Zurück zu den Communities"):
            mode = st.session_state.get("flow_mode")
            if mode == "combined" or mode == "genres":
                st.switch_page("pages/2_Genre_Flow.py")
            else:
                st.switch_page("pages/1_Artist_Flow.py")
    with col_next:
        if st.button("Empfehlungen anzeigen"):
            st.switch_page("pages/6_Recommendations_Flow.py")


if __name__ == "__main__":
    main()
