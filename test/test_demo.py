import json

from scripts.demo import DEMOS, DEMOS_EN, run
from src.modules.agenda import _parse_response as agenda_parse
from src.modules.crm import _parse_response as crm_parse
from src.modules.email import _parse_response as email_parse
from src.modules.facturation import _parse_response as facturation_parse
from src.modules.planification import _parse_response as planification_parse
from src.modules.resume import _parse_response as resume_parse
from src.modules.triage import _parse_response as triage_parse
from src.modules.veille import _parse_response as veille_parse

# recherche n'a pas d'equivalent ici : son _parse_response prend la reponse brute de
# l'API Perplexity (choices/citations), pas notre propre format {reponse, sources}.
PARSERS = {
    "triage": triage_parse,
    "veille": veille_parse,
    "planification": planification_parse,
    "resume": resume_parse,
    "email": email_parse,
    "crm": crm_parse,
    "agenda": agenda_parse,
    "facturation": facturation_parse,
}

ALL_MODULES = {
    "triage",
    "veille",
    "planification",
    "resume",
    "email",
    "recherche",
    "crm",
    "agenda",
    "facturation",
}


def test_demo_covers_every_module():
    assert {d["module"] for d in DEMOS} == ALL_MODULES


def test_demo_outputs_match_real_module_contracts():
    for demo in DEMOS:
        parser = PARSERS.get(demo["module"])
        if parser is None:
            continue
        raw = json.dumps(demo["sortie"])
        parser(raw)  # ne doit lever aucune exception


def test_demo_recherche_output_has_expected_shape():
    demo = next(d for d in DEMOS if d["module"] == "recherche")
    assert set(demo["sortie"].keys()) == {"reponse", "sources"}
    assert isinstance(demo["sortie"]["sources"], list)


def test_demo_en_covers_every_module():
    assert {d["module"] for d in DEMOS_EN} == ALL_MODULES


def test_demo_en_outputs_match_real_module_contracts():
    for demo in DEMOS_EN:
        parser = PARSERS.get(demo["module"])
        if parser is None:
            continue
        raw = json.dumps(demo["sortie"])
        parser(raw, lang="en")  # ne doit lever aucune exception


def test_demo_en_recherche_output_has_expected_shape():
    demo = next(d for d in DEMOS_EN if d["module"] == "recherche")
    assert set(demo["sortie"].keys()) == {"response", "sources"}
    assert isinstance(demo["sortie"]["sources"], list)


def test_demo_en_content_is_actually_english():
    triage_demo = next(d for d in DEMOS_EN if d["module"] == "triage")
    assert "Client X" in triage_demo["commande"]
    assert "urgency" in triage_demo["sortie"]
    assert "urgence" not in triage_demo["sortie"]


def test_run_prints_french_banner_by_default(capsys):
    run()
    out = capsys.readouterr().out
    assert "DEMO OPS AGENT" in out
    assert "brouillon_reponse" in out


def test_run_prints_english_banner_when_lang_en(capsys):
    run(lang="en")
    out = capsys.readouterr().out
    assert "OPS AGENT DEMO" in out
    assert "reply_draft" in out


def test_run_lang_from_env_var(monkeypatch, capsys):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")
    run()
    out = capsys.readouterr().out
    assert "OPS AGENT DEMO" in out
