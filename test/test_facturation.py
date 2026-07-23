import pytest

from src.modules.facturation import FacturationError, _parse_response


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
