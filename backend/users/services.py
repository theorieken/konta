"""Account email delivery and one-time password-link creation."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from base.models import Setting
from base.settings_registry import (
    EMAIL_FROM_ADDRESS,
    EMAIL_HOST,
    EMAIL_HOST_PASSWORD,
    EMAIL_HOST_USER,
    EMAIL_PORT,
    EMAIL_USE_TLS,
)
from users.models import User


class EmailDeliveryError(RuntimeError):
    """Raised when account email cannot be delivered."""


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _email_connection(*, household=None):
    host = str(Setting.get(EMAIL_HOST, "", household=household) or "").strip()
    if not host:
        if settings.DEBUG:
            return get_connection("django.core.mail.backends.console.EmailBackend")
        raise EmailDeliveryError("Der E-Mail-Server ist noch nicht konfiguriert.")

    try:
        port = int(Setting.get(EMAIL_PORT, 587, household=household) or 587)
    except (TypeError, ValueError) as exc:
        raise EmailDeliveryError("Der E-Mail-Port ist ungültig.") from exc

    return get_connection(
        "django.core.mail.backends.smtp.EmailBackend",
        host=host,
        port=port,
        username=str(Setting.get(EMAIL_HOST_USER, "", household=household) or "") or None,
        password=str(Setting.get(EMAIL_HOST_PASSWORD, "", household=household) or "") or None,
        use_tls=_as_bool(Setting.get(EMAIL_USE_TLS, True, household=household)),
        fail_silently=False,
    )


def password_link_url(token: str) -> str:
    """Build the browser URL from DOMAIN, SCHEME and PORT in `.env`."""
    return f"{settings.PUBLIC_URL.rstrip('/')}/reset-password/{token}"


def send_password_link(user: User, purpose: str) -> str:
    """Issue and send a fresh one-time link, invalidating any earlier link."""
    token = user.issue_password_link(purpose)
    url = password_link_url(token)
    invitation = purpose == User.PasswordLinkPurpose.INVITATION
    subject = "Einladung zur Finanzplanung" if invitation else "Passwort zurücksetzen"
    intro = (
        "Du wurdest zur gemeinsamen Finanzplanung eingeladen."
        if invitation
        else "Für dein Konto wurde ein neues Passwort angefordert."
    )
    action = "Passwort festlegen" if invitation else "Passwort zurücksetzen"
    body = (
        f"Hallo {user.display_name},\n\n"
        f"{intro}\n\n"
        f"{action}: {url}\n\n"
        "Der Link ist nur einmal verwendbar und läuft automatisch ab. "
        "Wenn du diese Nachricht nicht erwartet hast, kannst du sie ignorieren.\n"
    )
    household = user.current_household
    from_email = str(
        Setting.get(
            EMAIL_FROM_ADDRESS, "finanzplanung@localhost", household=household
        )
    )
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[user.email],
        connection=_email_connection(household=household),
    )
    try:
        sent = message.send()
    except Exception as exc:
        raise EmailDeliveryError("Die E-Mail konnte nicht versendet werden.") from exc
    if sent != 1:
        raise EmailDeliveryError("Die E-Mail konnte nicht versendet werden.")
    return url
