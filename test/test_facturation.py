from unittest.mock import MagicMock, patch

import pytest

from src.modules.facturation import FacturationError, _parse_response, facturation_export_xlsx


def test_parse_valid_response_with_prices():
    raw = (
        '{"client": "Societe X", '
        '"lignes": [{"designation": "Developpement site vitrine", "quantite": 1, '
        '"prix_unitaire": 1500}], '
        '"total_estime": 1500, "notes": ""}'
    )
    result = _parse_response(raw)
    assert result["client"] == "Societe X"
    assert result["total_estime"] == 1500


def test_parse_valid_response_without_prices():
    raw = (
        '{"client": "", "lignes": [{"designation": "Consulting", "quantite": 2, '
        '"prix_unitaire": null}], "total_estime": null, '
        '"notes": "Prix non precise, a completer"}'
    )
    result = _parse_response(raw)
    assert result["lignes"][0]["prix_unitaire"] is None
    assert result["total_estime"] is None


def test_parse_missing_field():
    raw = '{"client": "X", "lignes": [{"designation": "A", "quantite": 1, "prix_unitaire": 1}]}'
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_empty_lignes():
    raw = '{"client": "X", "lignes": [], "total_estime": null, "notes": ""}'
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_invalid_ligne_shape():
    raw = '{"client": "X", "lignes": [{"designation": "A"}], "total_estime": null, "notes": ""}'
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_invalid_quantite_type():
    raw = (
        '{"client": "X", "lignes": [{"designation": "A", "quantite": "deux", '
        '"prix_unitaire": null}], "total_estime": null, "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_invalid_prix_unitaire_type():
    raw = (
        '{"client": "X", "lignes": [{"designation": "A", "quantite": 1, '
        '"prix_unitaire": "cent euros"}], "total_estime": null, "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_invalid_total_estime_type():
    raw = (
        '{"client": "X", "lignes": [{"designation": "A", "quantite": 1, "prix_unitaire": 10}], '
        '"total_estime": "dix euros", "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_non_json():
    with pytest.raises(FacturationError):
        _parse_response("pas du json")


@pytest.mark.parametrize("raw", ["[]", "null", '"juste une chaine"', "42"])
def test_parse_valid_json_but_not_an_object(raw):
    with pytest.raises(FacturationError):
        _parse_response(raw)


def test_parse_valid_response_with_prices_en():
    raw = (
        '{"client": "Acme Corp", '
        '"line_items": [{"description": "Landing page development", "quantity": 1, '
        '"unit_price": 1500}], '
        '"estimated_total": 1500, "notes": ""}'
    )
    result = _parse_response(raw, lang="en")
    assert result["client"] == "Acme Corp"
    assert result["estimated_total"] == 1500


def test_parse_valid_response_without_prices_en():
    raw = (
        '{"client": "", "line_items": [{"description": "Consulting", "quantity": 2, '
        '"unit_price": null}], "estimated_total": null, '
        '"notes": "Price not specified, to be completed"}'
    )
    result = _parse_response(raw, lang="en")
    assert result["line_items"][0]["unit_price"] is None
    assert result["estimated_total"] is None


def test_parse_missing_field_en():
    raw = '{"client": "X", "line_items": [{"description": "A", "quantity": 1, "unit_price": 1}]}'
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_parse_empty_line_items_en():
    raw = '{"client": "X", "line_items": [], "estimated_total": null, "notes": ""}'
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_parse_invalid_line_item_shape_en():
    raw = (
        '{"client": "X", "line_items": [{"description": "A"}], '
        '"estimated_total": null, "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_parse_invalid_quantity_type_en():
    raw = (
        '{"client": "X", "line_items": [{"description": "A", "quantity": "two", '
        '"unit_price": null}], "estimated_total": null, "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_parse_invalid_unit_price_type_en():
    raw = (
        '{"client": "X", "line_items": [{"description": "A", "quantity": 1, '
        '"unit_price": "a hundred bucks"}], "estimated_total": null, "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_parse_invalid_estimated_total_type_en():
    raw = (
        '{"client": "X", "line_items": [{"description": "A", "quantity": 1, "unit_price": 10}], '
        '"estimated_total": "ten bucks", "notes": ""}'
    )
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_parse_non_json_en():
    with pytest.raises(FacturationError):
        _parse_response("not json", lang="en")


@pytest.mark.parametrize("raw", ["[]", "null", '"just a string"', "42"])
def test_parse_valid_json_but_not_an_object_en(raw):
    with pytest.raises(FacturationError):
        _parse_response(raw, lang="en")


def test_facturation_export_xlsx_en_builds_prompt_and_delegates_to_skill():
    quote = {
        "client": "Acme Corp",
        "line_items": [
            {"description": "Landing page development", "quantity": 1, "unit_price": 1500},
            {"description": "Maintenance", "quantity": 2, "unit_price": None},
        ],
        "estimated_total": None,
        "notes": "Maintenance price to confirm",
    }
    client = MagicMock()

    with patch(
        "src.modules.facturation.generate_file_with_skill", return_value="quote.xlsx"
    ) as mocked:
        result = facturation_export_xlsx(quote, "quote.xlsx", client=client, lang="en")

    assert result == "quote.xlsx"
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    prompt = args[0]
    assert "Acme Corp" in prompt
    assert "Landing page development" in prompt
    assert "1500 EUR" in prompt
    assert "price to be defined" in prompt
    assert args[1] == "xlsx"
    assert args[2] == "quote.xlsx"
    assert kwargs["client"] is client


def test_facturation_export_xlsx_builds_prompt_and_delegates_to_skill():
    devis = {
        "client": "Societe X",
        "lignes": [
            {"designation": "Developpement site vitrine", "quantite": 1, "prix_unitaire": 1500},
            {"designation": "Maintenance", "quantite": 2, "prix_unitaire": None},
        ],
        "total_estime": None,
        "notes": "Prix de maintenance a confirmer",
    }
    client = MagicMock()

    with patch(
        "src.modules.facturation.generate_file_with_skill", return_value="devis.xlsx"
    ) as mocked:
        result = facturation_export_xlsx(devis, "devis.xlsx", client=client)

    assert result == "devis.xlsx"
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    prompt = args[0]
    assert "Societe X" in prompt
    assert "Developpement site vitrine" in prompt
    assert "1500 EUR" in prompt
    assert "prix a definir" in prompt
    assert args[1] == "xlsx"
    assert args[2] == "devis.xlsx"
    assert kwargs["client"] is client
