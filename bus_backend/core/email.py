"""
Email sending helpers (Resend).

Uses the Resend Python SDK (HTTPS API) instead of SMTP, which works on
hosts that block outbound SMTP (e.g. Render).

Configuration is read from settings (which load from `.env` / environment):
    RESEND_API_KEY — API key from the Resend dashboard
    EMAIL_FROM     — verified sender address (e.g. "App <noreply@yourdomain.com>")
    FRONTEND_URL   — base URL for password-reset links
"""

from __future__ import annotations

import logging

import resend

from bus_backend.core.settings import get_settings

logger = logging.getLogger(__name__)


def send_email(to_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email via Resend.

    Raises on failure so the caller can decide how to handle it. The
    forgot-password route deliberately swallows that error and still returns
    the same safe message to the user.
    """
    settings = get_settings()

    resend.api_key = settings.resend_api_key

    params: resend.Emails.SendParams = {
        "from": settings.email_from,
        "to": [to_address],
        "subject": subject,
        "text": body,
    }

    resend.Emails.send(params)


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
