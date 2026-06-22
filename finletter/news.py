"""Weekly global-economy headlines, sourced via the Claude Code CLI.

This is the one part of Finletter that uses an LLM, and only for the opening
"general feel" summary at the top of the letter — the four data sections below
it stay strictly factual (see ``render.py``). We shell out to the ``claude``
command-line tool in non-interactive print mode, letting it use its built-in
web tools to find and synthesize the week's most important finance/macro news.

Design notes:

- **Non-fatal.** Mirroring the data layer's philosophy (a flaky ticker never
  fails the run), any failure here — missing binary, timeout, empty/garbled
  output — yields an empty list. The letter simply omits the summary block.
- **Balanced by instruction.** The prompt explicitly asks for a globally
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
from datetime import date

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 300

# Tools the CLI is allowed to use unattended. Web access is the whole point;
# nothing here touches the filesystem or shell.
_ALLOWED_TOOLS = ["WebSearch", "WebFetch"]

# Leading list markers we tolerate in the model's output: "-", "*", "•",
# "1.", "1)", optionally repeated/indented.
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


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
    timeout = timeout or int(os.environ.get("NEWS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))

    cmd = _claude_command(_build_prompt(today, n))
    if shutil.which(cmd[0]) is None:
        log.warning("Claude CLI %r not found on PATH; skipping news summary.", cmd[0])
        return []

    log.info("Fetching weekly news summary via %s", cmd[0])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("News summary timed out after %ds; skipping.", timeout)
        return []
    except OSError as exc:  # binary vanished between which() and exec, perms, etc.
        log.warning("Could not run Claude CLI: %s; skipping news summary.", exc)
        return []

    if result.returncode != 0:
        log.warning(
            "Claude CLI exited %d; skipping news summary. stderr: %s",
            result.returncode,
            (result.stderr or "").strip()[:500],
        )
        return []

    bullets = _parse_bullets(result.stdout or "", n)
    if not bullets:
        log.warning("Claude CLI returned no usable bullets; skipping news summary.")
    else:
        log.info("Got %d news bullet(s) for the weekly summary.", len(bullets))
    return bullets
