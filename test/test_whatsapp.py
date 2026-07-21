import json
from unittest.mock import MagicMock, patch

import pytest

from src.modules.whatsapp import REQUIRED_ENV_VARS, WhatsAppError, send_whatsapp_message


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

    with patch("src.modules.whatsapp.urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(WhatsAppError):
            send_whatsapp_message("+33600000000", "Bonjour")
