import json
from unittest.mock import MagicMock, patch

import pytest

from src.modules.whatsapp import (
    REQUIRED_ENV_VARS,
    WhatsAppError,
    send_whatsapp_message,
    send_whatsapp_template,
)


def test_missing_env_vars_raise_error(monkeypatch):
    for var in REQUIRED_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(WhatsAppError):
        send_whatsapp_message("+33600000000", "Bonjour")


def test_send_whatsapp_message_success(monkeypatch):
    monkeypatch.setenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")

    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({"messages": [{"id": "wamid.abc"}]}).encode()
    fake_response.__enter__.return_value = fake_response

    with patch("src.modules.whatsapp.urllib.request.urlopen", return_value=fake_response) as mocked:
        result = send_whatsapp_message("+33600000000", "Bonjour")

    assert result == {"messages": [{"id": "wamid.abc"}]}
    mocked.assert_called_once()


def test_send_whatsapp_message_api_error(monkeypatch):
    import urllib.error

    monkeypatch.setenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")

    http_error = urllib.error.HTTPError(
        url="https://graph.facebook.com/v20.0/123456/messages",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error": "invalid token"}'),
    )

    with (
        patch("src.modules.whatsapp.urllib.request.urlopen", side_effect=http_error),
        pytest.raises(WhatsAppError),
    ):
        send_whatsapp_message("+33600000000", "Bonjour")


def test_send_whatsapp_message_retries_transient_connection_error_then_succeeds(monkeypatch):
    import urllib.error

    monkeypatch.setenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setattr("src.retry.time.sleep", lambda seconds: None)

    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({"messages": [{"id": "wamid.abc"}]}).encode()
    fake_response.__enter__.return_value = fake_response

    with patch(
        "src.modules.whatsapp.urllib.request.urlopen",
        side_effect=[urllib.error.URLError("connection refused"), fake_response],
    ) as mocked:
        result = send_whatsapp_message("+33600000000", "Bonjour")

    assert result == {"messages": [{"id": "wamid.abc"}]}
    assert mocked.call_count == 2


def test_send_whatsapp_message_non_json_response(monkeypatch):
    monkeypatch.setenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")

    fake_response = MagicMock()
    fake_response.read.return_value = b"<html>not json</html>"
    fake_response.__enter__.return_value = fake_response

    with (
        patch("src.modules.whatsapp.urllib.request.urlopen", return_value=fake_response),
        pytest.raises(WhatsAppError),
    ):
        send_whatsapp_message("+33600000000", "Bonjour")


def test_send_whatsapp_template_success(monkeypatch):
    monkeypatch.setenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")

    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({"messages": [{"id": "wamid.tpl"}]}).encode()
    fake_response.__enter__.return_value = fake_response

    with patch(
        "src.modules.whatsapp.urllib.request.urlopen", return_value=fake_response
    ) as mocked:
        result = send_whatsapp_template(
            "+33600000000", "notification_urgente", "fr", body_params=["Client furieux"]
        )

    assert result == {"messages": [{"id": "wamid.tpl"}]}
    sent_payload = json.loads(mocked.call_args[0][0].data)
    assert sent_payload["type"] == "template"
    assert sent_payload["template"]["name"] == "notification_urgente"
    assert sent_payload["template"]["components"][0]["parameters"][0]["text"] == "Client furieux"


def test_send_whatsapp_template_without_params(monkeypatch):
    monkeypatch.setenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")

    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({"messages": [{"id": "wamid.tpl2"}]}).encode()
    fake_response.__enter__.return_value = fake_response

    with patch("src.modules.whatsapp.urllib.request.urlopen", return_value=fake_response) as mocked:
        send_whatsapp_template("+33600000000", "hello_world", "en_US")

    sent_payload = json.loads(mocked.call_args[0][0].data)
    assert "components" not in sent_payload["template"]
