"""Hilfsfunktionen für die Empfehlungsliste (Seitenweise Anzeige)."""

from __future__ import annotations

import json

# Standard wie bisher im Recommendations Flow (pages/6_Recommendations_Flow.py).
DEFAULT_RECOMMENDATIONS_PAGE_SIZE: int = 25

# Werte für die Auswahl „Alben pro Ladung“ (Streamlit-UI).
RECOMMENDATIONS_PAGE_SIZE_CHOICES: tuple[int, ...] = (10, 25, 50, 100, 200)


def recommendation_total_pages(*, total: int, page_size: int) -> int:
    """Anzahl Seiten bei fester Seitengröße (mindestens 1, wenn total > 0)."""
    if total <= 0:
        return 1
    if page_size <= 0:
        return 1
    return (total + page_size - 1) // page_size


def recommendation_page_slice_bounds(
    *,
    page_one_based: int,
    page_size: int,
    total: int,
) -> tuple[int, int]:
    """0-basierte halboffene Grenzen ``[start, end)`` für die aktuelle Seite.

    Jede Seite zeigt nur ihr Fenster (keine kumulative Liste).
    """
    if total <= 0 or page_size <= 0 or page_one_based <= 0:
        return 0, 0
    start = (page_one_based - 1) * page_size
    if start >= total:
        return total, total
    end = min(start + page_size, total)
    return start, end


def clamp_recommendation_page(page_one_based: int, total_pages: int) -> int:
    """Seitenindex 1-basiert in den gültigen Bereich klemmen."""
    if total_pages <= 0:
        return 1
    return max(1, min(page_one_based, total_pages))


def count_albums_on_next_page(
    *,
    current_page_one_based: int,
    page_size: int,
    total: int,
) -> int:
    """Anzahl Alben auf der folgenden Seite (für Button-Text)."""
    if total <= 0 or page_size <= 0:
        return 0
    _start, end = recommendation_page_slice_bounds(
        page_one_based=current_page_one_based,
        page_size=page_size,
        total=total,
    )
    remaining = total - end
    return max(0, min(page_size, remaining))


def streamlit_parent_scroll_to_anchor_html(*, anchor_element_id: str) -> str:
    """HTML mit Skript: im Elternfenster zum Anker scrollen (für ``components.html``).

    Läuft im Iframe-Kontext von Streamlit und nutzt ``window.parent.document``.
    """
    id_js = json.dumps(anchor_element_id)
    return f"""<script>
(function () {{
    const doc = window.parent.document;
    const anchor = doc.getElementById({id_js});
    if (anchor) {{
        anchor.scrollIntoView({{ block: "start", behavior: "instant" }});
        return;
    }}
    const main =
        doc.querySelector('[data-testid="stAppViewContainer"]') ||
        doc.querySelector("section.main");
    if (main) {{
        main.scrollTo({{ top: 0, behavior: "instant" }});
    }}
}})();
</script>"""


def parse_page_size_choice(label: str) -> int | None:
    """Wandelt die Auswahl aus dem Selectbox-Label in ``int`` oder ``None`` (alle)."""
    stripped = label.strip()
    if stripped.casefold() == "alle":
        return None
    return int(stripped)
