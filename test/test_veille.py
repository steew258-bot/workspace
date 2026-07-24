import pytest

from src.modules.veille import VeilleError, _parse_response


def test_parse_valid_response():
    raw = (
        '{"a_traiter": [{"titre": "Appel d\'offres X", "raison": "deadline proche"}], '
        '"archive": ["Article generique", "Annonce non pertinente"]}'
    )
    result = _parse_response(raw)
    assert len(result["a_traiter"]) == 1
    assert result["a_traiter"][0]["titre"] == "Appel d'offres X"
    assert "archive" in result


def test_parse_missing_field():
    raw = '{"a_traiter": []}'
    with pytest.raises(VeilleError):
        _parse_response(raw)


def test_parse_wrong_type():
    raw = '{"a_traiter": "pas une liste", "archive": []}'
    with pytest.raises(VeilleError):
        _parse_response(raw)


def test_parse_invalid_item_shape():
    raw = '{"a_traiter": [{"titre": "X"}], "archive": []}'
    with pytest.raises(VeilleError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(VeilleError):
        _parse_response("pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(VeilleError):
        _parse_response(raw)


def test_parse_valid_response_en():
    raw = (
        '{"to_review": [{"title": "RFP X", "reason": "deadline approaching"}], '
        '"archived": ["Generic article", "Irrelevant announcement"]}'
    )
    result = _parse_response(raw, lang="en")
    assert len(result["to_review"]) == 1
    assert result["to_review"][0]["title"] == "RFP X"
    assert "archived" in result


def test_parse_missing_field_en():
    raw = '{"to_review": []}'
    with pytest.raises(VeilleError):
        _parse_response(raw, lang="en")


def test_parse_wrong_type_en():
    raw = '{"to_review": "not a list", "archived": []}'
    with pytest.raises(VeilleError):
        _parse_response(raw, lang="en")


def test_parse_invalid_item_shape_en():
    raw = '{"to_review": [{"title": "X"}], "archived": []}'
    with pytest.raises(VeilleError):
        _parse_response(raw, lang="en")


def test_parse_non_json_en():
    with pytest.raises(VeilleError):
        _parse_response("not json", lang="en")


@pytest.mark.parametrize("raw", ["[]", "null", '"just a string"', "42"])
def test_parse_valid_json_but_not_an_object_en(raw):
    with pytest.raises(VeilleError):
        _parse_response(raw, lang="en")
