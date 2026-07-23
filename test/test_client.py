import pytest

from src.modules._client import MissingApiKeyError, get_client, parse_json_object


class _FakeError(ValueError):
    pass


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        get_client()


def test_parse_json_object_valid():
    result = parse_json_object('{"a": 1, "b": 2}', {"a", "b"}, _FakeError)
    assert result == {"a": 1, "b": 2}


def test_parse_json_object_non_json_raises():
    with pytest.raises(_FakeError):
        parse_json_object("pas du json", {"a"}, _FakeError)


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_json_object_not_an_object_raises(raw):
    with pytest.raises(_FakeError):
        parse_json_object(raw, {"a"}, _FakeError)


def test_parse_json_object_missing_key_raises():
    with pytest.raises(_FakeError):
        parse_json_object('{"a": 1}', {"a", "b"}, _FakeError)


def test_parse_json_object_ignores_extra_keys():
    result = parse_json_object('{"a": 1, "extra": true}', {"a"}, _FakeError)
    assert result == {"a": 1, "extra": True}
