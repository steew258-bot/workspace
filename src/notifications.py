import os
import sys

from src.modules.whatsapp import WhatsAppError, send_whatsapp_message, send_whatsapp_template


def _notify_target() -> str | None:
    return os.environ.get("WHATSAPP_NOTIFY_TO")


def _notify_template() -> tuple[str, str] | None:
    template_name = os.environ.get("WHATSAPP_NOTIFY_TEMPLATE")
    if not template_name:
        return None
    return template_name, os.environ.get("WHATSAPP_NOTIFY_TEMPLATE_LANG", "fr")


def _send(message: str) -> None:
    to = _notify_target()
    if not to:
        return

    template = _notify_template()
    try:
        if template:
            template_name, language_code = template
            send_whatsapp_template(to, template_name, language_code, body_params=[message])
        else:
            send_whatsapp_message(to, message)
    except WhatsAppError as exc:
        print(f"[notify] echec de l'envoi de la notification WhatsApp: {exc}", file=sys.stderr)


def notify_if_urgent(command: str, result: dict) -> None:
    if command in ("triage", "email") and result.get("urgence") == "haute":
        label = "Triage" if command == "triage" else "Email"
        _send(
            f"{label} urgent\n"
            f"Action : {result.get('action', '')}\n"
            f"Suggestion : {result.get('brouillon_reponse', '')}"
        )
    elif command in ("veille", "veille-feeds") and result.get("a_traiter"):
        items = result["a_traiter"]
        lignes = "\n".join(
            f"- {item.get('titre', '')} ({item.get('raison', '')})" for item in items
        )
        _send(f"Veille : {len(items)} element(s) prioritaire(s)\n{lignes}")
    elif command == "email-check":
        urgents = [item for item in result.get("traites", []) if item.get("urgence") == "haute"]
        if urgents:
            lignes = "\n".join(
                f"- {item.get('objet', '')} ({item.get('de', '')})" for item in urgents
            )
            _send(f"Email : {len(urgents)} message(s) urgent(s)\n{lignes}")
