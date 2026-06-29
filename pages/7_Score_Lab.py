"""Score Lab — internes Werkzeug zur Kalibrierung von Empfehlungs-Scores."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from pages.page_helpers import get_selected_communities, render_toolbar
from pages.profile_session import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_saved_profile_to_session,
)
from pages.recommendations_pool import (
    load_affinities,
    load_reviews_and_metadata,
)

from music_review.application.models import TasteProfile
from music_review.application.recommendation_service import RecommendationInputs
from music_review.dashboard.data_cache import (
    cached_load_communities_res_10,
    cached_load_community_memberships,
    cached_load_genre_labels_res_10,
    cached_load_sorted_unique_plattenlabels,
    cached_max_release_year_from_corpus,
    cached_min_release_year_from_corpus,
)
from music_review.dashboard.score_lab import (
    SCORE_LAB_TABLE_COLUMNS,
    ScoreLabDataSource,
    build_score_lab_rows,
    diagnose_score_lab_empty,
    format_score_lab_filter_summary,
    guess_matching_preset_id,
    lab_exploration_slider_defaults,
    lab_slider_settings_from_profile,
    load_active_saved_taste_profile,
    parse_review_ids_text,
    profile_with_lab_overrides,
    score_lab_rows_to_csv,
    taste_profile_from_saved_document,
)
from music_review.dashboard.score_lab_walkthrough import (
    build_album_score_walkthrough,
)
from music_review.dashboard.user_profile_store import (
    default_profiles_dir,
    ensure_active_profile_hydrated,
    load_profile,
)

_SCORE_LAB_WIDGET_PREFIX = "score_lab_"
_SCORE_LAB_LIMIT_OPTIONS: tuple[int | None, ...] = (50, 200, 500, None)
_SCORE_LAB_LIMIT_LABELS: dict[int | None, str] = {
    50: "50",
    200: "200",
    500: "500",
    None: "Alle",
}

_COMMUNITY_TABLE_DE: dict[str, str] = {
    "community_id": "Community",
    "label": "Bezeichnung",
    "profile_weight": "Profil-Gewicht",
    "album_affinity": "Album-Affinität",
    "weighted_contribution": "Beitrag (Gewicht * Affinität)",
    "share_of_s_a": "Anteil an S_a",
    "is_dominant": "Stärkster Treffer",
}

_PURITY_TABLE_DE: dict[str, str] = {
    "step": "Schritt",
    "explanation": "Erklärung",
    "calculation": "Rechnung",
    "value": "Ergebnis",
}

_BATCH_PURITY_TABLE_DE: dict[str, str] = {
    "rank_stilreinheit": "Rang (stilrein)",
    "artist": "Künstler",
    "album": "Album",
    "purity_raw": "purity_raw",
    "purity_norm": "purity_norm",
    "is_current_album": "Ausgewählt",
}

_BREADTH_TABLE_DE: dict[str, str] = {
    "community_id": "Community",
    "label": "Bezeichnung",
    "reference_mass": "Referenz-Masse",
    "profile_weight": "Profil-Gewicht",
    "weighted_mass": "Gewichtete Masse",
}

_STEP_TABLE_DE: dict[str, str] = {
    "step": "Schritt",
    "formula": "Formel",
    "inputs": "Eingaben",
    "value": "Ergebnis",
}


def _widget_key(name: str) -> str:
    return f"{_SCORE_LAB_WIDGET_PREFIX}{name}"


def _score_lab_wide_layout_css() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stMain"] .block-container {
            max-width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        section[data-testid="stMain"] {
            background: #fafafa;
        }
        .score-lab-walkthrough-title {
            font-size: 1.15rem;
            font-weight: 650;
            margin: 1.25rem 0 0.35rem 0;
            color: #111827;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    rename_map = {key: label for key, label in mapping.items() if key in df.columns}
    return df.rename(columns=rename_map)


def _active_profile_slug() -> str | None:
    raw = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _saved_profile_for_lab() -> TasteProfile | None:
    return load_active_saved_taste_profile(_active_profile_slug())


def _profile_from_session() -> TasteProfile | None:
    selected = get_selected_communities()
    if not selected:
        return None
    filter_settings = st.session_state.get("filter_settings")
    if not isinstance(filter_settings, dict):
        filter_settings = {}
    weights_raw = st.session_state.get("community_weights_raw")
    if not isinstance(weights_raw, dict):
        weights_raw = {}
    profile_name = "Gastprofil"
    active_slug = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if isinstance(active_slug, str) and active_slug.strip():
        try:
            loaded = load_profile(default_profiles_dir(), active_slug.strip())
            if loaded is not None:
                profile_name = str(loaded.get("name") or active_slug)
        except OSError:
            profile_name = active_slug.strip()
    return TasteProfile.from_mapping(
        {
            "name": profile_name,
            "selected_communities": sorted(selected),
            "filter_settings": filter_settings,
            "community_weights_raw": weights_raw,
        },
    )


def _apply_lab_sliders_from_profile(profile: TasteProfile) -> None:
    for key, value in lab_slider_settings_from_profile(profile).items():
        st.session_state[_widget_key(key)] = value


def _init_lab_slider_defaults(profile: TasteProfile) -> None:
    for key, value in lab_exploration_slider_defaults(profile).items():
        widget_key = _widget_key(key)
        if widget_key not in st.session_state:
            st.session_state[widget_key] = value


def _load_lab_settings_from_saved_profile() -> bool:
    """Apply saved DB profile to session and lab sliders; return False if none."""
    slug = _active_profile_slug()
    if slug is None:
        return False
    try:
        data = load_profile(default_profiles_dir(), slug)
    except OSError:
        return False
    if data is None:
        return False
    apply_saved_profile_to_session(data)
    loaded_profile = taste_profile_from_saved_document(data, profile_name=slug)
    _apply_lab_sliders_from_profile(loaded_profile)
    st.session_state[_widget_key("apply_product_filters")] = True
    return True


def _on_load_from_profile_click() -> None:
    """Streamlit callback: runs before widgets bind keys on the next rerun."""
    status_key = _widget_key("load_profile_status")
    if _load_lab_settings_from_saved_profile():
        st.session_state[status_key] = "saved"
        return
    profile = _profile_from_session()
    if profile is not None:
        _apply_lab_sliders_from_profile(profile)
    st.session_state[status_key] = "session_only"


def _on_reset_exploration_click() -> None:
    """Reset lab sliders to exploration defaults (full S_a range)."""
    profile = _profile_from_session()
    if profile is None:
        return
    for key, value in lab_exploration_slider_defaults(profile).items():
        st.session_state[_widget_key(key)] = value
    st.session_state[_widget_key("apply_product_filters")] = False
    st.session_state.pop(_widget_key("load_profile_status"), None)


def _recommendation_inputs() -> RecommendationInputs:
    reviews, metadata = load_reviews_and_metadata()
    return RecommendationInputs(
        reviews=reviews,
        metadata=metadata,
        affinities=load_affinities(),
        memberships=cached_load_community_memberships(),
        communities=cached_load_communities_res_10(),
        genre_labels=cached_load_genre_labels_res_10(),
        plattenlabels=cached_load_sorted_unique_plattenlabels(),
        year_floor=cached_min_release_year_from_corpus(),
        year_cap=cached_max_release_year_from_corpus(),
    )


@st.cache_data(ttl=300, show_spinner=False)
def _cached_score_lab_rows(
    profile_payload: str,
    data_source: ScoreLabDataSource,
    review_ids_text: str,
    overall_weight_alpha: float,
    overall_weight_beta: float,
    overall_weight_gamma: float,
    community_spectrum_crossover: float,
    score_min: float,
    score_max: float,
    corpus_signature: str,
    apply_product_filters: bool,
) -> list[dict[str, Any]]:
    _ = corpus_signature
    profile = TasteProfile.model_validate_json(profile_payload)
    lab_profile = profile_with_lab_overrides(
        profile,
        overall_weight_alpha=overall_weight_alpha,
        overall_weight_beta=overall_weight_beta,
        overall_weight_gamma=overall_weight_gamma,
        community_spectrum_crossover=community_spectrum_crossover,
        score_min=score_min,
        score_max=score_max,
    )
    review_ids = parse_review_ids_text(review_ids_text)
    return build_score_lab_rows(
        lab_profile,
        _recommendation_inputs(),
        data_source=data_source,
        limit=None,
        review_ids=review_ids if data_source == "review_ids" else None,
        apply_product_filters=apply_product_filters,
    )


def _render_profile_header(profile: TasteProfile) -> None:
    preset_id = guess_matching_preset_id(profile.filter_settings)
    preset_text = preset_id if preset_id else "kein Preset erkannt"
    n_communities = len(profile.selected_communities)
    st.caption(
        f"Profil: **{profile.name}** | Communities: **{n_communities}** "
        f"| Preset: **{preset_text}**",
    )


def _render_sidebar(
    profile: TasteProfile,
) -> tuple[ScoreLabDataSource, int | None, str, bool]:
    _init_lab_slider_defaults(profile)
    apply_product_filters = False
    with st.sidebar:
        st.subheader("Profil und Daten")
        data_source_label = st.radio(
            "Datenquelle",
            options=["Archiv (gefiltert)", "Feste Review-IDs"],
            index=0,
            key=_widget_key("data_source_radio"),
        )
        data_source: ScoreLabDataSource = (
            "review_ids" if data_source_label == "Feste Review-IDs" else "archive"
        )
        review_ids_text = ""
        if data_source == "review_ids":
            review_ids_text = st.text_input(
                "Review-IDs (kommagetrennt)",
                key=_widget_key("review_ids_text"),
                help=(
                    "Nur die angegebenen Alben werden bewertet "
                    "(ohne Jahr-/Label-Filter)."
                ),
            )
        limit_options = [
            _SCORE_LAB_LIMIT_LABELS[option] for option in _SCORE_LAB_LIMIT_OPTIONS
        ]
        limit_label = st.selectbox(
            "Anzahl Alben in Rangliste",
            options=limit_options,
            index=_SCORE_LAB_LIMIT_OPTIONS.index(200),
            key=_widget_key("limit_select"),
        )
        limit = next(
            key
            for key, label in _SCORE_LAB_LIMIT_LABELS.items()
            if label == limit_label
        )
        st.caption(
            f"Profil-Filter (Session): {format_score_lab_filter_summary(profile)}"
        )
        saved_profile = _saved_profile_for_lab()
        if saved_profile is not None:
            st.caption(
                "Gespeichertes Profil (DB): "
                f"{format_score_lab_filter_summary(saved_profile)}"
            )

        st.subheader("Live-Gewichtung")
        col_load, col_reset = st.columns(2)
        with col_load:
            st.button(
                "Aus Profil laden",
                key=_widget_key("load_from_profile"),
                on_click=_on_load_from_profile_click,
            )
        with col_reset:
            st.button(
                "Zurücksetzen",
                key=_widget_key("reset_defaults"),
                on_click=_on_reset_exploration_click,
            )
        load_status = st.session_state.get(_widget_key("load_profile_status"))
        if load_status == "session_only":
            st.warning(
                "Kein gespeichertes Konto-Profil gefunden. "
                "Session-Filter wurden in die Schieberegler übernommen."
            )
        elif load_status == "saved":
            st.success("Gespeichertes Profil in die Schieberegler geladen.")

        apply_product_filters = st.checkbox(
            "Empfehlungs-Filter (Jahr, Rating, Plattenlabel)",
            value=False,
            key=_widget_key("apply_product_filters"),
            help=(
                "Aus: nur Communities und Stilpassung min/max aus den Schiebereglern. "
                "An: wie die Seite Empfehlungen."
            ),
        )

        st.slider(
            "Relative Wichtigkeit: Stil-Nähe",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key=_widget_key("overall_weight_alpha"),
        )
        st.slider(
            "Relative Wichtigkeit: plattentests.de-Rating",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key=_widget_key("overall_weight_beta"),
        )
        st.slider(
            "Relative Wichtigkeit: Community-Spectrum",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key=_widget_key("overall_weight_gamma"),
        )
        st.slider(
            "Spectrum-Crossover",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key=_widget_key("community_spectrum_crossover"),
        )
        st.slider(
            "Stilpassung min (S_a)",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            key=_widget_key("score_min"),
        )
        st.slider(
            "Stilpassung max (S_a)",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            key=_widget_key("score_max"),
        )

    return data_source, limit, review_ids_text, apply_product_filters


def _apply_row_limit(
    rows: list[dict[str, Any]],
    limit: int | None,
) -> list[dict[str, Any]]:
    if limit is None or limit <= 0:
        return rows
    return rows[:limit]


def _render_score_walkthrough(
    rows: list[dict[str, Any]],
    batch_rows: list[dict[str, Any]],
    profile: TasteProfile,
    inputs: RecommendationInputs,
) -> None:
    if not rows:
        return

    st.markdown(
        '<p class="score-lab-walkthrough-title">Score-Nachvollzug (Beispielalbum)</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Wähle ein Album aus der Rangliste. Die Tabellen zeigen dieselbe Berechnung "
        "wie in der Produktions-Pipeline — Schritt für Schritt mit deinen Zahlen."
    )

    options = {
        f"#{row['rank']} — {row.get('artist')} — {row.get('album')}": row
        for row in rows
    }
    label = st.selectbox(
        "Album für Nachvollzug",
        options=list(options.keys()),
        key=_widget_key("walkthrough_album"),
    )
    row = options[label]
    walkthrough = build_album_score_walkthrough(
        row,
        profile,
        inputs,
        batch_rows=batch_rows,
    )

    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
    with meta_col1:
        st.metric("overall_score", f"{walkthrough['summary']['overall_score']:.4f}")
    with meta_col2:
        st.metric("S_a (Stilpassung)", f"{walkthrough['summary']['s_a']:.4f}")
    with meta_col3:
        st.metric("cosine_fit", f"{walkthrough['summary']['cosine_fit']:.4f}")
    with meta_col4:
        st.metric(
            "Kandidaten für Batch-Norm",
            int(walkthrough["summary"]["batch_size"]),
        )

    url = walkthrough.get("url")
    if isinstance(url, str) and url.strip():
        st.markdown(f"[Rezension auf plattentests.de]({url})")

    left, right = st.columns(2)

    with left:
        st.markdown("**Schritt 1: Stilpassung S_a**")
        style_df = _rename_columns(
            pd.DataFrame([walkthrough["style_steps"][0]]),
            _STEP_TABLE_DE,
        )
        st.dataframe(style_df, use_container_width=True, hide_index=True)

        st.markdown("**Community-Beiträge zur Stilpassung**")
        comm_source = pd.DataFrame(walkthrough["community_rows"])
        if "is_dominant" in comm_source.columns:
            comm_source = comm_source.sort_values(
                by=["is_dominant", "weighted_contribution"],
                ascending=[False, False],
            )
        comm_df = _rename_columns(comm_source, _COMMUNITY_TABLE_DE)
        st.dataframe(comm_df, use_container_width=True, hide_index=True)

        st.markdown("**Schritt 2: Stilreinheit (purity_raw)**")
        purity = walkthrough["purity_detail"]
        st.write(purity["concept"])
        purity_df = _rename_columns(
            pd.DataFrame(purity["calculation_rows"]),
            _PURITY_TABLE_DE,
        )
        st.dataframe(purity_df, use_container_width=True, hide_index=True)
        st.info(purity["interpretation"])

    with right:
        st.markdown("**Schritt 3: Stilreinheit normiert (purity_norm)**")
        purity_norm = walkthrough["purity_norm_detail"]
        st.write(purity_norm["concept"])
        purity_norm_df = _rename_columns(
            pd.DataFrame(purity_norm["calculation_rows"]),
            _PURITY_TABLE_DE,
        )
        st.dataframe(purity_norm_df, use_container_width=True, hide_index=True)

        batch_source = pd.DataFrame(purity_norm["batch_purity_rows"])
        if "is_current_album" in batch_source.columns:
            batch_source = batch_source.sort_values(
                by=["is_current_album", "rank_stilreinheit"],
                ascending=[False, True],
            )
        batch_df = _rename_columns(batch_source, _BATCH_PURITY_TABLE_DE)
        st.markdown("**Batch-Vergleich purity_raw / purity_norm**")
        st.caption(
            f"Alle {int(purity_norm['batch_size'])} Kandidaten; "
            "Rang 1 = stilreinster im Batch."
        )
        st.dataframe(batch_df, use_container_width=True, hide_index=True)
        st.info(purity_norm["interpretation"])

        st.markdown("**Schritte 4-8: Community-Spectrum**")
        spectrum_df = _rename_columns(
            pd.DataFrame(walkthrough["spectrum_steps"][1:]),
            _STEP_TABLE_DE,
        )
        st.dataframe(spectrum_df, use_container_width=True, hide_index=True)

        st.markdown("**Referenz-Künstler (Abdeckungsbreite)**")
        breadth_df = _rename_columns(
            pd.DataFrame(walkthrough["breadth_rows"]),
            _BREADTH_TABLE_DE,
        )
        st.dataframe(breadth_df, use_container_width=True, hide_index=True)

    st.markdown("**Gesamtscore overall_score**")
    overall_df = _rename_columns(
        pd.DataFrame(walkthrough["overall_steps"]),
        _STEP_TABLE_DE,
    )
    st.dataframe(overall_df, use_container_width=True, hide_index=True)

    st.caption(
        "Hinweis: purity_norm und breadth_norm sind relativ zur aktuellen "
        "Kandidatenliste (Batch), nicht absolut über alle Nutzer. S_a, Rating "
        "und die Gewichte alpha/beta/gamma sind nutzerabsolut."
    )


def main() -> None:
    _score_lab_wide_layout_css()
    render_toolbar("Score Lab")
    ensure_active_profile_hydrated(st.session_state)
    st.title("Score Lab")
    st.caption(
        "Internes Werkzeug: volle Dashboard-Breite, Score-Nachvollzug mit Tabellen. "
        "Nichts wird automatisch im Profil gespeichert."
    )

    profile = _profile_from_session()
    if profile is None:
        st.warning(
            "Kein Geschmacksprofil aktiv. Bitte zuerst die Schritte Einstieg, "
            "Genre/Stil und Filter abschließen.",
        )
        return

    _render_profile_header(profile)
    data_source, limit, review_ids_text, apply_product_filters = _render_sidebar(
        profile,
    )

    lab_profile = profile_with_lab_overrides(
        profile,
        overall_weight_alpha=float(
            st.session_state[_widget_key("overall_weight_alpha")]
        ),
        overall_weight_beta=float(st.session_state[_widget_key("overall_weight_beta")]),
        overall_weight_gamma=float(
            st.session_state[_widget_key("overall_weight_gamma")]
        ),
        community_spectrum_crossover=float(
            st.session_state[_widget_key("community_spectrum_crossover")],
        ),
        score_min=float(st.session_state[_widget_key("score_min")]),
        score_max=float(st.session_state[_widget_key("score_max")]),
    )

    with st.spinner("Scores werden berechnet …"):
        inputs = _recommendation_inputs()
        corpus_signature = f"{len(inputs.reviews)}:{len(inputs.affinities)}"
        batch_rows = _cached_score_lab_rows(
            profile.model_dump_json(),
            data_source,
            review_ids_text,
            float(st.session_state[_widget_key("overall_weight_alpha")]),
            float(st.session_state[_widget_key("overall_weight_beta")]),
            float(st.session_state[_widget_key("overall_weight_gamma")]),
            float(st.session_state[_widget_key("community_spectrum_crossover")]),
            float(st.session_state[_widget_key("score_min")]),
            float(st.session_state[_widget_key("score_max")]),
            corpus_signature,
            apply_product_filters,
        )

    if not batch_rows:
        counts = diagnose_score_lab_empty(
            lab_profile,
            inputs,
            apply_product_filters=apply_product_filters,
        )
        st.warning("Keine Alben für die aktuelle Konfiguration gefunden.")
        st.markdown(
            f"- Alben mit Community-Treffern: **{counts['community_hits']}**\n"
            f"- Davon im Stilpassungs-Intervall "
            f"({lab_profile.filter_settings.score_min:.2f}-"
            f"{lab_profile.filter_settings.score_max:.2f}): "
            f"**{counts['after_score_range']}**\n"
            f"- Nach allen aktiven Filtern: **{counts['after_product_filters']}**"
        )
        if counts["community_hits"] > 0 and counts["after_score_range"] == 0:
            st.info(
                "Die Stilpassung min/max-Schieberegler sind zu streng "
                f"(aktuell {lab_profile.filter_settings.score_min:.2f}"
                f"-{lab_profile.filter_settings.score_max:.2f}). "
                "Klicke **Aus Profil laden** für die gespeicherten Filter, "
                "oder **Zurücksetzen** für Erkundung (min = 0)."
            )
        elif counts["after_score_range"] > 0 and counts["after_product_filters"] == 0:
            st.info(
                "Empfehlungs-Filter (Jahr, Rating, Plattenlabel) schließen alle "
                "Kandidaten aus. Checkbox in der Sidebar aus lassen oder Filter "
                "im Filter-Flow lockern."
            )
        return

    display_rows = _apply_row_limit(batch_rows, limit)
    st.subheader("Rangliste")
    st.caption(
        f"Zeige {len(display_rows)} von {len(batch_rows)} Alben "
        f"(Batch-Normierung nutzt alle {len(batch_rows)} Kandidaten). "
        "cosine_fit: Kosinus-Ähnlichkeit zwischen Nutzer-Gewichtsvektor und "
        "Album-Affinitätsvektor über alle Communities."
    )
    table_df = pd.DataFrame(display_rows)
    display_columns = [
        column for column in SCORE_LAB_TABLE_COLUMNS if column in table_df.columns
    ]
    st.dataframe(
        table_df[display_columns],
        use_container_width=True,
        hide_index=True,
        height=min(420, 38 + len(display_rows) * 35),
    )

    csv_text = score_lab_rows_to_csv(display_rows)
    st.download_button(
        "CSV exportieren (sichtbare Rangliste)",
        data=csv_text.encode("utf-8"),
        file_name="score_lab_export.csv",
        mime="text/csv",
        key=_widget_key("csv_download"),
    )

    _render_score_walkthrough(
        display_rows,
        batch_rows,
        lab_profile,
        inputs,
    )


main()
