import pytest

from src.modules.resume import ResumeError, _parse_response


def test_parse_valid_response():
    raw = (
        '{"resume": "Le projet avance bien, deux blocages restent a lever.", '
        '"points_cles": ["Budget valide", "Delai serre sur le lot 2"]}'
    )
    result = _parse_response(raw)
    assert result["resume"].startswith("Le projet avance bien")
    assert len(result["points_cles"]) == 2


def test_parse_missing_field():
    raw = '{"resume": "Un resume"}'
    with pytest.raises(ResumeError):
        _parse_response(raw)


def test_parse_empty_resume():
    raw = '{"resume": "  ", "points_cles": ["x"]}'
    with pytest.raises(ResumeError):
        _parse_response(raw)


def test_parse_empty_points_cles():
    raw = '{"resume": "Un resume", "points_cles": []}'
    with pytest.raises(ResumeError):
        _parse_response(raw)


def test_parse_wrong_type():
    raw = '{"resume": "Un resume", "points_cles": "pas une liste"}'
    with pytest.raises(ResumeError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(ResumeError):
        _parse_response("pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(ResumeError):
        _parse_response(raw)
