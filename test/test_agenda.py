import pytest

from src.modules.agenda import AgendaError, _parse_response


def test_parse_valid_response():
    raw = (
        '{"conflits": [{"evenements": ["RDV client 14h", "Appel fournisseur 14h"], '
        '"raison": "meme creneau"}], '
        '"creneaux_libres": ["9h-10h", "16h-17h"], '
        '"suggestions": ["Decaler l\'appel fournisseur a 15h"]}'
    )
    result = _parse_response(raw)
    assert len(result["conflits"]) == 1
    assert result["creneaux_libres"] == ["9h-10h", "16h-17h"]


def test_parse_no_conflicts():
    raw = '{"conflits": [], "creneaux_libres": ["9h-12h"], "suggestions": []}'
    result = _parse_response(raw)
    assert result["conflits"] == []


def test_parse_missing_field():
    raw = '{"conflits": [], "creneaux_libres": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw)


def test_parse_wrong_type_conflits():
    raw = '{"conflits": "pas une liste", "creneaux_libres": [], "suggestions": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw)


def test_parse_invalid_conflit_shape():
    raw = '{"conflits": [{"evenements": ["A"]}], "creneaux_libres": [], "suggestions": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw)


def test_parse_wrong_type_creneaux_libres():
    raw = '{"conflits": [], "creneaux_libres": "pas une liste", "suggestions": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw)


def test_parse_wrong_type_suggestions():
    raw = '{"conflits": [], "creneaux_libres": [], "suggestions": "pas une liste"}'
    with pytest.raises(AgendaError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(AgendaError):
        _parse_response("pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(AgendaError):
        _parse_response(raw)
