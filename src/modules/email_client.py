import email as email_lib
import imaplib
import os
import re
import smtplib
import sys
from email.header import decode_header
from email.message import EmailMessage, Message
from html import unescape
from typing import cast

from dotenv import load_dotenv

from src.modules._client import get_lang
from src.retry import call_with_retry

load_dotenv()

IMAP_TIMEOUT_SECONDS = 10
SMTP_TIMEOUT_SECONDS = 10
MAX_BODY_CHARS = 5000
DEFAULT_MAILBOX = "INBOX"

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_BLOCK_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)

REQUIRED_IMAP_VARS = ("EMAIL_IMAP_HOST", "EMAIL_ADDRESS", "EMAIL_PASSWORD")
REQUIRED_SMTP_VARS = ("EMAIL_SMTP_HOST", "EMAIL_ADDRESS", "EMAIL_PASSWORD")

FIELDS = {
    "uid": {"fr": "uid", "en": "uid"},
    "from": {"fr": "de", "en": "from"},
    "subject": {"fr": "objet", "en": "subject"},
    "body": {"fr": "corps", "en": "body"},
}

_MISSING_ENV_VARS_MESSAGES = {
    "fr": (
        "Variables d'environnement manquantes: {names}. Copie .env.example en .env et "
        "renseigne ces valeurs."
    ),
    "en": (
        "Missing environment variables: {names}. Copy .env.example to .env and set these values."
    ),
}
_TRUNCATED_SUFFIX = {"fr": "\n[...tronque...]", "en": "\n[...truncated...]"}
_IMAP_CONNECT_FAILED_MESSAGES = {
    "fr": "Echec de connexion IMAP: {exc}",
    "en": "IMAP connection failed: {exc}",
}
_IMAP_SEARCH_FAILED_MESSAGES = {
    "fr": "Echec de la recherche IMAP des messages non lus",
    "en": "IMAP search for unread messages failed",
}
_IMAP_READ_FAILED_MESSAGES = {
    "fr": "Echec de la lecture des messages: {exc}",
    "en": "Failed to read messages: {exc}",
}
_IGNORED_MESSAGE_WARNING = {
    "fr": "[email-check] avertissement, message ignore: {failure}",
    "en": "[email-check] warning, message skipped: {failure}",
}
_MARK_AS_READ_FAILED_MESSAGES = {
    "fr": "Echec du marquage comme lu: {exc}",
    "en": "Failed to mark as read: {exc}",
}
_SEND_EMAIL_FAILED_MESSAGES = {
    "fr": "Echec de l'envoi de l'email: {exc}",
    "en": "Failed to send the email: {exc}",
}


class EmailClientError(RuntimeError):
    pass


def _get_env(names: tuple[str, ...], lang: str | None = None) -> dict[str, str]:
    lang = get_lang(lang)
    values = {name: os.environ.get(name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise EmailClientError(_MISSING_ENV_VARS_MESSAGES[lang].format(names=", ".join(missing)))
    return {name: cast(str, value) for name, value in values.items()}


def _decode_header_value(raw_value: str) -> str:
    if not raw_value:
        return ""
    parts = decode_header(raw_value)
    decoded = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _html_to_text(html: str) -> str:
    html = _HTML_BLOCK_RE.sub(" ", html)
    text = unescape(_HTML_TAG_RE.sub(" ", html))
    return re.sub(r"[ \t]+", " ", text).strip()


def _decode_part(part: Message) -> str | None:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return None
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_body(message: Message, lang: str | None = None) -> str:
    lang = get_lang(lang)
    plain_body = ""
    html_body = ""

    if message.is_multipart():
        for part in message.walk():
            if "attachment" in str(part.get("Content-Disposition", "")):
                continue
            content_type = part.get_content_type()
            if content_type == "text/plain" and not plain_body:
                plain_body = _decode_part(part) or ""
            elif content_type == "text/html" and not html_body:
                html_body = _decode_part(part) or ""
    elif message.get_content_type() == "text/html":
        html_body = _decode_part(message) or ""
    else:
        plain_body = _decode_part(message) or ""

    body = plain_body.strip() or _html_to_text(html_body)

    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + _TRUNCATED_SUFFIX[lang]
    return body.strip()


def _connect_imap(mailbox: str, lang: str | None = None) -> imaplib.IMAP4_SSL:
    lang = get_lang(lang)
    values = _get_env(REQUIRED_IMAP_VARS, lang=lang)
    host = values["EMAIL_IMAP_HOST"]
    port = int(os.environ.get("EMAIL_IMAP_PORT") or "993")

    def _connect() -> imaplib.IMAP4_SSL:
        connection = imaplib.IMAP4_SSL(host, port, timeout=IMAP_TIMEOUT_SECONDS)
        connection.login(values["EMAIL_ADDRESS"], values["EMAIL_PASSWORD"])
        connection.select(mailbox)
        return connection

    try:
        return call_with_retry(_connect, is_retryable=lambda exc: isinstance(exc, OSError))
    except (OSError, imaplib.IMAP4.error) as exc:
        raise EmailClientError(_IMAP_CONNECT_FAILED_MESSAGES[lang].format(exc=exc)) from exc


def fetch_unread(
    mailbox: str = DEFAULT_MAILBOX, max_messages: int = 10, lang: str | None = None
) -> list[dict]:
    lang = get_lang(lang)
    connection = _connect_imap(mailbox, lang=lang)
    messages = []
    failures = []
    try:
        status, data = connection.search(None, "UNSEEN")
        if status != "OK":
            raise EmailClientError(_IMAP_SEARCH_FAILED_MESSAGES[lang])

        uids = data[0].split()[:max_messages]
        for uid in uids:
            try:
                status, msg_data = connection.fetch(uid, "(RFC822)")
                item = msg_data[0] if msg_data else None
                if status != "OK" or not isinstance(item, tuple) or not isinstance(item[1], bytes):
                    continue
                raw = item[1]
                parsed = email_lib.message_from_bytes(raw)
                messages.append(
                    {
                        FIELDS["uid"][lang]: uid.decode(),
                        FIELDS["from"][lang]: _decode_header_value(parsed.get("From", "")),
                        FIELDS["subject"][lang]: _decode_header_value(parsed.get("Subject", "")),
                        FIELDS["body"][lang]: _extract_body(parsed, lang=lang),
                    }
                )
            except (imaplib.IMAP4.error, LookupError, ValueError, TypeError) as exc:
                failures.append(f"{uid.decode(errors='replace')}: {exc}")
    except imaplib.IMAP4.error as exc:
        raise EmailClientError(_IMAP_READ_FAILED_MESSAGES[lang].format(exc=exc)) from exc
    finally:
        connection.logout()

    for failure in failures:
        print(_IGNORED_MESSAGE_WARNING[lang].format(failure=failure), file=sys.stderr)

    return messages


def mark_as_read(uids: list[str], mailbox: str = DEFAULT_MAILBOX, lang: str | None = None) -> None:
    lang = get_lang(lang)
    if not uids:
        return

    connection = _connect_imap(mailbox, lang=lang)
    try:
        for uid in uids:
            connection.store(uid, "+FLAGS", "\\Seen")
    except imaplib.IMAP4.error as exc:
        raise EmailClientError(_MARK_AS_READ_FAILED_MESSAGES[lang].format(exc=exc)) from exc
    finally:
        connection.logout()


def send_email(to: str, subject: str, body: str, lang: str | None = None) -> None:
    lang = get_lang(lang)
    values = _get_env(REQUIRED_SMTP_VARS, lang=lang)
    host = values["EMAIL_SMTP_HOST"]
    port = int(os.environ.get("EMAIL_SMTP_PORT") or "587")

    message = EmailMessage()
    message["From"] = values["EMAIL_ADDRESS"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    def _send() -> None:
        with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as connection:
            connection.starttls()
            connection.login(values["EMAIL_ADDRESS"], values["EMAIL_PASSWORD"])
            connection.send_message(message)

    def _is_transient(exc: Exception) -> bool:
        # smtplib.SMTPException herite d'OSError en Python 3 : sans cette
        # exclusion, un echec d'authentification serait retente pour rien.
        return isinstance(exc, OSError) and not isinstance(exc, smtplib.SMTPException)

    try:
        call_with_retry(_send, is_retryable=_is_transient)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailClientError(_SEND_EMAIL_FAILED_MESSAGES[lang].format(exc=exc)) from exc
