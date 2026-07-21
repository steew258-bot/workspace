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
