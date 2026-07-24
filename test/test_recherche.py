import json
from unittest.mock import MagicMock, patch

import pytest

from src.modules.recherche import RechercheError, _parse_response, recherche


def test_missing_api_key_raises_error(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

    with pytest.raises(RechercheError):
        recherche("Quelles sont les dernieres nouvelles sur X ?")


def test_recherche_success(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    fake_body = {
        "choices": [{"message": {"content": "Voici la reponse."}}],
        "citations": ["https://exemple.com/a", "https://exemple.com/b"],
    }
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps(fake_body).encode()
    fake_response.__enter__.return_value = fake_response

    with patch(
        "src.modules.recherche.urllib.request.urlopen", return_value=fake_response
    ) as mocked:
        result = recherche("Une question")

    assert result == {
        "reponse": "Voici la reponse.",
        "sources": ["https://exemple.com/a", "https://exemple.com/b"],
    }
    sent_payload = json.loads(mocked.call_args[0][0].data)
    assert sent_payload["model"] == "sonar"
    assert sent_payload["messages"] == [{"role": "user", "content": "Une question"}]


def test_recherche_without_citations(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    fake_body = {"choices": [{"message": {"content": "Reponse sans sources."}}]}
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps(fake_body).encode()
    fake_response.__enter__.return_value = fake_response

    with patch("src.modules.recherche.urllib.request.urlopen", return_value=fake_response):
        result = recherche("Une question")

    assert result["sources"] == []


def test_recherche_api_error(monkeypatch):
    import urllib.error

    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    http_error = urllib.error.HTTPError(
        url="https://api.perplexity.ai/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error": "invalid api key"}'),
    )

    with (
        patch("src.modules.recherche.urllib.request.urlopen", side_effect=http_error),
        pytest.raises(RechercheError),
    ):
        recherche("Une question")


def test_parse_response_top_level_not_a_dict():
    for bad_data in ([], None, "juste une chaine", 42):
        with pytest.raises(RechercheError):
            _parse_response(bad_data)


def test_parse_response_choice_item_not_a_dict():
    with pytest.raises(RechercheError):
        _parse_response({"choices": ["pas-un-dict"]})


def test_parse_response_message_not_a_dict():
    with pytest.raises(RechercheError):
        _parse_response({"choices": [{"message": "pas-un-dict"}]})


def test_parse_response_missing_choices():
    with pytest.raises(RechercheError):
        _parse_response({})


def test_parse_response_empty_choices():
    with pytest.raises(RechercheError):
        _parse_response({"choices": []})


def test_parse_response_missing_content():
    with pytest.raises(RechercheError):
        _parse_response({"choices": [{"message": {}}]})


def test_parse_response_non_list_citations_defaults_to_empty():
    result = _parse_response(
        {"choices": [{"message": {"content": "ok"}}], "citations": "not-a-list"}
    )
    assert result["sources"] == []


def test_missing_api_key_raises_error_en(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

    with pytest.raises(RechercheError):
        recherche("What's the latest news on X?", lang="en")


def test_recherche_success_en(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    fake_body = {
        "choices": [{"message": {"content": "Here's the answer."}}],
        "citations": ["https://example.com/a", "https://example.com/b"],
    }
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps(fake_body).encode()
    fake_response.__enter__.return_value = fake_response

    with patch(
        "src.modules.recherche.urllib.request.urlopen", return_value=fake_response
    ) as mocked:
        result = recherche("A question", lang="en")

    assert result == {
        "response": "Here's the answer.",
        "sources": ["https://example.com/a", "https://example.com/b"],
    }
    sent_payload = json.loads(mocked.call_args[0][0].data)
    assert sent_payload["model"] == "sonar"
    assert sent_payload["messages"] == [{"role": "user", "content": "A question"}]


def test_recherche_without_citations_en(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    fake_body = {"choices": [{"message": {"content": "Answer without sources."}}]}
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps(fake_body).encode()
    fake_response.__enter__.return_value = fake_response

    with patch("src.modules.recherche.urllib.request.urlopen", return_value=fake_response):
        result = recherche("A question", lang="en")

    assert result["sources"] == []


def test_recherche_api_error_en(monkeypatch):
    import urllib.error

    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    http_error = urllib.error.HTTPError(
        url="https://api.perplexity.ai/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"error": "invalid api key"}'),
    )

    with (
        patch("src.modules.recherche.urllib.request.urlopen", side_effect=http_error),
        pytest.raises(RechercheError),
    ):
        recherche("A question", lang="en")


def test_recherche_url_error_en(monkeypatch):
    import urllib.error

    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    url_error = urllib.error.URLError("connection refused")

    with (
        patch("src.modules.recherche.urllib.request.urlopen", side_effect=url_error),
        pytest.raises(RechercheError),
    ):
        recherche("A question", lang="en")


def test_recherche_non_json_response_en(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")

    fake_response = MagicMock()
    fake_response.read.return_value = b"not json"
    fake_response.__enter__.return_value = fake_response

    with (
        patch("src.modules.recherche.urllib.request.urlopen", return_value=fake_response),
        pytest.raises(RechercheError),
    ):
        recherche("A question", lang="en")


def test_parse_response_top_level_not_a_dict_en():
    for bad_data in ([], None, "just a string", 42):
        with pytest.raises(RechercheError):
            _parse_response(bad_data, lang="en")


def test_parse_response_choice_item_not_a_dict_en():
    with pytest.raises(RechercheError):
        _parse_response({"choices": ["not-a-dict"]}, lang="en")


def test_parse_response_message_not_a_dict_en():
    with pytest.raises(RechercheError):
        _parse_response({"choices": [{"message": "not-a-dict"}]}, lang="en")


def test_parse_response_missing_choices_en():
    with pytest.raises(RechercheError):
        _parse_response({}, lang="en")


def test_parse_response_empty_choices_en():
    with pytest.raises(RechercheError):
        _parse_response({"choices": []}, lang="en")


def test_parse_response_missing_content_en():
    with pytest.raises(RechercheError):
        _parse_response({"choices": [{"message": {}}]}, lang="en")


def test_parse_response_non_list_citations_defaults_to_empty_en():
    result = _parse_response(
        {"choices": [{"message": {"content": "ok"}}], "citations": "not-a-list"},
        lang="en",
    )
    assert result["sources"] == []


def test_recherche_lang_from_env_var(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-token")
    monkeypatch.setenv("OPS_AGENT_LANG", "en")

    fake_body = {"choices": [{"message": {"content": "Here's the answer."}}]}
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps(fake_body).encode()
    fake_response.__enter__.return_value = fake_response

    with patch("src.modules.recherche.urllib.request.urlopen", return_value=fake_response):
        result = recherche("A question")

    assert "response" in result
