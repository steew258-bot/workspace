import imaplib
import smtplib
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from src.modules.email_client import (
    REQUIRED_IMAP_VARS,
    REQUIRED_SMTP_VARS,
    EmailClientError,
    fetch_unread,
    mark_as_read,
    send_email,
)


def _build_raw_email(subject="Bonjour", body="Contenu du message") -> bytes:
    msg = EmailMessage()
    msg["From"] = "client@exemple.com"
    msg["To"] = "moi@exemple.com"
    msg["Subject"] = subject
    msg.set_content(body)
    return msg.as_bytes()


def test_fetch_unread_missing_env_vars_raise_error(monkeypatch):
    for var in REQUIRED_IMAP_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(EmailClientError):
        fetch_unread()


def test_fetch_unread_parses_messages(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    raw = _build_raw_email(subject="Test urgent", body="Merci de rappeler.")
    fake_connection = MagicMock()
    fake_connection.search.return_value = ("OK", [b"1"])
    fake_connection.fetch.return_value = ("OK", [(b"1 (RFC822 {123}", raw)])

    with patch("src.modules.email_client.imaplib.IMAP4_SSL", return_value=fake_connection):
        messages = fetch_unread()

    assert len(messages) == 1
    assert messages[0]["uid"] == "1"
    assert messages[0]["de"] == "client@exemple.com"
    assert messages[0]["objet"] == "Test urgent"
    assert "rappeler" in messages[0]["corps"]
    fake_connection.login.assert_called_once_with("moi@exemple.com", "secret")
    fake_connection.logout.assert_called_once()


def test_fetch_unread_html_only_message_extracts_text(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    msg = EmailMessage()
    msg["From"] = "newsletter@exemple.com"
    msg["Subject"] = "Offre speciale"
    msg.set_content("<p>Profitez de <b>-20%</b> aujourd'hui.</p>", subtype="html")

    fake_connection = MagicMock()
    fake_connection.search.return_value = ("OK", [b"1"])
    fake_connection.fetch.return_value = ("OK", [(b"1 (RFC822 {123}", msg.as_bytes())])

    with patch("src.modules.email_client.imaplib.IMAP4_SSL", return_value=fake_connection):
        messages = fetch_unread()

    assert len(messages) == 1
    assert "-20%" in messages[0]["corps"]
    assert "<p>" not in messages[0]["corps"]
    assert "<b>" not in messages[0]["corps"]


def test_fetch_unread_skips_unparsable_message_and_continues(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    good_raw = _build_raw_email(subject="OK", body="Message correct")
    fake_connection = MagicMock()
    fake_connection.search.return_value = ("OK", [b"1 2"])

    def fake_fetch(uid, _spec):
        if uid == b"1":
            raise imaplib.IMAP4.error("boom")
        return ("OK", [(b"2 (RFC822 {123}", good_raw)])

    fake_connection.fetch.side_effect = fake_fetch

    with patch("src.modules.email_client.imaplib.IMAP4_SSL", return_value=fake_connection):
        messages = fetch_unread()

    assert len(messages) == 1
    assert messages[0]["uid"] == "2"


def test_fetch_unread_connection_error(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    with patch("src.modules.email_client.imaplib.IMAP4_SSL", side_effect=OSError("boom")):
        with pytest.raises(EmailClientError):
            fetch_unread()


def test_mark_as_read_stores_flags(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    fake_connection = MagicMock()

    with patch("src.modules.email_client.imaplib.IMAP4_SSL", return_value=fake_connection):
        mark_as_read(["1", "2"])

    assert fake_connection.store.call_count == 2
    fake_connection.store.assert_any_call("1", "+FLAGS", "\\Seen")
    fake_connection.store.assert_any_call("2", "+FLAGS", "\\Seen")


def test_mark_as_read_without_uids_does_nothing(monkeypatch):
    with patch("src.modules.email_client.imaplib.IMAP4_SSL") as mocked:
        mark_as_read([])

    mocked.assert_not_called()


def test_send_email_missing_env_vars_raise_error(monkeypatch):
    for var in REQUIRED_SMTP_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(EmailClientError):
        send_email("client@exemple.com", "Sujet", "Corps")


def test_send_email_success(monkeypatch):
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    fake_connection = MagicMock()
    fake_connection.__enter__.return_value = fake_connection

    with patch("src.modules.email_client.smtplib.SMTP", return_value=fake_connection):
        send_email("client@exemple.com", "Sujet", "Corps")

    fake_connection.starttls.assert_called_once()
    fake_connection.login.assert_called_once_with("moi@exemple.com", "secret")
    fake_connection.send_message.assert_called_once()


def test_send_email_smtp_error_raises_client_error(monkeypatch):
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.exemple.com")
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    with patch(
        "src.modules.email_client.smtplib.SMTP", side_effect=smtplib.SMTPException("boom")
    ):
        with pytest.raises(EmailClientError):
            send_email("client@exemple.com", "Sujet", "Corps")
