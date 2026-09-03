"""Weekly global-economy headlines and the week-ahead calendar, sourced via
the Claude Code CLI.

This is the one part of Finletter that uses an LLM, and only for the two prose
blocks that bracket the letter — the opening "general feel" summary and the
closing "Next week" look-ahead. The four data sections between them stay
strictly factual (see ``render.py``). We shell out to the ``claude``
command-line tool in non-interactive print mode, letting it use its built-in
web tools to find and synthesize the news.

Design notes:

- **Non-fatal.** Mirroring the data layer's philosophy (a flaky ticker never
  fails the run), any failure here — missing binary, timeout, empty/garbled
  output — yields an empty list. The letter simply omits that block.
- **Balanced by instruction.** The news prompt explicitly asks for a globally
  balanced set of headlines (regions *and* topics) rather than a US-centric or
  single-market view, to capture the general feel of the week's economy.
- **No new dependencies.** Uses only the stdlib ``subprocess``.

Configuration via environment:

- ``CLAUDE_BIN``           path to the Claude Code CLI (default ``claude``)
- ``NEWS_MODEL``          optional model id passed to ``claude --model``
- ``NEWS_TIMEOUT_SECONDS`` subprocess timeout (default ``300``)
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from datetime import date, timedelta

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 300

# Tools the CLI is allowed to use unattended. Web access is the whole point;
# nothing here touches the filesystem or shell.
_ALLOWED_TOOLS = ["WebSearch", "WebFetch"]

# Leading list markers we tolerate in the model's output: "-", "*", "•",
# "1.", "1)", optionally repeated/indented.
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")

# Separator between the date and the event text in a "Next week" bullet. The
# model is asked for " — " (em dash); we also accept an en dash or a plain
# hyphen surrounded by spaces, since models drift between them.
_EVENT_SPLIT = re.compile(r"\s+[—–-]\s+")


def _build_prompt(today: date, n: int) -> str:
    """The instruction handed to the CLI. Asks for a balanced global view."""
    return (
        f"Today is {today:%A, %B %d, %Y}. Using web search, identify the "
        f"{n} most important finance and macroeconomic news stories from the "
        "past week (roughly the last 7 days).\n\n"
        "Capture the general feel of the GLOBAL economy through the week. Do "
        "not skew toward any single market or region: aim for a balanced mix "
        "across regions (e.g. US, Europe, Asia) and across topics (central "
        "banks and interest rates, inflation, growth and employment, "
        "commodities and energy, currencies, and major market or corporate "
        "events). Prefer what genuinely moved or characterized the world "
        "economy this week over local or niche stories.\n\n"
        f"Output EXACTLY {n} bullet points, one per line, each starting with "
        "'- '. Keep each bullet to a single concise factual sentence. Do not "
        "add a preamble, headers, numbering, commentary, or closing remarks — "
        "output only the bullet lines."
    )


def _build_lookahead_prompt(today: date, n: int) -> str:
    """Instruction for the closing 'Next week' calendar block."""
    start = today + timedelta(days=1)
    end = today + timedelta(days=7)
    return (
        f"Today is {today:%A, %B %d, %Y}. Using web search, identify the "
        f"{n} most important scheduled economic and market events happening "
        f"between {start:%A, %B %d, %Y} and {end:%A, %B %d, %Y} inclusive.\n\n"
        "Consider central bank meetings and rate decisions (Fed, ECB, BoE, "
        "BoJ, Riksbank and peers), major macro data releases (jobs reports, "
        "CPI/inflation, GDP, PMIs), large or market-moving corporate earnings, "
        "and other scheduled events markets are positioned for (elections, "
        "OPEC meetings, major auctions or policy deadlines). Rank by how much "
        "the event is likely to move global markets, and keep the mix "
        "reasonably global rather than US-only. Only include events that are "
        "actually scheduled in that window — verify the date; do not guess or "
        "include anything already past.\n\n"
        f"Output EXACTLY {n} bullet points, one per line, in chronological "
        "order, each formatted exactly as:\n"
        "- Weekday, Month D — Event name: one concise factual clause on why "
        "it matters or what is expected.\n\n"
        "Do not add a preamble, headers, numbering, commentary, or closing "
        "remarks — output only the bullet lines."
    )


def _claude_command(prompt: str) -> list[str]:
    binary = os.environ.get("CLAUDE_BIN", "claude")
    cmd = [
        binary,
        "-p",  # print mode: run non-interactively and exit
        prompt,
        "--output-format",
        "text",
    ]
    # --allowedTools entries are passed as separate args so they survive
    # shell-free subprocess invocation verbatim.
    cmd += ["--allowedTools", *_ALLOWED_TOOLS]
    model = os.environ.get("NEWS_MODEL")
    if model:
        cmd += ["--model", model]
    return cmd


def _parse_bullets(output: str, n: int) -> list[str]:
    """Pull clean bullet text out of the CLI's stdout.

    Tolerant of stray blank lines and assorted list markers; returns at most
    ``n`` non-empty bullets with their leading markers stripped. If any lines
    carry a list marker we keep only those (dropping a stray preamble/footer);
    otherwise we fall back to every non-empty line.
    """
    marked: list[str] = []
    unmarked: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        if _BULLET_PREFIX.match(line):
            marked.append(_BULLET_PREFIX.sub("", line).strip())
        else:
            unmarked.append(line.strip())
    bullets = marked or unmarked
    return [b for b in bullets if b][:n]


def _run_claude(prompt: str, *, what: str, timeout: int | None) -> str | None:
    """Run the CLI in print mode and return stdout, or ``None`` on any failure.

    ``what`` is a short label used in log messages ("news summary", …). Never
    raises: every failure path is logged and reported as ``None`` so callers
    can degrade gracefully.
    """
    timeout = timeout or int(os.environ.get("NEWS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))

    cmd = _claude_command(prompt)
    if shutil.which(cmd[0]) is None:
        log.warning("Claude CLI %r not found on PATH; skipping %s.", cmd[0], what)
        return None

    log.info("Fetching %s via %s", what, cmd[0])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("%s timed out after %ds; skipping.", what.capitalize(), timeout)
        return None
    except OSError as exc:  # binary vanished between which() and exec, perms, etc.
        log.warning("Could not run Claude CLI: %s; skipping %s.", exc, what)
        return None

    if result.returncode != 0:
        log.warning(
            "Claude CLI exited %d; skipping %s. stderr: %s",
            result.returncode,
            what,
            (result.stderr or "").strip()[:500],
        )
        return None

    return result.stdout or ""


def fetch_news_bullets(
    today: date | None = None,
    *,
    n: int = 5,
    timeout: int | None = None,
) -> list[str]:
    """Return up to ``n`` global finance/macro headlines for the week.

    Always returns a list; an empty list signals "unavailable" so the caller
    can degrade gracefully (the summary block is simply skipped). Never raises.
    """
    today = today or date.today()
    output = _run_claude(
        _build_prompt(today, n), what="news summary", timeout=timeout
    )
    if output is None:
        return []

    bullets = _parse_bullets(output, n)
    if not bullets:
        log.warning("Claude CLI returned no usable bullets; skipping news summary.")
    else:
        log.info("Got %d news bullet(s) for the weekly summary.", len(bullets))
    return bullets


def fetch_lookahead_events(
    today: date | None = None,
    *,
    n: int = 3,
    timeout: int | None = None,
) -> list[tuple[str, str]]:
    """Return up to ``n`` ``(when, what)`` pairs for the coming week.

    ``when`` is the model's date string ("Wednesday, September 3"), ``what``
    the event description. If a bullet arrives without the expected date
    separator, ``when`` is empty and the whole bullet lands in ``what`` — the
    renderer handles both shapes. Always returns a list; empty means the
    "Next week" block is skipped. Never raises.
    """
    today = today or date.today()
    output = _run_claude(
        _build_lookahead_prompt(today, n), what="week-ahead calendar", timeout=timeout
    )
    if output is None:
        return []

    events: list[tuple[str, str]] = []
    for bullet in _parse_bullets(output, n):
        parts = _EVENT_SPLIT.split(bullet, maxsplit=1)
        if len(parts) == 2 and len(parts[0]) <= 40:
            events.append((parts[0].strip(), parts[1].strip()))
        else:
            events.append(("", bullet))

    if not events:
        log.warning("Claude CLI returned no usable events; skipping 'Next week'.")
    else:
        log.info("Got %d event(s) for the 'Next week' block.", len(events))
    return events
