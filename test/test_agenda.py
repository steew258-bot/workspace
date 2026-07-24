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


def test_parse_valid_response_en():
    raw = (
        '{"conflicts": [{"events": ["Client meeting 2pm", "Supplier call 2pm"], '
        '"reason": "same time slot"}], '
        '"free_slots": ["9am-10am", "4pm-5pm"], '
        '"suggestions": ["Move the supplier call to 3pm"]}'
    )
    result = _parse_response(raw, lang="en")
    assert len(result["conflicts"]) == 1
    assert result["free_slots"] == ["9am-10am", "4pm-5pm"]


def test_parse_no_conflicts_en():
    raw = '{"conflicts": [], "free_slots": ["9am-12pm"], "suggestions": []}'
    result = _parse_response(raw, lang="en")
    assert result["conflicts"] == []


def test_parse_missing_field_en():
    raw = '{"conflicts": [], "free_slots": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw, lang="en")


def test_parse_wrong_type_conflicts_en():
    raw = '{"conflicts": "not a list", "free_slots": [], "suggestions": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw, lang="en")


def test_parse_invalid_conflict_shape_en():
    raw = '{"conflicts": [{"events": ["A"]}], "free_slots": [], "suggestions": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw, lang="en")


def test_parse_wrong_type_free_slots_en():
    raw = '{"conflicts": [], "free_slots": "not a list", "suggestions": []}'
    with pytest.raises(AgendaError):
        _parse_response(raw, lang="en")


def test_parse_wrong_type_suggestions_en():
    raw = '{"conflicts": [], "free_slots": [], "suggestions": "not a list"}'
    with pytest.raises(AgendaError):
        _parse_response(raw, lang="en")


def test_parse_non_json_en():
    with pytest.raises(AgendaError):
        _parse_response("not json", lang="en")


@pytest.mark.parametrize("raw", ["[]", "null", '"just a string"', "42"])
def test_parse_valid_json_but_not_an_object_en(raw):
    with pytest.raises(AgendaError):
        _parse_response(raw, lang="en")
