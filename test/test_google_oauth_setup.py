import json
from unittest.mock import MagicMock, patch

import pytest

import scripts.google_oauth_setup as oauth_setup
from scripts.google_oauth_setup import (
    _CallbackHandler,
    _exchange_code_for_tokens,
    _get_client_credentials,
    _wait_for_authorization_code,
)


@pytest.fixture(autouse=True)
def _reset_authorization_code():
    _CallbackHandler.authorization_code = None
    yield
    _CallbackHandler.authorization_code = None


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


def test_wait_for_authorization_code_returns_when_received():
    fake_server = MagicMock()

    def fake_handle_request():
        _CallbackHandler.authorization_code = "the-code"

    fake_server.handle_request.side_effect = fake_handle_request

    result = _wait_for_authorization_code(fake_server, timeout_seconds=60)

    assert result == "the-code"
    fake_server.handle_request.assert_called_once()


def test_wait_for_authorization_code_times_out(monkeypatch):
    fake_server = MagicMock()
    fake_server.handle_request.side_effect = lambda: None  # jamais de code recu

    times = iter([0, 100, 200])
    monkeypatch.setattr(oauth_setup.time, "monotonic", lambda: next(times))

    with pytest.raises(SystemExit, match="Aucune autorisation recue"):
        _wait_for_authorization_code(fake_server, timeout_seconds=50)
