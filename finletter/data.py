"""Data fetching and weekly-return computation via yfinance.

The single public entry point is :func:`fetch_weekly_returns`. It batches a
download for a list of tickers and returns ``{ticker: weekly_return_or_None}``.
A ``None`` means data was missing or insufficient — callers should treat that as
"unavailable" and keep going rather than failing the whole run, since yfinance
coverage of some European/Swedish tickers is occasionally flaky.
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from . import config

log = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 3


def _start_of_week(today: date) -> date:
    """Monday of the week containing ``today``."""
    return today - timedelta(days=today.weekday())


def _weekly_return_from_series(closes: pd.Series, week_start: date) -> float | None:
    """Compute (last close / last close before this week's Monday) - 1.

    ``closes`` is a date-indexed Series of daily closing prices. Returns None if
    there is no usable prior-week close or current close.
    """
    closes = closes.dropna()
    if closes.empty:
        return None

    # Normalize index to plain dates for comparison.
    idx_dates = pd.to_datetime(closes.index).date
    prior = [c for d, c in zip(idx_dates, closes.values) if d < week_start]
    current = closes.values[-1]

    if not prior or current is None:
        return None
    prior_close = prior[-1]
    if prior_close in (None, 0):
        return None
    return float(current) / float(prior_close) - 1.0


def _download(tickers: list[str]) -> pd.DataFrame | None:
    """Batched yfinance download with retries. Returns the raw DataFrame."""
    period = f"{config.WEEK_LOOKBACK_DAYS}d"
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            df = yf.download(
                tickers,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            if df is not None and not df.empty:
                return df
            log.warning("Empty download (attempt %d/%d)", attempt, _MAX_ATTEMPTS)
        except Exception as exc:  # noqa: BLE001 — yfinance raises a variety of errors
            log.warning("Download failed (attempt %d/%d): %s", attempt, _MAX_ATTEMPTS, exc)
        if attempt < _MAX_ATTEMPTS:
            time.sleep(_RETRY_BACKOFF_SECONDS)
    return None


def _closes_for_ticker(df: pd.DataFrame, ticker: str, single: bool) -> pd.Series | None:
    """Extract the Close column for one ticker from a (possibly multiindex) df."""
    try:
        if single:
            return df["Close"]
        # group_by="ticker" => columns are a MultiIndex (ticker, field).
        return df[ticker]["Close"]
    except (KeyError, TypeError):
        return None


def fetch_weekly_returns(tickers: list[str], today: date | None = None) -> dict[str, float | None]:
    """Return ``{ticker: weekly_return}`` for each requested ticker.

    Weekly return = last available close / last close before the current week's
    Monday - 1. Missing/insufficient data yields ``None`` for that ticker.
    """
    if not tickers:
        return {}
    today = today or date.today()
    week_start = _start_of_week(today)

    df = _download(tickers)
    if df is None:
        log.error("All download attempts failed for %d tickers", len(tickers))
        return {t: None for t in tickers}

    single = len(tickers) == 1
    results: dict[str, float | None] = {}
    for ticker in tickers:
        closes = _closes_for_ticker(df, ticker, single)
        if closes is None:
            results[ticker] = None
            continue
        results[ticker] = _weekly_return_from_series(closes, week_start)
    return results
