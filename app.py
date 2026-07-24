import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import date

from src.diagnostics import FIELDS as DIAGNOSTICS_FIELDS
from src.diagnostics import check as check_environment
from src.modules._client import get_lang
from src.modules.agenda import FIELDS as AGENDA_FIELDS
from src.modules.agenda import agenda
from src.modules.calendar_client import fetch_events
from src.modules.crm import crm, crm_export_xlsx
from src.modules.email import email as email_triage
from src.modules.email_client import FIELDS as EMAIL_CLIENT_FIELDS
from src.modules.email_client import EmailClientError, fetch_unread, mark_as_read, send_email
from src.modules.facturation import facturation, facturation_export_xlsx
from src.modules.feeds import fetch_items_text
from src.modules.planification import planification
from src.modules.recherche import recherche
from src.modules.resume import resume, resume_export_docx
from src.modules.triage import triage
from src.modules.veille import veille
from src.modules.whatsapp import send_whatsapp_message
from src.notifications import RESULT_FIELDS, notify_if_urgent

__version__ = "1.0.0"

HELP = {
    "triage_cmd": {
        "fr": "Analyse un texte et propose une action",
        "en": "Analyzes a text and suggests an action",
    },
    "triage_text_arg": {
        "fr": "Texte a trier (email, tache, notification...)",
        "en": "Text to triage (email, task, notification...)",
    },
    "veille_cmd": {
        "fr": "Priorise une liste d'infos/alertes",
        "en": "Prioritizes a list of information/alerts",
    },
    "veille_text_arg": {
        "fr": "Liste brute d'infos/alertes (une par ligne)",
        "en": "Raw list of information/alerts (one per line)",
    },
    "veille_feeds_cmd": {
        "fr": "Recupere des flux RSS et priorise le resultat avec veille",
        "en": "Fetches RSS feeds and prioritizes the result with veille",
    },
    "veille_feeds_file_arg": {
        "fr": "Fichier avec une URL de flux RSS par ligne",
        "en": "File with one RSS feed URL per line",
    },
    "planification_cmd": {
        "fr": "Priorise les taches et contraintes du jour",
        "en": "Prioritizes today's tasks and constraints",
    },
    "planification_text_arg": {
        "fr": "Taches et contraintes du jour",
        "en": "Today's tasks and constraints",
    },
    "resume_cmd": {
        "fr": "Resume un texte long en points cles",
        "en": "Summarizes a long text into key points",
    },
    "resume_text_arg": {
        "fr": "Texte long a resumer (compte-rendu, doc, emails...)",
        "en": "Long text to summarize (report, doc, emails...)",
    },
    "resume_export_docx_arg": {
        "fr": "Chemin du fichier .docx a generer pour ce resume (beta, cf. doctor)",
        "en": "Path of the .docx file to generate for this summary (beta, see doctor)",
    },
    "facturation_cmd": {
        "fr": "Genere un brouillon de devis structure a partir d'une description",
        "en": "Generates a structured draft quote from a description",
    },
    "facturation_text_arg": {
        "fr": "Description de la prestation ou des produits",
        "en": "Description of the service or products",
    },
    "facturation_export_xlsx_arg": {
        "fr": "Chemin du fichier .xlsx a generer pour ce devis (beta, cf. doctor)",
        "en": "Path of the .xlsx file to generate for this quote (beta, see doctor)",
    },
    "agenda_cmd": {
        "fr": "Analyse evenements/contraintes du jour: conflits, creneaux, suggestions",
        "en": "Analyzes today's events/constraints: conflicts, free slots, suggestions",
    },
    "agenda_text_arg": {
        "fr": "Evenements et contraintes du jour",
        "en": "Today's events and constraints",
    },
    "agenda_check_cmd": {
        "fr": "Recupere les evenements du jour sur Google Calendar et detecte les conflits",
        "en": "Fetches today's events from Google Calendar and detects conflicts",
    },
    "agenda_check_date_arg": {
        "fr": "Date a verifier au format AAAA-MM-JJ (defaut: aujourd'hui)",
        "en": "Date to check in YYYY-MM-DD format (default: today)",
    },
    "crm_cmd": {
        "fr": "Analyse des notes d'echanges client et propose statut/action/risque",
        "en": "Analyzes customer exchange notes and suggests status/action/risk",
    },
    "crm_text_arg": {
        "fr": "Notes d'echanges avec le client ou prospect",
        "en": "Exchange notes with the client or prospect",
    },
    "crm_export_xlsx_arg": {
        "fr": "Chemin du fichier .xlsx a generer pour cette fiche client (beta, cf. doctor)",
        "en": "Path of the .xlsx file to generate for this customer sheet (beta, see doctor)",
    },
    "recherche_cmd": {
        "fr": "Recherche web en temps reel via Perplexity, avec sources",
        "en": "Real-time web search via Perplexity, with sources",
    },
    "recherche_text_arg": {
        "fr": "Question a rechercher sur le web",
        "en": "Question to search for on the web",
    },
    "email_cmd": {
        "fr": "Analyse un email brut (expediteur/objet/corps) et propose une action",
        "en": "Analyzes a raw email (sender/subject/body) and suggests an action",
    },
    "email_text_arg": {
        "fr": "Texte brut de l'email (expediteur, objet, corps)",
        "en": "Raw email text (sender, subject, body)",
    },
    "email_check_cmd": {
        "fr": "Recupere les emails non lus par IMAP et les triage automatiquement",
        "en": "Fetches unread emails via IMAP and triages them automatically",
    },
    "email_check_mailbox_arg": {
        "fr": "Boite a lire (defaut: EMAIL_MAILBOX ou INBOX)",
        "en": "Mailbox to read (default: EMAIL_MAILBOX or INBOX)",
    },
    "email_check_max_arg": {
        "fr": "Nombre max de messages a traiter (defaut: 10)",
        "en": "Maximum number of messages to process (default: 10)",
    },
    "email_send_cmd": {"fr": "Envoie un email via SMTP", "en": "Sends an email via SMTP"},
    "email_send_to_arg": {
        "fr": "Adresse email destinataire",
        "en": "Recipient email address",
    },
    "email_send_subject_arg": {"fr": "Objet de l'email", "en": "Email subject"},
    "email_send_body_arg": {"fr": "Corps de l'email", "en": "Email body"},
    "email_send_dry_run_arg": {
        "fr": "Affiche l'email sans l'envoyer",
        "en": "Shows the email without sending it",
    },
    "whatsapp_cmd": {
        "fr": "Envoie un message WhatsApp via l'API Cloud de Meta",
        "en": "Sends a WhatsApp message via Meta's Cloud API",
    },
    "whatsapp_to_arg": {
        "fr": "Numero destinataire (format E.164, ex: +33600000000)",
        "en": "Recipient number (E.164 format, e.g. +12025550123)",
    },
    "whatsapp_message_arg": {
        "fr": "Contenu du message a envoyer",
        "en": "Content of the message to send",
    },
    "whatsapp_dry_run_arg": {
        "fr": "Affiche le message sans l'envoyer",
        "en": "Shows the message without sending it",
    },
    "webhook_cmd": {
        "fr": "Demarre le serveur qui recoit les messages WhatsApp entrants",
        "en": "Starts the server that receives incoming WhatsApp messages",
    },
    "webhook_port_arg": {
        "fr": "Port d'ecoute (defaut: 8000)",
        "en": "Listening port (default: 8000)",
    },
    "doctor_cmd": {
        "fr": "Diagnostique la configuration (.env) et les modules utilisables",
        "en": "Diagnoses the configuration (.env) and usable modules",
    },
}

_STATUS_FIELD = {"fr": "statut", "en": "status"}
_STATUS_PREVIEW = {"fr": "apercu", "en": "preview"}
_STATUS_SENT = {"fr": "envoye", "en": "sent"}
_SUBJECT_FIELD = {"fr": "objet", "en": "subject"}
_BODY_FIELD = {"fr": "corps", "en": "body"}
_XLSX_FILE_FIELD = {"fr": "fichier_xlsx", "en": "xlsx_file"}
_DOCX_FILE_FIELD = {"fr": "fichier_docx", "en": "docx_file"}

_EMAIL_CHECK_TEXT_TEMPLATE = {
    "fr": "De: {from_}\nObjet: {subject}\n\n{body}",
    "en": "From: {from_}\nSubject: {subject}\n\n{body}",
}
_EMAIL_CHECK_ANALYSIS_FAILED_MESSAGES = {
    "fr": "[email-check] echec de l'analyse pour {uid}: {exc}",
    "en": "[email-check] analysis failed for {uid}: {exc}",
}
_EMAIL_CHECK_MARK_FAILED_MESSAGES = {
    "fr": "[email-check] echec du marquage comme lu: {exc}",
    "en": "[email-check] failed to mark as read: {exc}",
}


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    lang = get_lang()

    parser = argparse.ArgumentParser(prog="ops-agent")
    parser.add_argument("--version", action="version", version=f"ops-agent {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    triage_parser = subparsers.add_parser("triage", help=HELP["triage_cmd"][lang])
    triage_parser.add_argument("text", help=HELP["triage_text_arg"][lang])

    veille_parser = subparsers.add_parser("veille", help=HELP["veille_cmd"][lang])
    veille_parser.add_argument("text", help=HELP["veille_text_arg"][lang])

    feeds_parser = subparsers.add_parser("veille-feeds", help=HELP["veille_feeds_cmd"][lang])
    feeds_parser.add_argument("feeds_file", help=HELP["veille_feeds_file_arg"][lang])

    plan_parser = subparsers.add_parser("planification", help=HELP["planification_cmd"][lang])
    plan_parser.add_argument("text", help=HELP["planification_text_arg"][lang])

    resume_parser = subparsers.add_parser("resume", help=HELP["resume_cmd"][lang])
    resume_parser.add_argument("text", help=HELP["resume_text_arg"][lang])
    resume_parser.add_argument(
        "--export-docx", default=None, help=HELP["resume_export_docx_arg"][lang]
    )

    facturation_parser = subparsers.add_parser("facturation", help=HELP["facturation_cmd"][lang])
    facturation_parser.add_argument("text", help=HELP["facturation_text_arg"][lang])
    facturation_parser.add_argument(
        "--export-xlsx", default=None, help=HELP["facturation_export_xlsx_arg"][lang]
    )

    agenda_parser = subparsers.add_parser("agenda", help=HELP["agenda_cmd"][lang])
    agenda_parser.add_argument("text", help=HELP["agenda_text_arg"][lang])

    agenda_check_parser = subparsers.add_parser("agenda-check", help=HELP["agenda_check_cmd"][lang])
    agenda_check_parser.add_argument(
        "--date", default=None, help=HELP["agenda_check_date_arg"][lang]
    )

    crm_parser = subparsers.add_parser("crm", help=HELP["crm_cmd"][lang])
    crm_parser.add_argument("text", help=HELP["crm_text_arg"][lang])
    crm_parser.add_argument("--export-xlsx", default=None, help=HELP["crm_export_xlsx_arg"][lang])

    recherche_parser = subparsers.add_parser("recherche", help=HELP["recherche_cmd"][lang])
    recherche_parser.add_argument("text", help=HELP["recherche_text_arg"][lang])

    email_parser = subparsers.add_parser("email", help=HELP["email_cmd"][lang])
    email_parser.add_argument("text", help=HELP["email_text_arg"][lang])

    email_check_parser = subparsers.add_parser("email-check", help=HELP["email_check_cmd"][lang])
    email_check_parser.add_argument(
        "--mailbox", default=None, help=HELP["email_check_mailbox_arg"][lang]
    )
    email_check_parser.add_argument(
        "--max", type=int, default=10, help=HELP["email_check_max_arg"][lang]
    )

    email_send_parser = subparsers.add_parser("email-send", help=HELP["email_send_cmd"][lang])
    email_send_parser.add_argument("to", help=HELP["email_send_to_arg"][lang])
    email_send_parser.add_argument("subject", help=HELP["email_send_subject_arg"][lang])
    email_send_parser.add_argument("body", help=HELP["email_send_body_arg"][lang])
    email_send_parser.add_argument(
        "--dry-run", action="store_true", help=HELP["email_send_dry_run_arg"][lang]
    )

    whatsapp_parser = subparsers.add_parser("whatsapp", help=HELP["whatsapp_cmd"][lang])
    whatsapp_parser.add_argument("to", help=HELP["whatsapp_to_arg"][lang])
    whatsapp_parser.add_argument("message", help=HELP["whatsapp_message_arg"][lang])
    whatsapp_parser.add_argument(
        "--dry-run", action="store_true", help=HELP["whatsapp_dry_run_arg"][lang]
    )

    webhook_parser = subparsers.add_parser("webhook", help=HELP["webhook_cmd"][lang])
    webhook_parser.add_argument(
        "--port", type=int, default=8000, help=HELP["webhook_port_arg"][lang]
    )

    subparsers.add_parser("doctor", help=HELP["doctor_cmd"][lang])

    args = parser.parse_args(argv)

    if args.command == "webhook":
        from src.webhook import run as run_webhook

        run_webhook(port=args.port)
        return

    if args.command == "doctor":
        result = check_environment()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        modules = result[DIAGNOSTICS_FIELDS["modules"][lang]]
        issues_key = DIAGNOSTICS_FIELDS["issues"][lang]
        all_ok = not any(m[issues_key] for m in modules.values())
        sys.exit(0 if all_ok else 1)

    if args.command == "veille-feeds":
        result = veille(fetch_items_text(args.feeds_file))
        notify_if_urgent("veille-feeds", result)
    elif args.command == "agenda-check":
        day = date.fromisoformat(args.date) if args.date else None
        events = fetch_events(day=day)
        if events:
            text = "\n".join(f"{e['titre']}: {e['debut']} - {e['fin']}" for e in events)
            result = agenda(text)
        else:
            result = {
                AGENDA_FIELDS["conflicts"][lang]: [],
                AGENDA_FIELDS["free_slots"][lang]: [],
                AGENDA_FIELDS["suggestions"][lang]: [],
            }
        notify_if_urgent("agenda", result)
    elif args.command == "whatsapp":
        if args.dry_run:
            result = {
                _STATUS_FIELD[lang]: _STATUS_PREVIEW[lang],
                "to": args.to,
                "message": args.message,
            }
        else:
            result = send_whatsapp_message(args.to, args.message)
    elif args.command == "email-send":
        if args.dry_run:
            result = {
                _STATUS_FIELD[lang]: _STATUS_PREVIEW[lang],
                "to": args.to,
                _SUBJECT_FIELD[lang]: args.subject,
                _BODY_FIELD[lang]: args.body,
            }
        else:
            send_email(args.to, args.subject, args.body)
            result = {
                _STATUS_FIELD[lang]: _STATUS_SENT[lang],
                "to": args.to,
                _SUBJECT_FIELD[lang]: args.subject,
            }
    elif args.command == "facturation":
        result = facturation(args.text)
        if args.export_xlsx:
            chemin = facturation_export_xlsx(result, args.export_xlsx)
            result = {**result, _XLSX_FILE_FIELD[lang]: chemin}
        notify_if_urgent("facturation", result)
    elif args.command == "crm":
        result = crm(args.text)
        if args.export_xlsx:
            chemin = crm_export_xlsx(result, args.export_xlsx)
            result = {**result, _XLSX_FILE_FIELD[lang]: chemin}
        notify_if_urgent("crm", result)
    elif args.command == "resume":
        result = resume(args.text)
        if args.export_docx:
            chemin = resume_export_docx(result, args.export_docx)
            result = {**result, _DOCX_FILE_FIELD[lang]: chemin}
        notify_if_urgent("resume", result)
    elif args.command == "email-check":
        mailbox = args.mailbox or os.environ.get("EMAIL_MAILBOX") or "INBOX"
        messages = fetch_unread(mailbox=mailbox, max_messages=args.max)
        from_key = EMAIL_CLIENT_FIELDS["from"][lang]
        subject_key = EMAIL_CLIENT_FIELDS["subject"][lang]
        body_key = EMAIL_CLIENT_FIELDS["body"][lang]
        uid_key = EMAIL_CLIENT_FIELDS["uid"][lang]
        traites = []
        processed_uids = []
        for message in messages:
            text = _EMAIL_CHECK_TEXT_TEMPLATE[lang].format(
                from_=message[from_key], subject=message[subject_key], body=message[body_key]
            )
            try:
                analyse = email_triage(text)
            except Exception as exc:
                print(
                    _EMAIL_CHECK_ANALYSIS_FAILED_MESSAGES[lang].format(
                        uid=message[uid_key], exc=exc
                    ),
                    file=sys.stderr,
                )
                continue
            traites.append(
                {from_key: message[from_key], subject_key: message[subject_key], **analyse}
            )
            processed_uids.append(message[uid_key])
        result = {RESULT_FIELDS["processed"][lang]: traites}
        notify_if_urgent("email-check", result)
        if processed_uids:
            try:
                mark_as_read(processed_uids, mailbox=mailbox)
            except EmailClientError as exc:
                print(_EMAIL_CHECK_MARK_FAILED_MESSAGES[lang].format(exc=exc), file=sys.stderr)
    else:
        handlers: dict[str, Callable[[str], dict]] = {
            "triage": triage,
            "email": email_triage,
            "veille": veille,
            "planification": planification,
            "recherche": recherche,
            "agenda": agenda,
        }
        result = handlers[args.command](args.text)
        notify_if_urgent(args.command, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
