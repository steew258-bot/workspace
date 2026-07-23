import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.google_oauth_setup import _exchange_code_for_tokens, _get_client_credentials


def test_get_client_credentials_missing_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    with pytest.raises(SystemExit):
        _get_client_credentials()


def test_get_client_credentials_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")

    assert _get_client_credentials() == ("id", "secret")


def test_exchange_code_for_tokens_success():
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({"refresh_token": "abc"}).encode()
    fake_response.__enter__.return_value = fake_response

    with patch(
        "scripts.google_oauth_setup.urllib.request.urlopen", return_value=fake_response
    ) as mocked:
        tokens = _exchange_code_for_tokens("code123", "client-id", "client-secret")

    assert tokens == {"refresh_token": "abc"}
    mocked.assert_called_once()


def test_exchange_code_for_tokens_http_error():
    import urllib.error

    http_error = urllib.error.HTTPError(
        url="https://oauth2.googleapis.com/token",
        code=400,
        msg="Bad Request",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error": "invalid_grant"}'),
    )

    with (
        patch("scripts.google_oauth_setup.urllib.request.urlopen", side_effect=http_error),
        pytest.raises(SystemExit),
    ):
        _exchange_code_for_tokens("code123", "client-id", "client-secret")
