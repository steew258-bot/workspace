from unittest.mock import patch

from src.diagnostics import MODULE_REQUIREMENTS, _check_var, check

ALL_TRACKED_VARS = sorted({var for vars_ in MODULE_REQUIREMENTS.values() for var in vars_})


def test_check_var_missing():
    assert _check_var("FOO_VAR", {}) == "manquante"


def test_check_var_detects_placeholder(monkeypatch):
    monkeypatch.setenv("FOO_VAR", "exemple")
    assert _check_var("FOO_VAR", {"FOO_VAR": "exemple"}) == "valeur d'exemple non remplacee"


def test_check_var_configured(monkeypatch):
    monkeypatch.setenv("FOO_VAR", "vraie-valeur")
    assert _check_var("FOO_VAR", {"FOO_VAR": "exemple"}) is None


def test_check_var_usable_default_not_flagged_even_if_unchanged(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.gmail.com")
    result = _check_var("EMAIL_IMAP_HOST", {"EMAIL_IMAP_HOST": "imap.gmail.com"})
    assert result is None


def test_check_reports_all_modules_incomplete_when_nothing_configured(monkeypatch):
    for var in [*ALL_TRACKED_VARS, "WHATSAPP_APP_SECRET", "WHATSAPP_NOTIFY_TO"]:
        monkeypatch.delenv(var, raising=False)

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    assert set(result["modules"].keys()) == set(MODULE_REQUIREMENTS.keys())
    for module in result["modules"].values():
        assert module["statut"] == "incomplet"
    assert len(result["avertissements"]) == 2


def test_check_module_ok_when_all_vars_configured(monkeypatch):
    for var in ALL_TRACKED_VARS:
        monkeypatch.setenv(var, f"vraie-valeur-{var}")

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    for name, module in result["modules"].items():
        assert module["statut"] == "ok", f"{name}: {module['problemes']}"


def test_check_detects_unreplaced_placeholder(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-...")

    with patch(
        "src.diagnostics._load_example_values", return_value={"ANTHROPIC_API_KEY": "sk-ant-..."}
    ):
        result = check()

    assert result["modules"]["triage"]["statut"] == "incomplet"
    assert result["modules"]["triage"]["problemes"]["ANTHROPIC_API_KEY"] == (
        "valeur d'exemple non remplacee"
    )


def test_warnings_absent_when_whatsapp_extras_configured(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "un-secret")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    assert result["avertissements"] == []


def test_warning_present_when_app_secret_still_placeholder(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "your-meta-app-secret")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    with patch(
        "src.diagnostics._load_example_values",
        return_value={"WHATSAPP_APP_SECRET": "your-meta-app-secret"},
    ):
        result = check()

    assert any("WHATSAPP_APP_SECRET" in w for w in result["avertissements"])


def test_warnings_present_when_whatsapp_extras_missing(monkeypatch):
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    monkeypatch.delenv("WHATSAPP_NOTIFY_TO", raising=False)

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    assert any("WHATSAPP_APP_SECRET" in w for w in result["avertissements"])
    assert any("WHATSAPP_NOTIFY_TO" in w for w in result["avertissements"])
