import os
import sys

from src.modules._client import get_lang
from src.modules.agenda import FIELDS as AGENDA_FIELDS
from src.modules.crm import FIELDS as CRM_FIELDS
from src.modules.email import FIELDS as EMAIL_FIELDS
from src.modules.email_client import FIELDS as EMAIL_CLIENT_FIELDS
from src.modules.triage import FIELDS as TRIAGE_FIELDS
from src.modules.veille import FIELDS as VEILLE_FIELDS
from src.modules.whatsapp import WhatsAppError, send_whatsapp_message, send_whatsapp_template

# Nom logique canonique -> nom de champ localise, pour l'enveloppe de resultat
# construite par app.py pour la commande email-check (pas issue d'un module).
RESULT_FIELDS = {
    "processed": {"fr": "traites", "en": "processed"},
}

_URGENCY_HIGH_VALUES = {"fr": "haute", "en": "high"}
_CHURN_HIGH_VALUES = {"fr": "eleve", "en": "high"}

_TRIAGE_LABELS = {"fr": "Triage", "en": "Triage"}
_EMAIL_LABELS = {"fr": "Email", "en": "Email"}

_SEND_FAILURE_MESSAGES = {
    "fr": "[notify] echec de l'envoi de la notification WhatsApp: {exc}",
    "en": "[notify] failed to send WhatsApp notification: {exc}",
}
_URGENT_MESSAGES = {
    "fr": "{label} urgent\nAction : {action}\nSuggestion : {reply_draft}",
    "en": "{label} urgent\nAction: {action}\nSuggestion: {reply_draft}",
}
_VEILLE_MESSAGES = {
    "fr": "Veille : {count} element(s) prioritaire(s)\n{lines}",
    "en": "Monitoring: {count} priority item(s)\n{lines}",
}
_VEILLE_ITEM_LINE = {"fr": "- {title} ({reason})", "en": "- {title} ({reason})"}
_CHURN_MESSAGES = {
    "fr": "Risque de churn eleve\nStatut : {status}\nAction : {action}",
    "en": "High churn risk\nStatus: {status}\nAction: {action}",
}
_AGENDA_MESSAGES = {
    "fr": "Agenda : {count} conflit(s) detecte(s)\n{lines}",
    "en": "Calendar: {count} conflict(s) detected\n{lines}",
}
_AGENDA_ITEM_LINE = {"fr": "- {events} ({reason})", "en": "- {events} ({reason})"}
_EMAIL_CHECK_MESSAGES = {
    "fr": "Email : {count} message(s) urgent(s)\n{lines}",
    "en": "Email: {count} urgent message(s)\n{lines}",
}
_EMAIL_CHECK_ITEM_LINE = {"fr": "- {subject_} ({from_})", "en": "- {subject_} ({from_})"}


def _notify_target() -> str | None:
    return os.environ.get("WHATSAPP_NOTIFY_TO")


def _notify_template() -> tuple[str, str] | None:
    template_name = os.environ.get("WHATSAPP_NOTIFY_TEMPLATE")
    if not template_name:
        return None
    return template_name, os.environ.get("WHATSAPP_NOTIFY_TEMPLATE_LANG", "fr")


def _send(message: str, lang: str) -> None:
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
        print(_SEND_FAILURE_MESSAGES[lang].format(exc=exc), file=sys.stderr)


def notify_if_urgent(command: str, result: dict, lang: str | None = None) -> None:
    lang = get_lang(lang)

    if command in ("triage", "email"):
        fields = TRIAGE_FIELDS if command == "triage" else EMAIL_FIELDS
        label = _TRIAGE_LABELS[lang] if command == "triage" else _EMAIL_LABELS[lang]
        if result.get(fields["urgency"][lang]) == _URGENCY_HIGH_VALUES[lang]:
            _send(
                _URGENT_MESSAGES[lang].format(
                    label=label,
                    action=result.get(fields["action"][lang], ""),
                    reply_draft=result.get(fields["reply_draft"][lang], ""),
                ),
                lang,
            )
    elif command in ("veille", "veille-feeds"):
        items = result.get(VEILLE_FIELDS["to_review"][lang])
        if items:
            title_key = VEILLE_FIELDS["title"][lang]
            reason_key = VEILLE_FIELDS["reason"][lang]
            lignes = "\n".join(
                _VEILLE_ITEM_LINE[lang].format(
                    title=item.get(title_key, ""), reason=item.get(reason_key, "")
                )
                for item in items
            )
            _send(_VEILLE_MESSAGES[lang].format(count=len(items), lines=lignes), lang)
    elif (
        command == "crm" and result.get(CRM_FIELDS["churn_risk"][lang]) == _CHURN_HIGH_VALUES[lang]
    ):
        _send(
            _CHURN_MESSAGES[lang].format(
                status=result.get(CRM_FIELDS["status"][lang], ""),
                action=result.get(CRM_FIELDS["action"][lang], ""),
            ),
            lang,
        )
    elif command == "agenda" and result.get(AGENDA_FIELDS["conflicts"][lang]):
        conflits = result[AGENDA_FIELDS["conflicts"][lang]]
        events_key = AGENDA_FIELDS["events"][lang]
        reason_key = AGENDA_FIELDS["reason"][lang]
        lignes = "\n".join(
            _AGENDA_ITEM_LINE[lang].format(
                events=" / ".join(c.get(events_key, [])), reason=c.get(reason_key, "")
            )
            for c in conflits
        )
        _send(_AGENDA_MESSAGES[lang].format(count=len(conflits), lines=lignes), lang)
    elif command == "email-check":
        urgency_key = EMAIL_FIELDS["urgency"][lang]
        traites = result.get(RESULT_FIELDS["processed"][lang], [])
        urgents = [item for item in traites if item.get(urgency_key) == _URGENCY_HIGH_VALUES[lang]]
        if urgents:
            subject_key = EMAIL_CLIENT_FIELDS["subject"][lang]
            from_key = EMAIL_CLIENT_FIELDS["from"][lang]
            lignes = "\n".join(
                _EMAIL_CHECK_ITEM_LINE[lang].format(
                    subject_=item.get(subject_key, ""), from_=item.get(from_key, "")
                )
                for item in urgents
            )
            _send(_EMAIL_CHECK_MESSAGES[lang].format(count=len(urgents), lines=lignes), lang)
