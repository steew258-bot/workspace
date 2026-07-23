from unittest.mock import MagicMock, patch

import pytest

from src.modules.resume import ResumeError, _parse_response, resume_export_docx


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


def test_resume_export_docx_builds_prompt_and_delegates_to_skill():
    synthese = {
        "resume": "Le projet avance bien, deux blocages restent a lever.",
        "points_cles": ["Budget valide", "Delai serre sur le lot 2"],
    }
    client = MagicMock()

    with patch(
        "src.modules.resume.generate_file_with_skill", return_value="rapport.docx"
    ) as mocked:
        result = resume_export_docx(synthese, "rapport.docx", client=client)

    assert result == "rapport.docx"
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    prompt = args[0]
    assert "Le projet avance bien" in prompt
    assert "Budget valide" in prompt
    assert "Delai serre sur le lot 2" in prompt
    assert args[1] == "docx"
    assert args[2] == "rapport.docx"
    assert kwargs["client"] is client
