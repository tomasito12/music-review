"""Filter und Gewichte (Schritt 3 von 3) -- zentriertes Karten-Layout."""

from __future__ import annotations

from typing import Any

import streamlit as st
from pages.page_helpers import (
    DEFAULT_PLATTENTESTS_RATING_FILTER_MAX,
    DEFAULT_PLATTENTESTS_RATING_FILTER_MIN,
    FILTER_PLATTENLABEL_MULTISELECT_KEY,
    PLATTENLABEL_SONSTIGE_UI,
    SEMANTIC_CHAT_INPUT_KEY,
    SEMANTIC_CHAT_MESSAGES_KEY,
    SEMANTIC_CHAT_RESET_BUTTON_KEY,
    SEMANTIC_RAG_MAX_DISTANCE_KEY,
    SEMANTIC_SEARCH_CHAT_AVATAR_CSS,
    SPECTRUM_CROSSOVER_STOPS,
    STYLE_MATCH_FILTER_PERCENT_STEP,
    clamp_plattentests_rating_filter_range,
    clamp_year_filter_bounds,
    collapse_plattenlabel_ui_selection,
    community_display_label,
    expand_plattenlabel_ui_selection,
    get_selected_communities,
    load_communities_res_10,
    load_genre_labels_res_10,
    load_plattenlabel_filter_buckets,
    max_release_year_from_corpus,
    min_release_year_from_corpus,
    normalize_filter_expander_vspace_gap,
    overall_weights_tradeoff_bar_html,
    render_toolbar,
    snap_spectrum_crossover,
    spectrum_crossover_option_label,
    style_match_percent_tuple_for_slider,
    style_match_scores_from_percent_slider,
)

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
    RECOMMENDATION_OVERALL_ALPHA,
    RECOMMENDATION_OVERALL_BETA,
    RECOMMENDATION_OVERALL_GAMMA,
    normalize_overall_weights,
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
        .filter-hint {
            max-width: 34rem;
            margin: 0 auto 1.1rem auto;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 0.8rem 1rem;
            font-size: 0.86rem;
            color: #44403c;
            line-height: 1.55;
            text-align: left;
        }
        .filter-hint strong { color: #991b1b; }
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
        /* Drei-Punkt-Skala über dem Stil-Präferenz-Slider */
        .spectrum-scale-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.65rem;
            font-size: 0.78rem;
            line-height: 1.38;
            color: #6b7280;
            margin: 0.15rem 0 0.35rem 0;
            max-width: 100%;
        }
        .spectrum-scale-row .spectrum-end {
            flex: 1;
            min-width: 0;
        }
        .spectrum-scale-row .spectrum-end--left { text-align: left; }
        .spectrum-scale-row .spectrum-end--right { text-align: right; }
        .spectrum-scale-row .spectrum-mid {
            flex: 0 0 auto;
            text-align: center;
            font-weight: 650;
            color: #4b5563;
            white-space: nowrap;
            padding: 0 0.25rem;
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
        .ow-tradeoff-wrap {
            margin: 1rem 0 0.75rem 0;
        }
        .ow-tradeoff-legend {
            font-size: 0.82rem;
            color: #6b7280;
            margin: 0 0 0.45rem 0;
            line-height: 1.45;
        }
        .ow-tradeoff-bar {
            display: flex;
            height: 14px;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            background: #f3f4f6;
        }
        .ow-tradeoff-seg {
            display: block;
            min-width: 0;
            height: 100%;
        }
        """
        + SEMANTIC_SEARCH_CHAT_AVATAR_CSS
        + """
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
    if "free_text_query" not in st.session_state:
        st.session_state["free_text_query"] = ""


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

    communities = load_communities_res_10()
    genre_labels = load_genre_labels_res_10()
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    st.markdown(
        '<p class="filter-section-caption filter-section-caption--lead">'
        "Vergebe pro Stil-Schwerpunkt einen Wert zwischen 0 und 1. "
        "Höhere Werte betonen diesen Schwerpunkt stärker in den Empfehlungen."
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
        top_artists_str = ", ".join(str(a) for a in top_artists[:2])
        comm_dict = c if isinstance(c, dict) else None
        base = community_display_label(cid, genre_labels, comm_dict)
        display_label = f"{base} ({top_artists_str})" if top_artists_str else base

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
    return raw_weights


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar -- Finetuning",
        page_icon=None,
        layout="centered",
    )

    _ensure_session_state()
    # Styles vor der Toolbar: so liegt der Hero direkt unter der Leiste wie
    # auf Schritt 1/2 (kein zusätzlicher Markdown-Block zwischen --- und Hero).
    _filter_css()
    render_toolbar("filter_flow")

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
        "werden sollen. Die Standardwerte liefern bereits gute "
        "Ergebnisse - passe nur an, was du bewusst verändern möchtest."
        "</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="filter-hint">'
        "<strong>Tipp:</strong> Die Voreinstellungen funktionieren gut "
        "als Startpunkt. Du kannst jederzeit hierher zurückkehren "
        "und nachjustieren."
        "</div>",
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
        year_floor = min_release_year_from_corpus()
        year_cap = max_release_year_from_corpus()
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
            )
        with col_rating:
            rating_min, rating_max = st.slider(
                "Rating (plattentests.de)",
                min_value=0,
                max_value=10,
                value=(rating_min_default, rating_max_default),
                step=1,
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
        freq_labels, rare_labels, _n_rev = load_plattenlabel_filter_buckets()
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
        _filter_vertical_space("md")

        # ── Stil-Präferenz ───────────────────────────────────
        st.markdown(
            '<div class="filter-section accent-weight">'
            '<p class="filter-section-label">Stil-Präferenz</p>',
            unsafe_allow_html=True,
        )
        _filter_vertical_space("sm")
        st.markdown(
            '<div class="spectrum-scale-row">'
            '<span class="spectrum-end spectrum-end--left">'
            "Klare Präferenz:<br>"
            "<strong>ein</strong> gewählter Stil dominiert"
            "</span>"
            '<span class="spectrum-mid">Ausgewogen</span>'
            '<span class="spectrum-end spectrum-end--right">'
            "Breite Präferenz:<br>"
            "<strong>möglichst viele</strong> gewählte Stilrichtungen zugleich"
            "</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        _filter_vertical_space("sm")
        crossover_default = snap_spectrum_crossover(
            existing_settings.get(
                "community_spectrum_crossover",
                RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
            ),
        )
        community_spectrum_crossover = float(
            st.select_slider(
                "Stil-Präferenz (Auswahl)",
                options=list(SPECTRUM_CROSSOVER_STOPS),
                value=crossover_default,
                format_func=spectrum_crossover_option_label,
                label_visibility="collapsed",
                help=(
                    "**Stufen:** links starker Fokus auf **einen** gewählten "
                    "Stil, rechts **möglichst viele** gewählte Stile zugleich; "
                    "**Ausgewogen** in der Mitte.\n\n"
                    "Wie stark das insgesamt ins Ranking einfließt, steuert "
                    "**gamma** (Abschnitt darunter); bei gamma = 0 wirkt diese "
                    "Einstellung nicht."
                ),
            ),
        )
        st.markdown(
            '<p class="filter-section-caption">'
            "Reine Bedeutungs-Skala (fünf Stufen, keine Zahlen). "
            "Voreinstellung: <strong>Ausgewogen</strong>. Im Gesamtscore "
            "wirkt das über <strong>gamma</strong> (Abschnitt darunter)."
            "</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        _filter_vertical_space("xl")

        # ── Gewichtung des Gesamtscores ─────────────────────────
        st.markdown(
            '<div class="filter-section accent-weight">'
            '<p class="filter-section-label">Gewichtung des Gesamtscores</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="filter-section-caption filter-section-caption--lead">'
            "Die drei Regler stehen für <strong>relative Wichtigkeit</strong>. "
            "Zusammen bestimmen sie zu 100&nbsp;% den Einfluss auf den "
            "Gesamtscore (vor der Sortierung werden die Anteile automatisch "
            "normalisiert)."
            "</p>",
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
            help=(
                "Hohe Werte betonen die Bewertung von plattentests.de "
                "im Gesamtscore (fehlende Ratings werden mit einem "
                "Standardwert angenommen)."
            ),
        )
        _filter_vertical_space("sm")
        st.markdown(
            '<p class="filter-weight-question">'
            "Wie wichtig ist dir bei der Sortierung, ob Alben eher einem "
            "Stil klar zuzuordnen sind oder mehrere deiner gewählten "
            "Fein-Genres abdecken? (Unabhängig von der Bedeutungs-Skala "
            "weiter oben: die steuert nur die Richtung; hier steuerst du, "
            "wie stark dieser Aspekt insgesamt zählt.)"
            "</p>",
            unsafe_allow_html=True,
        )
        overall_weight_gamma = st.slider(
            "Relative Wichtigkeit: Stil-Präferenz im Score",
            min_value=0.0,
            max_value=1.0,
            value=min(1.0, max(0.0, ow_g_def)),
            step=0.05,
            help=(
                "Steuert, wie stark der Spektrum-Term ins Gewicht fällt "
                "(Zusammenspiel aus Fokus auf einen Stil vs. Abdeckung "
                "mehrerer Stile, passend zur Bedeutungs-Skala oben). "
                "Bei 0 wirkst du diesen Teil des Scores ab."
            ),
        )
        ah, bh, gh = normalize_overall_weights(
            overall_weight_alpha,
            overall_weight_beta,
            overall_weight_gamma,
        )
        st.markdown(
            overall_weights_tradeoff_bar_html(ah, bh, gh),
            unsafe_allow_html=True,
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

    with st.expander("Semantische Suche"):
        st.markdown(
            '<div class="filter-expander-desc-wrap" '
            'style="text-align:center;width:100%;">'
            '<p class="filter-desc" style="text-align:center;margin-left:auto;'
            'margin-right:auto;max-width:34rem;">'
            "Beschreibe Stimmung, Klang oder Inhalte. Auf der Seite "
            "<strong>Empfehlungen</strong> erscheinen darauf passende Alben "
            "(Schnittmenge mit deiner Rangliste und weitere semantische "
            "Treffer)."
            "</p></div>",
            unsafe_allow_html=True,
        )
        _filter_vertical_space("md")

        chat_reset = st.button(
            "Chat zurücksetzen",
            key=SEMANTIC_CHAT_RESET_BUTTON_KEY,
        )
        if chat_reset:
            st.session_state["free_text_query"] = ""
            st.session_state[SEMANTIC_CHAT_MESSAGES_KEY] = []

        chat_messages = st.session_state.get(SEMANTIC_CHAT_MESSAGES_KEY)
        if not isinstance(chat_messages, list):
            chat_messages = []
        if not chat_messages:
            chat_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Kannst du mir beschreiben, nach welcher Musik du "
                        "gerade suchst?"
                    ),
                }
            ]

        chat_input = st.chat_input(
            "Stimmung oder Inhalte beschreiben …",
            key=SEMANTIC_CHAT_INPUT_KEY,
        )
        if chat_input is not None:
            chat_input_clean = chat_input.strip()
            st.session_state["free_text_query"] = chat_input_clean
            if chat_input_clean:
                chat_messages.append({"role": "user", "content": chat_input_clean})
                chat_messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Alles klar - ich passe die Trefferliste "
                            "an deine Beschreibung an."
                        ),
                    },
                )
        st.session_state[SEMANTIC_CHAT_MESSAGES_KEY] = chat_messages

        for msg in chat_messages:
            role = msg.get("role")
            content = msg.get("content")
            if role not in {"assistant", "user"}:
                continue
            if not isinstance(content, str):
                continue
            with st.chat_message(role):
                st.markdown(content)

        q_show = (st.session_state.get("free_text_query") or "").strip()
        if q_show:
            st.caption(f"**Aktuelle Freitext-Suche:** {q_show}")

        free_text_semantic = (st.session_state.get("free_text_query") or "").strip()
        st.slider(
            "Ähnlichkeit (niedriger = passender)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.05,
            disabled=not bool(free_text_semantic),
            key=SEMANTIC_RAG_MAX_DISTANCE_KEY,
        )

    # ── Session State speichern ──────────────────────────────────
    # Sortierung/Serendipity: Empfehlungsseite; Freitext-Strategie fest B (kein UI).
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
            "community_spectrum_crossover": community_spectrum_crossover,
            "overall_weight_alpha": overall_weight_alpha,
            "overall_weight_beta": overall_weight_beta,
            "overall_weight_gamma": overall_weight_gamma,
            "rag_query_strategy": "B",
        },
    )
    p_freq, p_rare, _p_n = load_plattenlabel_filter_buckets()
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

    # ── CTA ──────────────────────────────────────────────────────
    st.markdown('<div class="filter-cta">', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Zurück", width="stretch"):
            st.switch_page("pages/1_Community_Auswahl.py")
    with col_next:
        if st.button(
            "Empfehlungen anzeigen",
            type="primary",
            width="stretch",
        ):
            st.switch_page("pages/6_Recommendations_Flow.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
