import json
import urllib.error
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.modules.calendar_client import REQUIRED_ENV_VARS, CalendarClientError, fetch_events


def _set_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh-token")


def _fake_response(body: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(body).encode()
    response.__enter__.return_value = response
    return response


def test_fetch_events_missing_env_vars_raise_error(monkeypatch):
    for var in REQUIRED_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(CalendarClientError):
        fetch_events()


def test_fetch_events_success(monkeypatch):
    _set_env(monkeypatch)

    token_response = _fake_response({"access_token": "fresh-token"})
    events_response = _fake_response(
        {
            "items": [
                {
                    "summary": "RDV client",
                    "start": {"dateTime": "2026-08-06T14:00:00+04:00"},
                    "end": {"dateTime": "2026-08-06T15:00:00+04:00"},
                },
                {"summary": "", "start": {}, "end": {}},
            ]
        }
    )

    with patch(
        "src.modules.calendar_client.urllib.request.urlopen",
        side_effect=[token_response, events_response],
    ):
        events = fetch_events(day=date(2026, 8, 6))

    assert len(events) == 1
    assert events[0]["titre"] == "RDV client"
    assert events[0]["debut"] == "2026-08-06T14:00:00+04:00"


def test_fetch_events_retries_transient_connection_error_then_succeeds(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setattr("src.retry.time.sleep", lambda seconds: None)

    token_response = _fake_response({"access_token": "fresh-token"})
    events_response = _fake_response({"items": []})

    with patch(
        "src.modules.calendar_client.urllib.request.urlopen",
        side_effect=[urllib.error.URLError("connection refused"), token_response, events_response],
    ) as mocked:
        events = fetch_events(day=date(2026, 8, 6))

    assert events == []
    assert mocked.call_count == 3


def test_fetch_events_token_refresh_error(monkeypatch):
    _set_env(monkeypatch)

    http_error = urllib.error.HTTPError(
        url="https://oauth2.googleapis.com/token",
        code=400,
        msg="Bad Request",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error": "invalid_grant"}'),
    )

    with (
        patch("src.modules.calendar_client.urllib.request.urlopen", side_effect=http_error),
        pytest.raises(CalendarClientError),
    ):
        fetch_events()


def test_fetch_events_missing_items_raises_error(monkeypatch):
    _set_env(monkeypatch)

    token_response = _fake_response({"access_token": "fresh-token"})
    bad_events_response = _fake_response({"error": "boom"})

    with (
        patch(
            "src.modules.calendar_client.urllib.request.urlopen",
            side_effect=[token_response, bad_events_response],
        ),
        pytest.raises(CalendarClientError),
    ):
        fetch_events()


def test_fetch_events_no_access_token_raises_error(monkeypatch):
    _set_env(monkeypatch)

    token_response = _fake_response({"error": "invalid_grant"})

    with (
        patch("src.modules.calendar_client.urllib.request.urlopen", return_value=token_response),
        pytest.raises(CalendarClientError),
    ):
        fetch_events()
