"""Shared CSS for recommendation and filter flow pages."""

from __future__ import annotations

from pages._streamlit_ctx import st

OVERALL_WEIGHT_TRADEOFF_RED_LIGHT = "#fca5a5"
OVERALL_WEIGHT_TRADEOFF_RED_MID = "#dc2626"
OVERALL_WEIGHT_TRADEOFF_RED_DARK = "#7f1d1d"


_REC_FLOW_SHELL_CHAT_AVATAR_CSS = """
        div[data-testid="chatAvatarIcon-assistant"] {
            background-color: #fef2f2 !important;
            color: #991b1b !important;
        }
"""

# Shared by Empfehlungen (6) and Neueste Rezensionen (8); keep in sync visually.
_RECOMMENDATION_FLOW_SHELL_CSS_BASE = """
        .rec-hero {
            text-align: center;
            padding: 0.5rem 0 0.15rem 0;
        }
        .rec-page-title {
            font-size: 1.6rem;
            font-weight: 650;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        div[data-testid="stMarkdownContainer"] #rec-page-desc-wrap {
            text-align: center !important;
            width: 100% !important;
            box-sizing: border-box;
            margin: 0 0 1.3rem 0 !important;
        }
        div[data-testid="stMarkdownContainer"] #rec-page-desc-wrap .rec-page-desc {
            color: #6b7280;
            font-size: 0.9rem;
            max-width: 34rem;
            margin: 0 auto !important;
            text-align: center !important;
            line-height: 1.55;
        }
        .rec-sort-section-label {
            font-size: 0.92rem;
            font-weight: 650;
            color: #111827;
            margin-bottom: 0.55rem;
        }
        .rec-card {
            background: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .rec-card:hover {
            border-color: #fca5a5;
            box-shadow: 0 4px 8px rgba(220, 38, 38, 0.08);
        }
        .rec-card-rag {
            border: 1px solid #fca5a5;
            background: #fef2f2;
        }
        .rec-header {
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            flex-wrap: wrap;
        }
        a.rec-title,
        a.rec-title:link,
        a.rec-title:visited,
        div[data-testid="stMarkdownContainer"] a.rec-title {
            font-size: 1.08rem;
            font-weight: 600;
            text-decoration: none;
            color: #1f2937 !important;
            letter-spacing: -0.01em;
        }
        a.rec-title:hover,
        div[data-testid="stMarkdownContainer"] a.rec-title:hover {
            text-decoration: underline;
            color: #dc2626 !important;
        }
        a.rec-title:active,
        div[data-testid="stMarkdownContainer"] a.rec-title:active {
            color: #991b1b !important;
        }
        .rec-meta {
            font-size: 0.8rem;
            color: #6b7280;
            margin-bottom: 0.40rem;
        }
        .rec-communities {
            font-size: 0.78rem;
            color: #4b5563;
            margin-bottom: 0.35rem;
        }
        .rec-comm-tag {
            display: inline-flex;
            align-items: center;
            padding: 0.10rem 0.45rem;
            margin: 0 0.25rem 0.25rem 0;
            border-radius: 999px;
            border: 1px solid transparent;
            font-size: 0.78rem;
            white-space: nowrap;
        }
        .rec-comm-tag.rec-comm-tag--filtered {
            box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.22),
                0 0 0 3px rgba(0, 0, 0, 0.06);
        }
        .rec-excerpt {
            font-size: 0.86rem;
            line-height: 1.5;
            color: #4b5563;
        }
        .rec-rank {
            font-variant-numeric: tabular-nums;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 1.8rem;
            height: 1.45rem;
            padding: 0 0.4rem;
            border-radius: 6px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 0.55rem;
            flex-shrink: 0;
        }
        .rec-pane-header {
            margin: -0.15rem 0 0.85rem 0;
            padding: 0.2rem 0 0.85rem 0.85rem;
            border-bottom: 1px solid rgba(220, 38, 38, 0.2);
        }
        .rec-pane-header-filter {
            border-left: 3px solid #dc2626;
        }
        .rec-pane-header-semantic {
            border-left: 3px solid #7f1d1d;
            border-bottom-color: rgba(127, 29, 29, 0.2);
        }
        .rec-eyebrow {
            font-size: 0.65rem;
            font-weight: 650;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.28rem;
        }
        .rec-pane-header-semantic .rec-eyebrow {
            color: #991b1b;
        }
        .rec-pane-title {
            font-size: 1.02rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #0f172a;
            line-height: 1.3;
        }
        .rec-pane-sub {
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 0.45rem;
            line-height: 1.45;
        }
        .rec-results-divider {
            margin: 1rem 0 0.65rem 0;
            padding-top: 0.85rem;
            border-top: 1px dashed rgba(220, 38, 38, 0.25);
        }
        .rec-results-label {
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.35rem;
        }
        .rec-results-title {
            font-size: 0.92rem;
            font-weight: 600;
            color: #991b1b;
            letter-spacing: -0.01em;
        }
        .rec-callout {
            font-size: 0.84rem;
            color: #57534e;
            background: #fafaf9;
            border: 1px solid #e7e5e4;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            line-height: 1.5;
            margin: 0.35rem 0 0.5rem 0;
        }
        .rec-callout-warn {
            background: #fff1f2;
            border-color: #fda4af;
            color: #881337;
        }
        .rec-callout-info {
            background: #fef2f2;
            border-color: #fecaca;
            color: #991b1b;
        }
"""


def recommendation_flow_shell_css_rules(
    *,
    include_chat_avatar_style: bool = False,
    extra_rules: str = "",
) -> str:
    """Return CSS rules for the shared recommendation / newest-reviews card shell."""
    parts: list[str] = [_RECOMMENDATION_FLOW_SHELL_CSS_BASE.strip()]
    if include_chat_avatar_style:
        parts.append(_REC_FLOW_SHELL_CHAT_AVATAR_CSS.strip())
    extra = extra_rules.strip()
    if extra:
        parts.append(extra)
    return "\n".join(parts)


def inject_recommendation_flow_shell_css(
    *,
    include_chat_avatar_style: bool = False,
    extra_rules: str = "",
) -> None:
    """Inject shared shell styles into the active Streamlit page."""
    rules = recommendation_flow_shell_css_rules(
        include_chat_avatar_style=include_chat_avatar_style,
        extra_rules=extra_rules,
    )
    st.markdown(f"<style>\n{rules}\n</style>", unsafe_allow_html=True)
