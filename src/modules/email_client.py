import email as email_lib
import imaplib
import os
import re
import smtplib
import sys
from email.header import decode_header
from email.message import EmailMessage, Message
from html import unescape

from dotenv import load_dotenv

load_dotenv()

IMAP_TIMEOUT_SECONDS = 10
SMTP_TIMEOUT_SECONDS = 10
MAX_BODY_CHARS = 5000
DEFAULT_MAILBOX = "INBOX"

_HTML_TAG_RE = re.compile(r"<[^>]+>")

REQUIRED_IMAP_VARS = ("EMAIL_IMAP_HOST", "EMAIL_ADDRESS", "EMAIL_PASSWORD")
REQUIRED_SMTP_VARS = ("EMAIL_SMTP_HOST", "EMAIL_ADDRESS", "EMAIL_PASSWORD")


class EmailClientError(RuntimeError):
    pass


def _get_env(names: tuple[str, ...]) -> dict[str, str]:
    values = {name: os.environ.get(name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise EmailClientError(
            f"Variables d'environnement manquantes: {', '.join(missing)}. "
            "Copie .env.example en .env et renseigne ces valeurs."
        )
    return values


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
    return unescape(_HTML_TAG_RE.sub(" ", html)).strip()


def _decode_part(part: Message) -> str | None:
    payload = part.get_payload(decode=True)
    if payload is None:
        return None
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_body(message: Message) -> str:
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

    body = (plain_body.strip() or _html_to_text(html_body))

    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n[...tronque...]"
    return body.strip()


def _connect_imap(mailbox: str) -> imaplib.IMAP4_SSL:
    values = _get_env(REQUIRED_IMAP_VARS)
    host = values["EMAIL_IMAP_HOST"]
    port = int(os.environ.get("EMAIL_IMAP_PORT", "993"))
    try:
        connection = imaplib.IMAP4_SSL(host, port, timeout=IMAP_TIMEOUT_SECONDS)
        connection.login(values["EMAIL_ADDRESS"], values["EMAIL_PASSWORD"])
        connection.select(mailbox)
    except (OSError, imaplib.IMAP4.error) as exc:
        raise EmailClientError(f"Echec de connexion IMAP: {exc}") from exc
    return connection


def fetch_unread(mailbox: str = DEFAULT_MAILBOX, max_messages: int = 10) -> list[dict]:
    connection = _connect_imap(mailbox)
    messages = []
    failures = []
    try:
        status, data = connection.search(None, "UNSEEN")
        if status != "OK":
            raise EmailClientError("Echec de la recherche IMAP des messages non lus")

        uids = data[0].split()[:max_messages]
        for uid in uids:
            try:
                status, msg_data = connection.fetch(uid, "(RFC822)")
                if status != "OK" or not msg_data or msg_data[0] is None:
                    continue
                raw = msg_data[0][1]
                parsed = email_lib.message_from_bytes(raw)
                messages.append(
                    {
                        "uid": uid.decode(),
                        "de": _decode_header_value(parsed.get("From", "")),
                        "objet": _decode_header_value(parsed.get("Subject", "")),
                        "corps": _extract_body(parsed),
                    }
                )
            except (imaplib.IMAP4.error, LookupError, ValueError, TypeError) as exc:
                failures.append(f"{uid.decode(errors='replace')}: {exc}")
    except imaplib.IMAP4.error as exc:
        raise EmailClientError(f"Echec de la lecture des messages: {exc}") from exc
    finally:
        connection.logout()

    for failure in failures:
        print(f"[email-check] avertissement, message ignore: {failure}", file=sys.stderr)

    return messages


def mark_as_read(uids: list[str], mailbox: str = DEFAULT_MAILBOX) -> None:
    if not uids:
        return

    connection = _connect_imap(mailbox)
    try:
        for uid in uids:
            connection.store(uid, "+FLAGS", "\\Seen")
    except imaplib.IMAP4.error as exc:
        raise EmailClientError(f"Echec du marquage comme lu: {exc}") from exc
    finally:
        connection.logout()


def send_email(to: str, subject: str, body: str) -> None:
    values = _get_env(REQUIRED_SMTP_VARS)
    host = values["EMAIL_SMTP_HOST"]
    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))

    message = EmailMessage()
    message["From"] = values["EMAIL_ADDRESS"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as connection:
            connection.starttls()
            connection.login(values["EMAIL_ADDRESS"], values["EMAIL_PASSWORD"])
            connection.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailClientError(f"Echec de l'envoi de l'email: {exc}") from exc
