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
    assert len(result["avertissements"]) == 3


FORMAT_SENSITIVE_VALUES = {
    "EMAIL_ADDRESS": "moi@exemple.com",
    "WHATSAPP_API_URL": "https://graph.facebook.com/v20.0",
    "EMAIL_IMAP_PORT": "993",
    "EMAIL_SMTP_PORT": "587",
}


def test_check_module_ok_when_all_vars_configured(monkeypatch):
    for var in ALL_TRACKED_VARS:
        monkeypatch.setenv(var, FORMAT_SENSITIVE_VALUES.get(var, f"vraie-valeur-{var}"))

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


def test_whatsapp_warnings_absent_when_whatsapp_extras_configured(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "un-secret")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    assert not any("WHATSAPP" in w for w in result["avertissements"])


def test_skills_cost_warning_always_present(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "un-secret")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    assert any("export-xlsx" in w for w in result["avertissements"])


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


def test_check_var_email_format_valid(monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "moi@exemple.com")
    assert _check_var("EMAIL_ADDRESS", {}) is None


def test_check_var_email_format_invalid(monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "pas-un-email")
    result = _check_var("EMAIL_ADDRESS", {})
    assert result is not None
    assert "format invalide" in result


def test_check_var_url_format_invalid(monkeypatch):
    monkeypatch.setenv("WHATSAPP_API_URL", "graph.facebook.com/v20.0")
    result = _check_var("WHATSAPP_API_URL", {})
    assert result is not None
    assert "format invalide" in result


def test_check_var_port_format_invalid(monkeypatch):
    monkeypatch.setenv("EMAIL_IMAP_PORT", "pas-un-port")
    result = _check_var("EMAIL_IMAP_PORT", {})
    assert result is not None
    assert "format invalide" in result


def test_check_var_port_out_of_range_invalid(monkeypatch):
    monkeypatch.setenv("EMAIL_SMTP_PORT", "99999")
    result = _check_var("EMAIL_SMTP_PORT", {})
    assert result is not None
    assert "format invalide" in result


def test_whatsapp_notify_to_invalid_format_warns(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "un-secret")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "0600000000")  # sans indicatif +33

    with patch("src.diagnostics._load_example_values", return_value={}):
        result = check()

    assert any(
        "WHATSAPP_NOTIFY_TO" in w and "format invalide" in w for w in result["avertissements"]
    )
