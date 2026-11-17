"""Generic ranking helpers for the recommendation engine."""
from __future__ import annotations

from typing import Any, Callable, Hashable, Sequence


def rank_top_n(
    candidates: Sequence[Any],
    *,
    key_fn: Callable[[Any], Hashable],
    score_fn: Callable[[Any], float],
    limit: int,
) -> list[Any]:
    """Sort by score descending, dedupe by key (keep highest score), take top N."""
    if limit <= 0:
        return []
    best: dict[Hashable, Any] = {}
    for c in candidates:
        k = key_fn(c)
        if k not in best or score_fn(c) > score_fn(best[k]):
            best[k] = c
    ranked = sorted(best.values(), key=score_fn, reverse=True)
    return ranked[:limit]