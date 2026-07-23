from unittest.mock import MagicMock, patch

import pytest

from src.modules.crm import CrmError, _parse_response, crm_export_xlsx


def test_parse_valid_response():
    raw = (
        '{"statut": "a relancer", "relance_a_faire": true, '
        '"action": "Rappeler avant vendredi", "risque_churn": "eleve"}'
    )
    result = _parse_response(raw)
    assert result["statut"] == "a relancer"
    assert result["relance_a_faire"] is True
    assert result["risque_churn"] == "eleve"


def test_parse_missing_field():
    raw = '{"statut": "actif", "relance_a_faire": false, "action": "Rien a faire"}'
    with pytest.raises(CrmError):
        _parse_response(raw)


def test_parse_invalid_risque_churn():
    raw = (
        '{"statut": "actif", "relance_a_faire": false, "action": "Rien a faire", '
        '"risque_churn": "critique"}'
    )
    with pytest.raises(CrmError):
        _parse_response(raw)


def test_parse_invalid_relance_a_faire_type():
    raw = (
        '{"statut": "actif", "relance_a_faire": "oui", "action": "Rien a faire", '
        '"risque_churn": "faible"}'
    )
    with pytest.raises(CrmError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(CrmError):
        _parse_response("pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(CrmError):
        _parse_response(raw)


def test_crm_export_xlsx_builds_prompt_and_delegates_to_skill():
    fiche = {
        "statut": "a relancer",
        "relance_a_faire": True,
        "action": "Rappeler avant vendredi",
        "risque_churn": "eleve",
    }
    client = MagicMock()

    with patch("src.modules.crm.generate_file_with_skill", return_value="fiche.xlsx") as mocked:
        result = crm_export_xlsx(fiche, "fiche.xlsx", client=client)

    assert result == "fiche.xlsx"
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    prompt = args[0]
    assert "a relancer" in prompt
    assert "oui" in prompt
    assert "Rappeler avant vendredi" in prompt
    assert "eleve" in prompt
    assert args[1] == "xlsx"
    assert args[2] == "fiche.xlsx"
    assert kwargs["client"] is client
