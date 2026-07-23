import urllib.error
from unittest.mock import MagicMock

import pytest

from src.retry import call_with_retry, is_transient_url_error


def test_call_with_retry_succeeds_first_try():
    func = MagicMock(return_value="ok")
    result = call_with_retry(func, is_retryable=lambda exc: True)
    assert result == "ok"
    func.assert_called_once()


def test_call_with_retry_succeeds_after_transient_failures(monkeypatch):
    monkeypatch.setattr("src.retry.time.sleep", lambda seconds: None)
    func = MagicMock(side_effect=[OSError("boom"), OSError("boom"), "ok"])

    result = call_with_retry(func, is_retryable=lambda exc: isinstance(exc, OSError))

    assert result == "ok"
    assert func.call_count == 3


def test_call_with_retry_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("src.retry.time.sleep", lambda seconds: None)
    func = MagicMock(side_effect=OSError("boom"))

    with pytest.raises(OSError):
        call_with_retry(func, is_retryable=lambda exc: isinstance(exc, OSError), attempts=3)

    assert func.call_count == 3


def test_call_with_retry_does_not_retry_non_retryable_error():
    func = MagicMock(side_effect=ValueError("pas transitoire"))

    with pytest.raises(ValueError):
        call_with_retry(func, is_retryable=lambda exc: isinstance(exc, OSError))

    func.assert_called_once()


def test_is_transient_url_error_true_for_connection_error():
    assert is_transient_url_error(urllib.error.URLError("connection refused")) is True


def test_is_transient_url_error_false_for_http_error():
    http_error = urllib.error.HTTPError(
        url="https://exemple.com", code=401, msg="Unauthorized", hdrs=None, fp=None
    )
    assert is_transient_url_error(http_error) is False


def test_is_transient_url_error_false_for_unrelated_exception():
    assert is_transient_url_error(ValueError("autre chose")) is False
