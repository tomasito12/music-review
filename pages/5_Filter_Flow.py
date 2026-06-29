"""Filter und Gewichte (Schritt 3 von 3) -- zentriertes Karten-Layout."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st
from pages.page_helpers import (
    DEFAULT_PLATTENTESTS_RATING_FILTER_MAX,
    DEFAULT_PLATTENTESTS_RATING_FILTER_MIN,
    FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY,
    FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_BETA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA,
    FILTER_FLOW_WIDGET_KEY_RATING_RANGE,
    FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
    FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
    FILTER_PLATTENLABEL_MULTISELECT_KEY,
    PLATTENLABEL_SONSTIGE_UI,
    STYLE_MATCH_FILTER_PERCENT_STEP,
    WIZARD_ACCOUNT_SAVE_INTENT_KEY,
    clamp_plattentests_rating_filter_range,
    clamp_year_filter_bounds,
    collapse_plattenlabel_ui_selection,
    community_display_label,
    expand_plattenlabel_ui_selection,
    format_style_weight_example_artists,
    get_selected_communities,
    has_step3_state,
    normalize_filter_expander_vspace_gap,
    prune_weights_to_selected_communities,
    refresh_taste_wizard_after_filter_save,
    render_toolbar,
    reset_step3,
    style_match_percent_tuple_for_slider,
    style_match_scores_from_percent_slider,
)

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_OVERALL_ALPHA,
    RECOMMENDATION_OVERALL_BETA,
    RECOMMENDATION_OVERALL_GAMMA,
)
from music_review.dashboard.community_weight_mapping import (
    community_weight_bias_from_stored,
    community_weight_stored_from_bias,
)
from music_review.dashboard.data_cache import (
    cached_load_communities_res_10,
    cached_load_genre_labels_res_10,
    cached_load_plattenlabel_filter_buckets,
    cached_max_release_year_from_corpus,
    cached_min_release_year_from_corpus,
)


def _filter_css() -> None:
    st.markdown(
        """
        <style>
        .filter-hero {
            text-align: center;
            padding: 1.1rem 0.75rem 0.35rem 0.75rem;
        }
        .filter-eyebrow {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.4rem;
        }
        .filter-title {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
            color: #111827;
        }
        /* Streamlit Markdown-Container: oft links; Ausgleich per ID + !important */
        div[data-testid="stMarkdownContainer"] #filter-page-desc-wrap,
        div[data-testid="stMarkdownContainer"] .filter-expander-desc-wrap {
            text-align: center !important;
            width: 100% !important;
            box-sizing: border-box;
            margin: 0 0 0.85rem 0 !important;
        }
        div[data-testid="stMarkdownContainer"] #filter-page-desc-wrap .filter-desc,
        div[data-testid="stMarkdownContainer"] .filter-expander-desc-wrap .filter-desc {
            max-width: 34rem;
            margin-left: auto !important;
            margin-right: auto !important;
            color: #6b7280;
            font-size: 0.92rem;
            line-height: 1.58;
            text-align: center !important;
        }
        /* Expander-Titel: einheitlich rot (Filterung + Gewichtung) */
        section[data-testid="stMain"] div[data-testid="stExpander"] summary,
        section[data-testid="stMain"] div[data-testid="stExpander"] summary p,
        section[data-testid="stMain"] div[data-testid="stExpander"] summary span {
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            color: #dc2626 !important;
        }
        div[data-testid="stExpander"] {
            margin-bottom: 0.85rem;
        }
        .filter-style-weight-name {
            font-size: 0.82rem;
            font-weight: 600;
            color: #374151;
            margin: 0;
            line-height: 1.35;
        }
        /*
         * Artist line: same colour and line-height as weight questions, normal weight,
         * smaller than .filter-style-weight-name. Streamlit markdown can override
         * plain class rules; target stMarkdownContainer and use !important.
         */
        section[data-testid="stMain"]
            div[data-testid="stMarkdownContainer"]
            .filter-style-weight-artist-caption,
        section[data-testid="stMain"]
            .filter-style-weight-unit
            .filter-style-weight-artist-caption {
            font-size: 0.72rem !important;
            font-weight: 400 !important;
            color: #374151 !important;
            line-height: 1.45 !important;
            margin: 0 0 0.28rem 0 !important;
            max-width: 40rem !important;
        }
        /*
         * Style-weight units: bordered st.container plus key style_weight_unit_*.
         * Match st-key-* and align fill/shadow with the filter page.
         */
        section[data-testid="stMain"] [class*="st-key-style_weight_unit"] {
            background-color: #ffffff !important;
            border-color: #e5e7eb !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
            padding: 0.45rem 0.4rem 0.5rem !important;
            margin-bottom: 0.6rem !important;
        }
        .filter-style-weight-unit .filter-style-weight-name:not(:last-child) {
            margin-bottom: 0.2rem;
        }
        .filter-style-weight-unit {
            margin-bottom: 0.3rem;
        }
        .filter-style-weight-end {
            margin: 0.1rem 0 0 0;
            padding: 0 0.05rem;
            text-align: center;
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1;
            color: #6b7280;
            user-select: none;
        }
        .filter-style-weight-end__line {
            display: block;
        }
        div[data-testid="stHorizontalBlock"]:has(.filter-style-weight-end)
            > div[data-testid="column"]
            > div[data-testid="element-container"] {
            margin-top: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.filter-style-weight-end)
            div[data-testid="stSlider"] {
            margin-top: 0 !important;
        }
        /*
         * Style-bias row (has end caps): flat inner track, thumb only.
         */
        div[data-testid="stHorizontalBlock"]:has(.filter-style-weight-end)
            div[data-testid="stSlider"]
            div:has([data-testid="stSliderThumbValue"])
            + div {
            background-image: none !important;
            background: #d1d5db !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.filter-style-weight-end)
            div[data-testid="stSlider"]
            div[style*="linear-gradient"] {
            background-image: none !important;
            background: #d1d5db !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.filter-style-weight-end)
            div[data-testid="stSlider"] [data-testid="stSliderTickBar"] {
            display: none !important;
        }
        /* Vertikaler Rhythmus innerhalb der Expander (nur Finetuning) */
        .filter-vspace-sm {
            display: block;
            height: 0.55rem;
            min-height: 0.55rem;
            margin: 0;
            padding: 0;
            line-height: 0;
            font-size: 0;
        }
        .filter-vspace-md {
            display: block;
            height: 1rem;
            min-height: 1rem;
            margin: 0;
            padding: 0;
            line-height: 0;
            font-size: 0;
        }
        .filter-vspace-lg {
            display: block;
            height: 1.5rem;
            min-height: 1.5rem;
            margin: 0;
            padding: 0;
            line-height: 0;
            font-size: 0;
        }
        .filter-vspace-xl {
            display: block;
            height: 2rem;
            min-height: 2rem;
            margin: 0;
            padding: 0;
            line-height: 0;
            font-size: 0;
        }
        .filter-section {
            background: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 1.25rem 1.35rem 1.05rem 1.35rem;
            margin-bottom: 0.95rem;
        }
        .filter-section.accent-filter {
            border-left: 3px solid #dc2626;
        }
        .filter-section.accent-weight {
            border-left: 3px solid #dc2626;
        }
        .filter-section-label {
            font-size: 0.92rem;
            font-weight: 650;
            color: #111827;
            margin: 0 0 0.15rem 0;
            line-height: 1.35;
        }
        .filter-section-caption {
            font-size: 0.82rem;
            color: #6b7280;
            margin: 1.05rem 0 0.35rem 0;
            line-height: 1.5;
        }
        .filter-section-caption--lead {
            margin-top: 0.35rem;
            margin-bottom: 1.05rem;
        }
        .filter-cta {
            text-align: center;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .filter-weight-question {
            font-size: 0.88rem;
            font-weight: 600;
            color: #374151;
            margin: 0 0 0.35rem 0;
            line-height: 1.45;
            max-width: 40rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _filter_vertical_space(gap: str = "md") -> None:
    """Extra vertical space inside Filterung/Gewichtung expanders."""
    safe = normalize_filter_expander_vspace_gap(gap)
    st.markdown(
        f'<div class="filter-vspace-{safe}" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def _ensure_session_state() -> None:
    if "filter_settings" not in st.session_state:
        st.session_state["filter_settings"] = {}
    if "community_weights_raw" not in st.session_state:
        st.session_state["community_weights_raw"] = {}


def _render_style_weights(
    selected_comms: set[str],
) -> dict[str, float]:
    """Render per-style weight sliders and return raw weights dict."""
    if not selected_comms:
        st.info(
            "Noch keine Stil-Schwerpunkte ausgewählt. "
            "Bitte gehe zurück und wähle zuerst Genre und Künstler aus."
        )
        return {}

    communities = cached_load_communities_res_10()
    genre_labels = cached_load_genre_labels_res_10()
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    st.markdown(
        '<p class="filter-section-caption filter-section-caption--lead">'
        "Hier kannst du bei der Sortierung bestimmte Stilrichtungen "
        "stärker oder schwächer gewichten."
        "</p>",
        unsafe_allow_html=True,
    )
    existing_raw = st.session_state.get("community_weights_raw") or {}
    raw_weights: dict[str, float] = dict(existing_raw)

    cols = st.columns(2)
    for idx, cid in enumerate(sorted(selected_comms)):
        c = comm_by_id.get(cid, {})
        top_artists = c.get("top_artists") if isinstance(c, dict) else None
        if not isinstance(top_artists, list):
            top_artists = []
        top_artists_str = format_style_weight_example_artists(top_artists)
        comm_dict = c if isinstance(c, dict) else None
        base = community_display_label(cid, genre_labels, comm_dict)

        col = cols[idx % len(cols)]
        with col:
            unit_key = f"style_weight_unit_{cid}"
            with st.container(border=True, key=unit_key):
                default_w = RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW
                raw_val = float(raw_weights.get(cid, default_w))
                bias = community_weight_bias_from_stored(raw_val)
                head_html = [
                    '<div class="filter-style-weight-unit">',
                    f'<p class="filter-style-weight-name">{html.escape(base)}</p>',
                ]
                if top_artists_str:
                    head_html.append(
                        '<div class="filter-style-weight-artist-caption">'
                        f"{html.escape(top_artists_str)}</div>"
                    )
                head_html.append("</div>")
                st.markdown("".join(head_html), unsafe_allow_html=True)
                cap_l, mid, cap_r = st.columns([0.65, 7.7, 0.65])
                with cap_l:
                    st.markdown(
                        '<p class="filter-style-weight-end" '
                        'title="Geringeres Gewicht für diese Stilrichtung">'
                        '<span class="filter-style-weight-end__line">&#8722;</span>'
                        "</p>",
                        unsafe_allow_html=True,
                    )
                with mid:
                    new_bias = st.slider(
                        "style_weight_bias",
                        min_value=-1.0,
                        max_value=1.0,
                        value=bias,
                        step=0.1,
                        label_visibility="collapsed",
                        key=f"weight_comm_{cid}",
                        help=(
                            "Mitte = neutral. Nach rechts mehr Gewicht für diese "
                            "Stilrichtung, nach links weniger."
                        ),
                    )
                with cap_r:
                    st.markdown(
                        '<p class="filter-style-weight-end" '
                        'title="Stärkeres Gewicht für diese Stilrichtung">'
                        '<span class="filter-style-weight-end__line">+</span>'
                        "</p>",
                        unsafe_allow_html=True,
                    )
                raw_weights[cid] = community_weight_stored_from_bias(float(new_bias))
    return raw_weights


def _render_filter_account_save_prompt() -> bool:
    """Show post-step-3 save prompt; return True if this view handled the page."""
    if not st.session_state.get(FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY):
        return False
    st.markdown(
        '<div class="filter-hero"><p class="filter-eyebrow">Speichern</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div id="filter-page-desc-wrap" class="filter-desc-wrap" '
        'style="text-align:center;width:100%;">'
        '<p class="filter-desc" style="text-align:center;margin-left:auto;'
        'margin-right:auto;max-width:34rem;">'
        "Sollen die vorgenommenen Einstellungen zu deiner Musikauswahl in einem "
        "Nutzerkonto gespeichert werden? Dann musst du diese Auswahl nicht jedes "
        "Mal wieder vornehmen, wenn du auf die Seite kommst."
        "</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="filter-cta">', unsafe_allow_html=True)
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button(
            "Ja, ich möchte die Auswahl speichern",
            type="primary",
            width="stretch",
            key="filter_account_save_yes",
        ):
            st.session_state[WIZARD_ACCOUNT_SAVE_INTENT_KEY] = True
            st.session_state.pop(FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY, None)
            st.switch_page("pages/0c_Anmelden.py")
    with col_no:
        if st.button(
            "Nein, ohne Speichern weiter",
            width="stretch",
            key="filter_account_save_no",
        ):
            st.session_state.pop(FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY, None)
            st.session_state.pop(WIZARD_ACCOUNT_SAVE_INTENT_KEY, None)
            st.switch_page("pages/2_Entdecken.py")
    st.markdown("</div>", unsafe_allow_html=True)
    return True


def main() -> None:
    _ensure_session_state()
    prune_weights_to_selected_communities()
    # Styles vor dem oberen Trennstrich: Hero direkt unter --- wie auf Schritt 1/2.
    _filter_css()
    render_toolbar("filter_flow")
    if _render_filter_account_save_prompt():
        return

    selected_comms = get_selected_communities()
    existing_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}

    # ── Hero ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="filter-hero">'
        '<p class="filter-eyebrow">Schritt 3 von 3</p>'
        '<p class="filter-title">Finetuning</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div id="filter-page-desc-wrap" class="filter-desc-wrap" '
        'style="text-align:center;width:100%;">'
        '<p class="filter-desc" style="text-align:center;margin-left:auto;'
        'margin-right:auto;max-width:34rem;">'
        "Stelle ein, wonach die Empfehlungen sortiert und gefiltert "
        "werden sollen.<br>"
        "Die Standardwerte liefern bereits gute Ergebnisse -<br>"
        "passe nur an, was du bewusst verändern möchtest."
        "</p></div>",
        unsafe_allow_html=True,
    )

    # ── Filterung / Gewichtung (aufklappbar) ─────────────────────
    st.markdown('<div style="margin-top:2.5rem;"></div>', unsafe_allow_html=True)

    with st.expander("Filterung"):
        st.markdown(
            '<div class="filter-expander-desc-wrap" '
            'style="text-align:center;width:100%;">'
            '<p class="filter-desc" style="text-align:center;margin-left:auto;'
            'margin-right:auto;max-width:34rem;">'
            "Diese Einstellungen bestimmen, welche Alben in den Empfehlungen "
            "erscheinen. Alben außerhalb der gewählten Bereiche werden "
            "ausgeblendet."
            "</p></div>",
            unsafe_allow_html=True,
        )
        _filter_vertical_space("md")

        # ── Zeitraum und Rating ─────────────────────────────────
        st.markdown(
            '<div class="filter-section accent-filter">'
            '<p class="filter-section-label">Zeitraum und Rating</p>',
            unsafe_allow_html=True,
        )
        _filter_vertical_space("sm")
        year_floor = cached_min_release_year_from_corpus()
        year_cap = cached_max_release_year_from_corpus()
        year_min_default, year_max_default = clamp_year_filter_bounds(
            existing_settings.get("year_min", year_floor),
            existing_settings.get("year_max", year_cap),
            year_cap=year_cap,
            year_floor=year_floor,
        )
        rating_min_default, rating_max_default = clamp_plattentests_rating_filter_range(
            existing_settings.get("rating_min", DEFAULT_PLATTENTESTS_RATING_FILTER_MIN),
            existing_settings.get("rating_max", DEFAULT_PLATTENTESTS_RATING_FILTER_MAX),
        )

        col_year, col_rating = st.columns(2)
        with col_year:
            year_min, year_max = st.slider(
                "Veröffentlichungsjahr",
                min_value=year_floor,
                max_value=year_cap,
                value=(year_min_default, year_max_default),
                step=1,
                key=FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
            )
        with col_rating:
            rating_min, rating_max = st.slider(
                "Rating (plattentests.de)",
                min_value=0,
                max_value=10,
                value=(rating_min_default, rating_max_default),
                step=1,
                key=FILTER_FLOW_WIDGET_KEY_RATING_RANGE,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        _filter_vertical_space("xl")

        # ── Passung ──────────────────────────────────────────────
        st.markdown(
            '<div class="filter-section accent-filter">'
            '<p class="filter-section-label">'
            "Passung"
            "</p>",
            unsafe_allow_html=True,
        )
        _filter_vertical_space("sm")
        pct_lo_def, pct_hi_def = style_match_percent_tuple_for_slider(
            existing_settings.get("score_min", 0.0),
            existing_settings.get("score_max", 1.0),
            step=STYLE_MATCH_FILTER_PERCENT_STEP,
        )
        pct_lo, pct_hi = st.slider(
            "Wie stark sollen die Alben deinen gewählten Fein-Genres entsprechen?",
            min_value=0,
            max_value=100,
            value=(pct_lo_def, pct_hi_def),
            step=STYLE_MATCH_FILTER_PERCENT_STEP,
            format="%d %%",
            key=FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
            help=(
                "Linke Marke: Untergrenze, rechte Marke: Obergrenze der "
                "zulässigen Passung (0-100 %). Alben dazwischen bleiben im "
                "Spielraum; niedrigere Werte erlauben insgesamt lockerere "
                "Übereinstimmung mit deinen Fein-Genres."
            ),
        )
        st.markdown(
            '<p class="filter-section-caption">'
            "Niedrige <strong>Prozentwerte</strong> bedeuten, dass auch andere, "
            "von dir nicht präferierte Stilrichtungen in den "
            "<strong>empfohlenen Alben</strong> vertreten sein dürfen."
            "</p>",
            unsafe_allow_html=True,
        )
        score_min, score_max = style_match_scores_from_percent_slider(
            int(pct_lo),
            int(pct_hi),
        )
        st.markdown("</div>", unsafe_allow_html=True)

        _filter_vertical_space("xl")

        # ── Plattenlabel (Expertenfilter) ─────────────────────────
        freq_labels, rare_labels, _n_rev = cached_load_plattenlabel_filter_buckets()
        all_concrete = sorted(set(freq_labels) | set(rare_labels))
        ui_options = list(freq_labels)
        if rare_labels:
            ui_options.append(PLATTENLABEL_SONSTIGE_UI)
        ms_key = FILTER_PLATTENLABEL_MULTISELECT_KEY
        opts_set = set(ui_options)
        with st.expander("Plattenlabel (Expertenfilter)", expanded=False):
            if all_concrete:
                if ms_key not in st.session_state:
                    prev_sel = existing_settings.get("plattenlabel_selection")
                    if isinstance(prev_sel, list):
                        prev_set = {x for x in prev_sel if x in all_concrete}
                        if prev_sel == []:
                            st.session_state[ms_key] = []
                        elif prev_set:
                            st.session_state[ms_key] = (
                                collapse_plattenlabel_ui_selection(
                                    prev_set,
                                    freq_labels,
                                    rare_labels,
                                )
                            )
                        else:
                            st.session_state[ms_key] = list(ui_options)
                    else:
                        st.session_state[ms_key] = list(ui_options)
                prev_ms = list(st.session_state[ms_key])
                pruned_ms = [x for x in prev_ms if x in opts_set]
                if pruned_ms:
                    st.session_state[ms_key] = pruned_ms
                elif not prev_ms:
                    st.session_state[ms_key] = []
                else:
                    st.session_state[ms_key] = list(ui_options)

                # Buttons vor dem Multiselect: sonst ist der Widget-Key gesperrt
                # und Session-State darf nicht mehr gesetzt werden.
                col_pl_off, col_pl_on = st.columns(2)
                with col_pl_off:
                    if st.button(
                        "Alle Plattenlabels abwählen",
                        key="filter_plattenlabel_clear",
                        width="stretch",
                    ):
                        st.session_state[ms_key] = []
                        st.rerun()
                with col_pl_on:
                    if st.button(
                        "Alle Plattenlabels auswählen",
                        key="filter_plattenlabel_fill",
                        width="stretch",
                    ):
                        st.session_state[ms_key] = list(ui_options)
                        st.rerun()

                st.multiselect(
                    "Plattenlabel auswählen",
                    options=ui_options,
                    key=ms_key,
                    help=(
                        f"„{PLATTENLABEL_SONSTIGE_UI}“ schließt alle selteneren Labels "
                        "ein. Standard: alle Optionen aktiv (= kein Ausschluss). "
                        "„Alle abwählen“: nur noch Alben ohne Label-Eintrag."
                    ),
                )
            else:
                st.caption(
                    "In der Rezensionen-Datei sind keine Plattenlabels hinterlegt; "
                    "dieser Filter steht nicht zur Verfügung."
                )

    st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)

    with st.expander("Gewichtung"):
        st.markdown(
            '<div class="filter-expander-desc-wrap" '
            'style="text-align:center;width:100%;">'
            '<p class="filter-desc" style="text-align:center;margin-left:auto;'
            'margin-right:auto;max-width:34rem;">'
            "Diese Einstellungen beeinflussen die Reihenfolge der Empfehlungen, "
            "schließen aber keine Alben aus."
            "</p></div>",
            unsafe_allow_html=True,
        )
        _filter_vertical_space("xl")

        # ── Gewichtung des Gesamtscores ─────────────────────────
        st.markdown(
            '<div class="filter-section accent-weight">'
            '<p class="filter-section-label">Gewichtung des Gesamtscores</p>',
            unsafe_allow_html=True,
        )
        _filter_vertical_space("md")
        ow_a_def = float(
            existing_settings.get(
                "overall_weight_alpha",
                RECOMMENDATION_OVERALL_ALPHA,
            ),
        )
        ow_b_def = float(
            existing_settings.get(
                "overall_weight_beta",
                RECOMMENDATION_OVERALL_BETA,
            ),
        )
        ow_g_def = float(
            existing_settings.get(
                "overall_weight_gamma",
                RECOMMENDATION_OVERALL_GAMMA,
            ),
        )
        st.markdown(
            '<p class="filter-weight-question">'
            "Wie wichtig ist dir, dass die Sortierung der Alben deinen "
            "gewählten Musikrichtungen entspricht?"
            "</p>",
            unsafe_allow_html=True,
        )
        overall_weight_alpha = st.slider(
            "Relative Wichtigkeit: Stil-Nähe",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_a_def)),
            step=0.05,
            key=FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA,
            help=(
                "Hohe Werte ziehen Alben nach oben, die stark zu deinen "
                "gewählten Stil-Schwerpunkten passen (Community-Affinität)."
            ),
        )
        _filter_vertical_space("sm")
        st.markdown(
            '<p class="filter-weight-question">'
            "Wie wichtig ist dir, dass höher bewertete Alben weiter oben in "
            "der Sortierung stehen?"
            "</p>",
            unsafe_allow_html=True,
        )
        overall_weight_beta = st.slider(
            "Relative Wichtigkeit: plattentests.de-Rating",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_b_def)),
            step=0.05,
            key=FILTER_FLOW_WIDGET_KEY_OVERALL_BETA,
            help=(
                "Hohe Werte betonen die Bewertung von plattentests.de "
                "im Gesamtscore (fehlende Ratings werden mit einem "
                "Standardwert angenommen)."
            ),
        )
        _filter_vertical_space("sm")
        st.markdown(
            '<p class="filter-weight-question">'
            "Wie wichtig ist dir bei der Sortierung, ob Alben viele "
            "verschiedene Stilrichtungen vereinen oder eher stilrein sind?"
            "</p>",
            unsafe_allow_html=True,
        )
        overall_weight_gamma = st.slider(
            "Relative Wichtigkeit: Album-Stilbreite",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_g_def)),
            step=0.05,
            key=FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA,
            help=(
                "Hohe Werte bevorzugen Alben mit breiterer Stilverteilung "
                "(Shannon-Diversität über alle erkannten Stile, relativ zum "
                "Archiv). Bei 0 zählt dieser Teil des Gesamtscores nicht."
            ),
        )
        st.markdown("</div>", unsafe_allow_html=True)

        _filter_vertical_space("xl")

        # ── Gewichte pro Stil-Schwerpunkt ───────────────────────
        st.markdown(
            '<div class="filter-section accent-weight">'
            '<p class="filter-section-label">Gewichte pro Stil-Schwerpunkt</p>',
            unsafe_allow_html=True,
        )
        _filter_vertical_space("sm")
        raw_weights = _render_style_weights(selected_comms)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)

    # ── Session State speichern ──────────────────────────────────
    # Sortierung/Serendipity: Empfehlungsseite.
    merged_fs: dict[str, Any] = dict(
        st.session_state.get("filter_settings") or {},
    )
    merged_fs.update(
        {
            "year_min": year_min,
            "year_max": year_max,
            "rating_min": rating_min,
            "rating_max": rating_max,
            "score_min": score_min,
            "score_max": score_max,
            "overall_weight_alpha": overall_weight_alpha,
            "overall_weight_beta": overall_weight_beta,
            "overall_weight_gamma": overall_weight_gamma,
        },
    )
    p_freq, p_rare, _p_n = cached_load_plattenlabel_filter_buckets()
    p_all = sorted(set(p_freq) | set(p_rare))
    if p_all:
        p_ui = list(p_freq)
        if p_rare:
            p_ui.append(PLATTENLABEL_SONSTIGE_UI)
        raw_ui = st.session_state.get(FILTER_PLATTENLABEL_MULTISELECT_KEY, p_ui)
        merged_fs["plattenlabel_selection"] = expand_plattenlabel_ui_selection(
            list(raw_ui),
            p_rare,
        )
    else:
        merged_fs.pop("plattenlabel_selection", None)

    st.session_state["filter_settings"] = merged_fs
    st.session_state["community_weights_raw"] = raw_weights
    refresh_taste_wizard_after_filter_save()

    # ── CTA ──────────────────────────────────────────────────────
    st.markdown('<div class="filter-cta">', unsafe_allow_html=True)
    if has_step3_state():
        st.button(
            "Filter und Gewichte zurücksetzen",
            type="secondary",
            width="stretch",
            key="filter_flow_reset",
            on_click=reset_step3,
        )
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button(
            "Zurück zu Schritt 2",
            type="secondary",
            width="stretch",
            key="filter_flow_back_step2",
        ):
            st.switch_page("pages/1_Community_Auswahl.py")
    with col_next:
        if st.button(
            "Weiter",
            type="primary",
            width="stretch",
            key="filter_flow_continue_to_save_prompt",
        ):
            st.session_state[FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY] = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
