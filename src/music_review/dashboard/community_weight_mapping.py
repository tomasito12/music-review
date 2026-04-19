"""Map stereo-style bias controls to stored per-community weights in ``[0, 1]``."""

from __future__ import annotations


def community_weight_stored_from_bias(bias: float) -> float:
    """Convert UI bias in ``[-1, 1]`` to a stored weight in ``[0, 1]``.

    Center bias ``0`` maps to ``0.5`` (neutral stored weight). Endpoints ``-1``
    and ``+1`` map to ``0`` and ``1``.
    """
    b = max(-1.0, min(1.0, float(bias)))
    return (b + 1.0) / 2.0


def community_weight_bias_from_stored(stored: float) -> float:
    """Convert stored weight in ``[0, 1]`` to UI bias in ``[-1, 1]``.

    Out-of-range values are clamped before mapping.
    """
    w = max(0.0, min(1.0, float(stored)))
    return 2.0 * w - 1.0
