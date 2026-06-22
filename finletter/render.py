"""HTML (and plain-text) assembly from predefined templates.

Strictly factual: every string is a fixed template filled with numbers — no
generated prose, per the spec. The HTML uses inline CSS for email-client
compatibility and references the two charts by CID.
"""

from __future__ import annotations

import base64
from datetime import date
from html import escape as html_escape

Ranked = list[tuple[str, float]]

# CIDs used both here (img src) and by the emailer to attach the images.
REGION_CHART_CID = "region_rotation"
SECTOR_CHART_CID = "sector_rotation"

_CSS_TABLE = (
    "border-collapse:collapse;width:100%;max-width:560px;"
    "font-family:Arial,Helvetica,sans-serif;font-size:14px;margin:8px 0 20px;"
)
_CSS_TH = "text-align:left;padding:6px 10px;background:#f0f0f0;border-bottom:2px solid #ddd;"
_CSS_TD = "padding:6px 10px;border-bottom:1px solid #eee;"


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _color(value: float) -> str:
    return "#2e7d32" if value >= 0 else "#c62828"


def _document(body: str) -> str:
    """Wrap the body in a minimal HTML document declaring UTF-8.

    Without a charset declaration, browsers (and some mail clients) guess the
    encoding when opening the file/message and decode our UTF-8 bytes — en/em
    dashes, curly quotes — as Windows-1252, producing mojibake like ``â€“``.
    The ``<meta charset>`` pins it to UTF-8.
    """
    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"</head><body>{body}</body></html>"
    )


def _h2(text: str) -> str:
    return (
        f'<h2 style="font-family:Arial,Helvetica,sans-serif;font-size:18px;'
        f'margin:28px 0 6px;">{text}</h2>'
    )


def _news_block(bullets: list[str]) -> str:
    """Opening 'general feel of the global economy' summary as a bullet list."""
    items = "".join(
        f'<li style="margin:0 0 6px;">{html_escape(b)}</li>' for b in bullets
    )
    return (
        f"{_h2('This week in the global economy')}"
        f'<ul style="font-family:Arial,Helvetica,sans-serif;font-size:14px;'
        f'line-height:1.5;color:#222;margin:8px 0 20px;padding-left:20px;">'
        f"{items}</ul>"
    )


def _rotation_table(ranked: Ranked, label_header: str) -> str:
    rows = "".join(
        f'<tr><td style="{_CSS_TD}">{i}. {label}</td>'
        f'<td style="{_CSS_TD}color:{_color(ret)};text-align:right;font-weight:bold;">'
        f"{_pct(ret)}</td></tr>"
        for i, (label, ret) in enumerate(ranked, start=1)
    )
    return (
        f'<table style="{_CSS_TABLE}">'
        f'<tr><th style="{_CSS_TH}">{label_header}</th>'
        f'<th style="{_CSS_TH}text-align:right;">Weekly return</th></tr>'
        f"{rows}</table>"
    )


def _winners_losers_table(region: str, top: Ranked, bottom: Ranked) -> str:
    def block(title: str, rows: Ranked) -> str:
        body = "".join(
            f'<tr><td style="{_CSS_TD}">{label}</td>'
            f'<td style="{_CSS_TD}color:{_color(ret)};text-align:right;font-weight:bold;">'
            f"{_pct(ret)}</td></tr>"
            for label, ret in rows
        )
        return (
            f'<table style="{_CSS_TABLE}">'
            f'<tr><th style="{_CSS_TH}">{title}</th>'
            f'<th style="{_CSS_TH}text-align:right;">Weekly return</th></tr>'
            f"{body}</table>"
        )

    return (
        f'<h3 style="font-family:Arial,Helvetica,sans-serif;font-size:15px;'
        f'margin:18px 0 4px;">{region}</h3>'
        f"{block('Top performers', top)}"
        f"{block('Bottom performers', bottom)}"
    )


def render_html(
    *,
    as_of: date,
    region_rotation: Ranked,
    region_currency_note: str,
    sector_rotation: Ranked,
    cap_tiers: Ranked,
    region_winners_losers: dict[str, tuple[Ranked, Ranked]],
    missing: list[str],
    news_bullets: list[str] | None = None,
) -> str:
    """Assemble the full HTML email body."""
    parts: list[str] = []
    parts.append(
        '<div style="max-width:600px;margin:0 auto;color:#222;">'
        f'<h1 style="font-family:Arial,Helvetica,sans-serif;font-size:22px;margin:0 0 2px;">'
        f"Finletter</h1>"
        f'<p style="font-family:Arial,Helvetica,sans-serif;color:#666;font-size:13px;margin:0 0 8px;">'
        f'Week ending {as_of:%A, %B %-d, %Y}</p>'
    )

    # Opening "general feel" summary, when available (omitted on fetch failure).
    if news_bullets:
        parts.append(_news_block(news_bullets))

    parts.append(_h2("Region rotation"))
    parts.append(
        f'<p style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#666;margin:0 0 4px;">'
        f"{region_currency_note}</p>"
    )
    parts.append(f'<img src="cid:{REGION_CHART_CID}" alt="Region rotation" style="max-width:100%;">')
    parts.append(_rotation_table(region_rotation, "Region"))

    parts.append(_h2("US sector rotation"))
    parts.append(f'<img src="cid:{SECTOR_CHART_CID}" alt="Sector rotation" style="max-width:100%;">')
    parts.append(_rotation_table(sector_rotation, "Sector"))

    parts.append(_h2("US market-cap tiers"))
    parts.append(_rotation_table(cap_tiers, "Tier"))

    parts.append(_h2("Regional winners & losers"))
    for region, (top, bottom) in region_winners_losers.items():
        parts.append(_winners_losers_table(region, top, bottom))

    if missing:
        parts.append(
            f'<p style="font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#999;'
            f'margin-top:24px;border-top:1px solid #eee;padding-top:8px;">'
            f"Data unavailable this week for: {', '.join(missing)}.</p>"
        )

    parts.append("</div>")
    return _document("".join(parts))


def inline_images(html: str, images: dict[str, bytes]) -> str:
    """Replace ``cid:`` image references with self-contained base64 data URIs.

    Used for the on-disk ``--out`` preview, where there are no MIME parts to
    resolve ``cid:`` against. The emailed version keeps ``cid:`` references,
    which are more reliably rendered by mail clients than large data URIs.
    """
    for cid, png in images.items():
        b64 = base64.b64encode(png).decode("ascii")
        html = html.replace(f"cid:{cid}", f"data:image/png;base64,{b64}")
    return html


def render_text(
    *,
    as_of: date,
    region_rotation: Ranked,
    sector_rotation: Ranked,
    cap_tiers: Ranked,
    region_winners_losers: dict[str, tuple[Ranked, Ranked]],
    missing: list[str],
    news_bullets: list[str] | None = None,
) -> str:
    """Plain-text fallback for clients that don't render HTML."""
    lines = [f"Finletter — week ending {as_of:%A, %B %-d, %Y}", ""]

    def ranked_lines(ranked: Ranked) -> list[str]:
        return [f"  {i}. {label}: {_pct(ret)}" for i, (label, ret) in enumerate(ranked, 1)]

    if news_bullets:
        lines += ["THIS WEEK IN THE GLOBAL ECONOMY"]
        lines += [f"  - {b}" for b in news_bullets]
        lines += [""]

    lines += ["REGION ROTATION (local currency)"] + ranked_lines(region_rotation) + [""]
    lines += ["US SECTOR ROTATION"] + ranked_lines(sector_rotation) + [""]
    lines += ["US MARKET-CAP TIERS"] + ranked_lines(cap_tiers) + [""]
    lines += ["REGIONAL WINNERS & LOSERS"]
    for region, (top, bottom) in region_winners_losers.items():
        lines.append(f"  {region}")
        lines.append("    Top:")
        lines += [f"      {label}: {_pct(ret)}" for label, ret in top]
        lines.append("    Bottom:")
        lines += [f"      {label}: {_pct(ret)}" for label, ret in bottom]
    if missing:
        lines += ["", f"Data unavailable: {', '.join(missing)}"]
    return "\n".join(lines)
