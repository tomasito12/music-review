from __future__ import annotations

import html
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from pages.page_helpers import (
    get_selected_communities,
    inject_recommendation_flow_shell_css,
    recommendation_card_community_tags_html,
    recommendation_card_meta_parts,
    render_toolbar,
)
from pages.recommendations_pool import (
    SORT_MODE_FIXED,
    SORT_MODE_MIGRATION,
    SORT_MODE_RANDOM,
    compute_recommendations,
)

from music_review.config import (
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
)
from music_review.dashboard.recommendations_flow_pagination import (
    DEFAULT_RECOMMENDATIONS_PAGE_SIZE,
    RECOMMENDATIONS_PAGE_SIZE_CHOICES,
    clamp_recommendation_page,
    count_albums_on_next_page,
    parse_page_size_choice,
    recommendation_page_slice_bounds,
    recommendation_total_pages,
    streamlit_parent_scroll_to_anchor_html,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    default_profiles_dir,
    load_profile,
)

REC_PAGE_SIZE_SELECT_OPTIONS: tuple[str, ...] = (
    *(str(n) for n in RECOMMENDATIONS_PAGE_SIZE_CHOICES),
    "Alle",
)
REC_PAGE_SIZE_DEFAULT_INDEX = RECOMMENDATIONS_PAGE_SIZE_CHOICES.index(
    DEFAULT_RECOMMENDATIONS_PAGE_SIZE
)

# Streamlit widget keys: keep centralized to avoid accidental duplicates.
KEY_START_WORKFLOW_BUTTON = "rec_start_workflow_button"
KEY_PAGE_SIZE_PREV = "rec_page_size_prev"
KEY_REC_PAGE = "rec_results_page_1based"
KEY_SCROLL_REC_LIST = "rec_scroll_to_list_after_page_change"
LEGACY_KEY_VISIBLE_COUNT = "rec_visible_count"

_REC_LIST_SCROLL_ANCHOR_ID = "music-review-rec-list-top"


_REC_PAGE_SIZE_HEADING_CSS = """
        .rec-sort-section-label.rec-page-size-heading {
            margin-top: 1.35rem;
        }
        .rec-list-scroll-anchor {
            scroll-margin-top: 1rem;
        }
"""


def _recommendations_css() -> None:
    inject_recommendation_flow_shell_css(
        include_chat_avatar_style=False,
        extra_rules=_REC_PAGE_SIZE_HEADING_CSS,
    )


def _inject_scroll_to_recommendation_list() -> None:
    """Nach Seitenwechsel zum Anfang der Ergebnisliste scrollen."""
    components.html(
        streamlit_parent_scroll_to_anchor_html(
            anchor_element_id=_REC_LIST_SCROLL_ANCHOR_ID,
        ),
        height=0,
    )


def _render_sort_settings_widgets_and_persist() -> None:
    """Ranglisten-Modus und Zufallsanteil; schreibt in ``filter_settings``.

    Erwartet einen umgebenden Container (z. B. ``st.container(border=True)``).
    """
    fs: dict[str, Any] = dict(st.session_state.get("filter_settings") or {})
    st.markdown(
        '<p class="rec-sort-section-label">Sortierung und Zufall</p>',
        unsafe_allow_html=True,
    )
    col_sort, col_ser = st.columns(2)
    with col_sort:
        sm_raw = str(fs.get("sort_mode", SORT_MODE_FIXED))
        sm_def = SORT_MODE_MIGRATION.get(sm_raw, sm_raw)
        sort_mode = st.selectbox(
            "Reihenfolge",
            options=[SORT_MODE_FIXED, SORT_MODE_RANDOM],
            index=0 if sm_def == SORT_MODE_FIXED else 1,
            help=(
                "Feste Reihenfolge: Alben werden strikt nach "
                "Score sortiert. Mit Zufall: Die Liste wird etwas "
                "durchgemischt, damit du auch Alben entdeckst, "
                "die sonst weiter unten stehen."
            ),
        )
    with col_ser:
        ser_def = float(fs.get("serendipity", 0.0))
        serendipity = st.slider(
            "Zufallsanteil (0 = stabil, 1 = stark gemischt)",
            min_value=0.0,
            max_value=1.0,
            value=ser_def,
            step=0.1,
            disabled=(sort_mode != SORT_MODE_RANDOM),
            help=(
                "Bestimmt, wie stark die Liste durchgemischt wird. "
                "0 bedeutet kaum Veränderung, 1 mischt die "
                "Reihenfolge fast komplett zufällig durch."
            ),
        )
    fs["sort_mode"] = sort_mode
    fs["serendipity"] = serendipity
    fs["rag_query_strategy"] = "B"
    st.session_state["filter_settings"] = fs


def main() -> None:
    render_toolbar("recommendations")
    _recommendations_css()

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Deine Empfehlungen</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Basierend auf deinen gewählten Stil-Schwerpunkten '
        "und Filtereinstellungen.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        _render_sort_settings_widgets_and_persist()
        recs = compute_recommendations()

        if not recs:
            st.markdown(
                '<div class="rec-callout rec-callout-warn">'
                "Es konnten keine passenden Alben auf Basis der aktuellen Auswahl "
                "und Filter gefunden werden. Du kannst die Filter zurücknehmen oder "
                "andere Stil-Schwerpunkte wählen."
                "</div>",
                unsafe_allow_html=True,
            )
            st.page_link(
                "pages/5_Filter_Flow.py",
                label="Zurück zu den Filtern",
                use_container_width=True,
            )
            return

        st.markdown(
            '<p class="rec-sort-section-label rec-page-size-heading">'
            "Anzahl der gleichzeitig angezeigten Alben</p>",
            unsafe_allow_html=True,
        )
        size_label = st.selectbox(
            "Alben pro Ladung",
            options=REC_PAGE_SIZE_SELECT_OPTIONS,
            index=REC_PAGE_SIZE_DEFAULT_INDEX,
            key="rec_page_size_select",
            label_visibility="collapsed",
        )
        st.markdown(f"{len(recs)} Alben entsprechen aktuell deinen Kriterien.")
    page_size = parse_page_size_choice(size_label)
    prev_ps: int | None = st.session_state.get(KEY_PAGE_SIZE_PREV)
    if prev_ps != page_size:
        st.session_state.pop(KEY_REC_PAGE, None)
        st.session_state.pop(LEGACY_KEY_VISIBLE_COUNT, None)
    st.session_state[KEY_PAGE_SIZE_PREV] = page_size

    if (
        KEY_REC_PAGE not in st.session_state
        and LEGACY_KEY_VISIBLE_COUNT in st.session_state
        and page_size is not None
        and page_size > 0
    ):
        legacy_raw = st.session_state.get(LEGACY_KEY_VISIBLE_COUNT)
        if isinstance(legacy_raw, (int, float)):
            legacy_vis = int(legacy_raw)
            migrated = max(1, (legacy_vis + page_size - 1) // page_size)
            st.session_state[KEY_REC_PAGE] = migrated
        st.session_state.pop(LEGACY_KEY_VISIBLE_COUNT, None)

    selected_comms = get_selected_communities()

    def _render_filter_cards(
        rec_list: list[dict[str, Any]],
        *,
        rank_start: int = 1,
    ) -> None:
        for idx, rec in enumerate(rec_list):
            rank = rank_start + idx
            artist = rec.get("artist") or ""
            album = rec.get("album") or ""
            url = rec.get("url") or ""
            rating = rec.get("rating")
            year = rec.get("year")
            labels = rec.get("labels") or ""
            overall = float(rec.get("overall_score") or 0.0)
            top_comms = rec.get("top_communities") or []

            snippet_source = rec.get("text") or ""
            snippet = snippet_source[:260] + (
                "..." if len(snippet_source) > 260 else ""
            )

            title = f"{html.escape(str(artist))} — {html.escape(str(album))}"
            if url:
                la = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
                title_html = f'<a {la} class="rec-title">{title}</a>'
            else:
                title_html = f'<span class="rec-title">{title}</span>'
            rank_html = (
                f'<span class="rec-rank" aria-label="Platz {rank}">{rank}</span>'
            )

            meta_parts = recommendation_card_meta_parts(
                rec.get("release_date"),
                year,
                rating,
                overall,
                labels,
                default_rating=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
            )
            meta_html = html.escape(" · ".join(meta_parts))

            card = '<div class="rec-card">'
            card += f'<div class="rec-header">{rank_html}{title_html}</div>'
            if meta_html:
                card += f'<div class="rec-meta">{meta_html}</div>'
            if top_comms:
                card += recommendation_card_community_tags_html(
                    top_comms,
                    filter_selected_community_ids=selected_comms,
                )
            if snippet:
                card += (
                    '<div class="rec-excerpt">'
                    f"{html.escape(snippet).replace(chr(10), '<br>')}"
                    "</div>"
                )
            card += "</div>"
            st.markdown(card, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Rangliste (filter-based ranking), seitenweise
    # ------------------------------------------------------------------
    if page_size is None:
        _render_filter_cards(recs)
    else:
        total_pages = recommendation_total_pages(total=len(recs), page_size=page_size)
        raw_page = st.session_state.get(KEY_REC_PAGE)
        page_one = int(raw_page) if raw_page is not None else 1
        page_one = clamp_recommendation_page(page_one, total_pages)
        st.session_state[KEY_REC_PAGE] = page_one
        start_idx, end_idx = recommendation_page_slice_bounds(
            page_one_based=page_one,
            page_size=page_size,
            total=len(recs),
        )
        st.markdown(
            f'<div id="{html.escape(_REC_LIST_SCROLL_ANCHOR_ID)}" '
            'class="rec-list-scroll-anchor"></div>',
            unsafe_allow_html=True,
        )
        _render_filter_cards(
            recs[start_idx:end_idx],
            rank_start=start_idx + 1,
        )
        if st.session_state.pop(KEY_SCROLL_REC_LIST, False):
            _inject_scroll_to_recommendation_list()
        st.caption(f"Seite {page_one} von {total_pages}")
        prev_col, next_col = st.columns(2)
        with prev_col:
            if page_one > 1 and st.button(
                "Vorherige Seite",
                key="rec_page_prev",
            ):
                st.session_state[KEY_REC_PAGE] = page_one - 1
                st.session_state[KEY_SCROLL_REC_LIST] = True
                st.rerun()
        with next_col:
            if page_one < total_pages:
                n_next = count_albums_on_next_page(
                    current_page_one_based=page_one,
                    page_size=page_size,
                    total=len(recs),
                )
                next_page_num = page_one + 1
                if st.button(
                    "Zeige nächste "
                    f"{n_next} Alben (Seite {next_page_num} von {total_pages})",
                    key="rec_page_next",
                ):
                    st.session_state[KEY_REC_PAGE] = next_page_num
                    st.session_state[KEY_SCROLL_REC_LIST] = True
                    st.rerun()

    st.markdown("---")
    col_back, col_start = st.columns([1, 1])
    with col_back:
        st.page_link(
            "pages/5_Filter_Flow.py",
            label="Filter anpassen",
            use_container_width=True,
        )
    with col_start:
        if st.button("Von vorn beginnen", key=KEY_START_WORKFLOW_BUTTON):
            saved_slug = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.clear()
            if saved_slug is not None:
                st.session_state[ACTIVE_PROFILE_SESSION_KEY] = saved_slug
                loaded = load_profile(default_profiles_dir(), str(saved_slug))
                if loaded is not None:
                    apply_profile_to_session(st.session_state, loaded)
            st.switch_page("pages/0b_Einstieg.py")


if __name__ == "__main__":
    main()
