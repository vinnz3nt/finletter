"""Bar charts rendered to PNG bytes for inline email embedding.

Uses the headless Agg backend (no display needed on the Raspberry Pi). Charts
are returned as raw PNG bytes and embedded via CID by :mod:`finletter.emailer`;
nothing is written to disk.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # headless — must be set before pyplot import
import matplotlib.pyplot as plt  # noqa: E402

_GAIN = "#2e7d32"
_LOSS = "#c62828"


def bar_chart(ranked: list[tuple[str, float]], title: str) -> bytes:
    """Horizontal bar chart of ``[(label, return), ...]``, best at the top.

    Returns are plotted as percentages; gains are green, losses red.
    """
    labels = [label for label, _ in ranked]
    values = [ret * 100 for _, ret in ranked]
    colors = [_GAIN if v >= 0 else _LOSS for v in values]

    fig, ax = plt.subplots(figsize=(7, max(2.0, 0.45 * len(ranked) + 0.8)), dpi=110)
    y = range(len(labels))
    ax.barh(list(y), values, color=colors)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # best performer on top
    ax.axvline(0, color="#999999", linewidth=0.8)
    ax.set_xlabel("Weekly return (%)")
    ax.set_title(title, fontweight="bold")

    for i, v in enumerate(values):
        ax.text(
            v + (0.05 if v >= 0 else -0.05),
            i,
            f"{v:+.2f}%",
            va="center",
            ha="left" if v >= 0 else "right",
            fontsize=8,
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
