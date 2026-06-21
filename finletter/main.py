"""Finletter entrypoint: fetch -> analyze -> chart -> render -> send.

Run once per invocation (cron drives the weekly schedule). Examples::

    python -m finletter.main                  # fetch + send the email
    python -m finletter.main --no-send --out out.html   # local preview, no SMTP
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from dotenv import load_dotenv

from . import analysis, charts, config, data, emailer, render

log = logging.getLogger("finletter")


def _build_report(today: date) -> dict:
    """Fetch everything and assemble the structured pieces the renderer needs."""
    # --- Section 1: region rotation (local currency) -------------------------
    index_tickers = [meta["ticker"] for meta in config.REGION_INDICES.values()]
    index_returns = data.fetch_weekly_returns(index_tickers, today)
    region_rotation_raw: dict[str, float | None] = {}
    for region, meta in config.REGION_INDICES.items():
        label = f"{region} — {meta['name']} ({meta['currency']})"
        region_rotation_raw[label] = index_returns.get(meta["ticker"])
    region_rotation = analysis.rank_rotation(region_rotation_raw)

    # --- Section 2: US sector rotation ---------------------------------------
    sector_returns = data.fetch_weekly_returns(list(config.SECTOR_ETFS), today)
    sector_named = {config.SECTOR_ETFS[t]: r for t, r in sector_returns.items()}
    sector_rotation = analysis.rank_rotation(sector_named)

    # --- Section 3: US market-cap tiers --------------------------------------
    cap_returns = data.fetch_weekly_returns(list(config.CAP_TIER_ETFS), today)
    cap_named = {config.CAP_TIER_ETFS[t]: r for t, r in cap_returns.items()}
    cap_tiers = analysis.rank_rotation(cap_named)

    # --- Section 4: per-region winners & losers ------------------------------
    # One batched download across all regions, then split by region.
    all_constituents = sorted(
        {t for tickers in config.REGION_CONSTITUENTS.values() for t in tickers}
    )
    constituent_returns = data.fetch_weekly_returns(all_constituents, today)

    region_winners_losers: dict[str, tuple] = {}
    missing: list[str] = analysis.missing_tickers(index_returns)
    for region, tickers in config.REGION_CONSTITUENTS.items():
        region_returns = {t: constituent_returns.get(t) for t in tickers}
        missing += analysis.missing_tickers(region_returns)
        region_winners_losers[region] = analysis.winners_losers(region_returns, n=3)

    currencies = ", ".join(
        dict.fromkeys(meta["currency"] for meta in config.REGION_INDICES.values())
    )
    return {
        "as_of": today,
        "region_rotation": region_rotation,
        "region_currency_note": f"Each region in its own local currency ({currencies}).",
        "sector_rotation": sector_rotation,
        "cap_tiers": cap_tiers,
        "region_winners_losers": region_winners_losers,
        "missing": sorted(set(missing)),
    }


def run(no_send: bool = False, out: str | None = None, today: date | None = None) -> int:
    today = today or date.today()
    report = _build_report(today)

    images = {
        render.REGION_CHART_CID: charts.bar_chart(
            report["region_rotation"], "Region rotation (local currency)"
        ),
        render.SECTOR_CHART_CID: charts.bar_chart(
            report["sector_rotation"], "US sector rotation"
        ),
    }

    html = render.render_html(
        as_of=report["as_of"],
        region_rotation=report["region_rotation"],
        region_currency_note=report["region_currency_note"],
        sector_rotation=report["sector_rotation"],
        cap_tiers=report["cap_tiers"],
        region_winners_losers=report["region_winners_losers"],
        missing=report["missing"],
    )
    text = render.render_text(
        as_of=report["as_of"],
        region_rotation=report["region_rotation"],
        sector_rotation=report["sector_rotation"],
        cap_tiers=report["cap_tiers"],
        region_winners_losers=report["region_winners_losers"],
        missing=report["missing"],
    )

    if out:
        # Embed charts as data URIs so the on-disk preview is self-contained.
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(render.inline_images(html, images))
        log.info("Wrote HTML preview to %s", out)

    if report["missing"]:
        log.warning("Data unavailable for: %s", ", ".join(report["missing"]))

    if no_send:
        log.info("--no-send set; skipping email.")
        return 0

    subject = f"Finletter — week ending {today:%b %-d, %Y}"
    emailer.send(subject=subject, html=html, text=text, images=images)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()

    parser = argparse.ArgumentParser(description="Send the weekly Finletter email.")
    parser.add_argument("--no-send", action="store_true", help="Skip SMTP delivery.")
    parser.add_argument("--out", metavar="PATH", help="Write rendered HTML to PATH.")
    args = parser.parse_args()

    return run(no_send=args.no_send, out=args.out)


if __name__ == "__main__":
    raise SystemExit(main())
