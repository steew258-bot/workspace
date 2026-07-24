import pytest

from src.modules.triage import TriageError, _parse_response


def test_parse_valid_response():
    raw = (
        '{"action": "Repondre au client", "urgence": "haute", '
        '"brouillon_reponse": "Bonjour, je reviens vers vous rapidement."}'
    )
    result = _parse_response(raw)
    assert result["action"] == "Repondre au client"
    assert result["urgence"] == "haute"
    assert "brouillon_reponse" in result


def test_parse_missing_field():
    raw = '{"action": "Repondre", "urgence": "haute"}'
    with pytest.raises(TriageError):
        _parse_response(raw)


def test_parse_invalid_urgence():
    raw = '{"action": "Repondre", "urgence": "critique", "brouillon_reponse": "..."}'
    with pytest.raises(TriageError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(TriageError):
        _parse_response("ceci n'est pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(TriageError):
        _parse_response(raw)


def test_parse_valid_response_en():
    raw = (
        '{"action": "Reply to the client", "urgency": "high", '
        '"reply_draft": "Hello, I will get back to you shortly."}'
    )
    result = _parse_response(raw, lang="en")
    assert result["action"] == "Reply to the client"
    assert result["urgency"] == "high"
    assert "reply_draft" in result


def test_parse_missing_field_en():
    raw = '{"action": "Reply", "urgency": "high"}'
    with pytest.raises(TriageError):
        _parse_response(raw, lang="en")


def test_parse_invalid_urgency_en():
    raw = '{"action": "Reply", "urgency": "critical", "reply_draft": "..."}'
    with pytest.raises(TriageError):
        _parse_response(raw, lang="en")


def test_parse_non_json_en():
    with pytest.raises(TriageError):
        _parse_response("this is not json", lang="en")


@pytest.mark.parametrize("raw", ["[]", "null", '"just a string"', "42"])
def test_parse_valid_json_but_not_an_object_en(raw):
    with pytest.raises(TriageError):
        _parse_response(raw, lang="en")


def test_parse_response_reads_ops_agent_lang_env_var(monkeypatch):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")
    raw = '{"action": "Reply", "urgency": "high", "reply_draft": "..."}'
    result = _parse_response(raw)
    assert result["urgency"] == "high"
