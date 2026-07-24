import pytest

from src.modules._client import (
    DEFAULT_LANG,
    MissingApiKeyError,
    get_client,
    get_lang,
    parse_json_object,
)


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


def test_get_lang_defaults_to_fr(monkeypatch):
    monkeypatch.delenv("OPS_AGENT_LANG", raising=False)
    assert get_lang() == DEFAULT_LANG == "fr"


def test_get_lang_reads_env_var(monkeypatch):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")
    assert get_lang() == "en"


def test_get_lang_explicit_argument_wins_over_env(monkeypatch):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")
    assert get_lang("fr") == "fr"


def test_missing_api_key_raises_clear_error_en(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError, match="ANTHROPIC_API_KEY is missing"):
        get_client(lang="en")


def test_parse_json_object_non_json_raises_en():
    with pytest.raises(_FakeError, match="Response is not JSON"):
        parse_json_object("not json", {"a"}, _FakeError, lang="en")


@pytest.mark.parametrize("raw", ["[]", "null", '"just a string"', "42"])
def test_parse_json_object_not_an_object_raises_en(raw):
    with pytest.raises(_FakeError, match="Invalid JSON response"):
        parse_json_object(raw, {"a"}, _FakeError, lang="en")


def test_parse_json_object_missing_key_raises_en():
    with pytest.raises(_FakeError, match="Missing fields in response"):
        parse_json_object('{"a": 1}', {"a", "b"}, _FakeError, lang="en")


def test_parse_json_object_valid_en():
    result = parse_json_object('{"a": 1, "b": 2}', {"a", "b"}, _FakeError, lang="en")
    assert result == {"a": 1, "b": 2}


def test_parse_json_object_reads_ops_agent_lang_env_var(monkeypatch):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")
    with pytest.raises(_FakeError, match="Response is not JSON"):
        parse_json_object("not json", {"a"}, _FakeError)
