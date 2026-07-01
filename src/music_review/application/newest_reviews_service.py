"""Newest-review ranking service independent of Streamlit session state."""

from __future__ import annotations

import logging
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from music_review.application.models import TasteProfile
from music_review.application.recommendation_service import (
    RES_KEY,
    selected_communities_from_profile,
)
from music_review.dashboard.preference_ranking import (
    global_breadth_norm_by_review_id,
    global_style_fit_norm_for_profile,
    preference_ranked_rows,
)
from music_review.domain.models import Review

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NewestReviewsInputs:
    """All data needed to rank the latest review batch."""

    newest_reviews: Sequence[Review]
    affinity_by_review_id: Mapping[int, Mapping[str, Any]]
    memberships: dict[str, dict[str, str]]


@dataclass(frozen=True, slots=True)
class NewestReviewsService:
    """Rank a latest-review batch for one taste profile."""

    inputs: NewestReviewsInputs
    logger: logging.Logger = field(default=LOGGER)

    def compute_ranked_rows(
        self,
        profile: TasteProfile,
        *,
        rng: random.Random | None = None,
        apply_serendipity: bool = False,
        global_breadth_norm: Mapping[int, float] | None = None,
        global_style_fit_norm: Mapping[int, float] | None = None,
    ) -> list[dict[str, Any]] | None:
        """Return preference-ranked newest rows, or None without taste input."""
        selected_comms = selected_communities_from_profile(profile)
        if not selected_comms:
            self.logger.info(
                "newest_reviews_ranked_rows: skipped "
                "(no selected communities; uniform album weights). n_reviews=%s",
                len(self.inputs.newest_reviews),
            )
            return None

        breadth_norm = (
            dict(global_breadth_norm)
            if global_breadth_norm is not None
            else self.compute_global_breadth_norm()
        )
        style_fit_norm = (
            dict(global_style_fit_norm)
            if global_style_fit_norm is not None
            else self.compute_global_style_fit_norm(profile)
        )
        rows = preference_ranked_rows(
            self.inputs.newest_reviews,
            affinity_by_review_id=self.inputs.affinity_by_review_id,
            memberships=self.inputs.memberships,
            selected_comms=selected_comms,
            weights_raw=profile.community_weights_raw,
            filter_settings=profile.filter_settings.to_dict(),
            rng=rng,
            apply_serendipity=apply_serendipity,
            global_breadth_norm_by_review_id=breadth_norm,
            global_style_fit_norm_by_review_id=style_fit_norm,
        )
        self.logger.info(
            "newest_reviews_ranked_rows: applied n_reviews=%s n_ranked_rows=%s "
            "n_selected_communities=%s",
            len(self.inputs.newest_reviews),
            len(rows),
            len(selected_comms),
        )
        self.logger.debug(
            "newest_reviews_ranked_rows: selected_community_ids=%s "
            "filter_settings_keys=%s n_community_weights=%s",
            sorted(selected_comms),
            sorted(profile.filter_settings.to_dict().keys()),
            len(profile.community_weights_raw),
        )
        return rows

    def compute_global_breadth_norm(self) -> dict[int, float]:
        """Return corpus-wide style-breadth percentile norms."""
        return global_breadth_norm_by_review_id(self.inputs.affinity_by_review_id)

    def compute_global_style_fit_norm(self, profile: TasteProfile) -> dict[int, float]:
        """Return corpus-wide style-fit percentile norms for one profile."""
        selected_comms = selected_communities_from_profile(profile)
        if not selected_comms:
            return {}
        return global_style_fit_norm_for_profile(
            self.inputs.affinity_by_review_id,
            selected_comms=selected_comms,
            weights_raw=profile.community_weights_raw,
        )


__all__ = ["RES_KEY", "NewestReviewsInputs", "NewestReviewsService"]
