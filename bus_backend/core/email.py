"""
Email sending helpers (SMTP).

Uses the standard library `smtplib` so no extra dependency is required.
All connection details are read from settings (which load from the `.env`
file / environment) — nothing is hardcoded.

Gmail setup:
    1. Enable 2-Step Verification on the Google account.
    2. Create an "App Password": Google Account -> Security -> App passwords.
    3. Put that 16-character App Password in the `.env` file as SMTP_PASSWORD.
       (Do NOT use your normal Gmail login password, and never commit it.)
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from bus_backend.core.settings import get_settings

logger = logging.getLogger(__name__)


def send_email(to_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email via SMTP using STARTTLS (e.g. Gmail on port 587).

    Raises on failure so the caller can decide how to handle it. The
    forgot-password route deliberately swallows that error and still returns
    the same safe message to the user.
    """
    settings = get_settings()

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def send_password_reset_email(to_address: str, token: str) -> None:
    """Build and send the password-reset email for the given token."""
    settings = get_settings()

    reset_link = f"{settings.frontend_url}/reset-password.html?token={token}"

    subject = "Reset your password"
    body = (
        "Hi,\n\n"
        "We received a request to reset the password for your account.\n"
        "Click the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        "This link will expire in 30 minutes.\n\n"
        "If you did not request a password reset, you can safely ignore "
        "this email — your password will not be changed.\n"
    )

    send_email(to_address, subject, body)
