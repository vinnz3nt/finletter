"""Pure analysis helpers over weekly-return dicts. No I/O.

Two operations cover all four email sections:
- :func:`rank_rotation` — order a label->return mapping best-to-worst.
- :func:`winners_losers` — top-N and bottom-N from a return mapping.

Tickers whose return is ``None`` (data unavailable) are excluded from rankings
and reported separately via :func:`missing_tickers`.
"""

from __future__ import annotations

Ranked = list[tuple[str, float]]


def _clean(returns: dict[str, float | None]) -> dict[str, float]:
    return {k: v for k, v in returns.items() if v is not None}


def missing_tickers(returns: dict[str, float | None]) -> list[str]:
    """Tickers with no usable data this week."""
    return [k for k, v in returns.items() if v is None]


def rank_rotation(returns: dict[str, float | None]) -> Ranked:
    """Return ``[(label, ret), ...]`` sorted by return, descending."""
    return sorted(_clean(returns).items(), key=lambda kv: kv[1], reverse=True)


def winners_losers(returns: dict[str, float | None], n: int = 3) -> tuple[Ranked, Ranked]:
    """Return ``(top_n, bottom_n)`` from a return mapping, each sorted desc.

    Bottom-N is ordered worst-first so the steepest loser leads the losers list.
    If fewer than ``2*n`` names have data, the two slices may overlap; callers
    with small universes should account for that (regions here have ~15).
    """
    ranked = rank_rotation(returns)
    top = ranked[:n]
    bottom = list(reversed(ranked[-n:])) if ranked else []
    return top, bottom
