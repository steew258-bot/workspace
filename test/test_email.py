import pytest

from src.modules.email import EmailError, _parse_response


def test_parse_valid_response():
    raw = (
        '{"urgence": "haute", "necessite_reponse": true, "action": "Rappeler le client", '
        '"brouillon_reponse": "Bonjour, je vous rappelle rapidement."}'
    )
    result = _parse_response(raw)
    assert result["urgence"] == "haute"
    assert result["necessite_reponse"] is True
    assert result["action"] == "Rappeler le client"
    assert "brouillon_reponse" in result


def test_parse_missing_field():
    raw = '{"urgence": "haute", "necessite_reponse": true, "action": "Rappeler"}'
    with pytest.raises(EmailError):
        _parse_response(raw)


def test_parse_invalid_urgence():
    raw = (
        '{"urgence": "critique", "necessite_reponse": true, "action": "Rappeler", '
        '"brouillon_reponse": "..."}'
    )
    with pytest.raises(EmailError):
        _parse_response(raw)


def test_parse_invalid_necessite_reponse():
    raw = (
        '{"urgence": "basse", "necessite_reponse": "oui", "action": "Archiver", '
        '"brouillon_reponse": ""}'
    )
    with pytest.raises(EmailError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(EmailError):
        _parse_response("ceci n'est pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(EmailError):
        _parse_response(raw)
