import pytest

from src.modules.planification import PlanificationError, _parse_response


def test_parse_valid_response():
    raw = (
        '{"ordre": ["Repondre au client urgent", "Preparer le devis"], '
        '"tache_prioritaire": "Repondre au client urgent", '
        '"justification": "Impact direct sur une vente en cours"}'
    )
    result = _parse_response(raw)
    assert result["ordre"][0] == "Repondre au client urgent"
    assert result["tache_prioritaire"] == "Repondre au client urgent"


def test_parse_missing_field():
    raw = '{"ordre": ["A", "B"]}'
    with pytest.raises(PlanificationError):
        _parse_response(raw)


def test_parse_empty_ordre():
    raw = '{"ordre": [], "tache_prioritaire": "", "justification": ""}'
    with pytest.raises(PlanificationError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(PlanificationError):
        _parse_response("pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(PlanificationError):
        _parse_response(raw)
