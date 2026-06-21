"""SMTP delivery of the rendered email with inline chart images.

Credentials and addressing come from the environment (loaded from ``.env`` by
the entrypoint):

- ``SMTP_HOST``           default ``smtp.gmail.com``
- ``SMTP_PORT``           default ``465`` (implicit TLS / SMTP_SSL)
- ``SMTP_USER``           Gmail address used to authenticate
- ``SMTP_APP_PASSWORD``   Gmail app password (not the account password)
- ``MAIL_FROM``           From header; defaults to ``SMTP_USER``
- ``MAIL_TO``             recipient address
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


class EmailConfigError(RuntimeError):
    """Raised when required SMTP environment variables are missing."""


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EmailConfigError(f"Missing required environment variable: {name}")
    return value


def send(
    *,
    subject: str,
    html: str,
    text: str,
    images: dict[str, bytes],
) -> None:
    """Send a multipart/related email. ``images`` maps CID -> PNG bytes."""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = _require("SMTP_USER")
    password = _require("SMTP_APP_PASSWORD")
    mail_from = os.environ.get("MAIL_FROM", user)
    mail_to = _require("MAIL_TO")

    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = mail_from
    root["To"] = mail_to

    alt = MIMEMultipart("alternative")
    root.attach(alt)
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))

    for cid, png in images.items():
        img = MIMEImage(png, _subtype="png")
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
        root.attach(img)

    log.info("Sending email to %s via %s:%d", mail_to, host, port)
    with smtplib.SMTP_SSL(host, port) as server:
        server.login(user, password)
        server.sendmail(mail_from, [mail_to], root.as_string())
    log.info("Email sent.")
