import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import date

from src.diagnostics import check as check_environment
from src.modules.agenda import agenda
from src.modules.calendar_client import fetch_events
from src.modules.crm import crm, crm_export_xlsx
from src.modules.email import email as email_triage
from src.modules.email_client import EmailClientError, fetch_unread, mark_as_read, send_email
from src.modules.facturation import facturation, facturation_export_xlsx
from src.modules.feeds import fetch_items_text
from src.modules.planification import planification
from src.modules.recherche import recherche
from src.modules.resume import resume, resume_export_docx
from src.modules.triage import triage
from src.modules.veille import veille
from src.modules.whatsapp import send_whatsapp_message
from src.notifications import notify_if_urgent


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="ops-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    triage_parser = subparsers.add_parser("triage", help="Analyse un texte et propose une action")
    triage_parser.add_argument("text", help="Texte a trier (email, tache, notification...)")

    veille_parser = subparsers.add_parser("veille", help="Priorise une liste d'infos/alertes")
    veille_parser.add_argument("text", help="Liste brute d'infos/alertes (une par ligne)")

    feeds_parser = subparsers.add_parser(
        "veille-feeds", help="Recupere des flux RSS et priorise le resultat avec veille"
    )
    feeds_parser.add_argument("feeds_file", help="Fichier avec une URL de flux RSS par ligne")

    plan_parser = subparsers.add_parser(
        "planification", help="Priorise les taches et contraintes du jour"
    )
    plan_parser.add_argument("text", help="Taches et contraintes du jour")

    resume_parser = subparsers.add_parser(
        "resume", help="Resume un texte long en points cles"
    )
    resume_parser.add_argument("text", help="Texte long a resumer (compte-rendu, doc, emails...)")
    resume_parser.add_argument(
        "--export-docx",
        default=None,
        help="Chemin du fichier .docx a generer pour ce resume (beta, cf. doctor)",
    )

    facturation_parser = subparsers.add_parser(
        "facturation", help="Genere un brouillon de devis structure a partir d'une description"
    )
    facturation_parser.add_argument("text", help="Description de la prestation ou des produits")
    facturation_parser.add_argument(
        "--export-xlsx",
        default=None,
        help="Chemin du fichier .xlsx a generer pour ce devis (beta, cf. doctor)",
    )

    agenda_parser = subparsers.add_parser(
        "agenda", help="Analyse evenements/contraintes du jour: conflits, creneaux, suggestions"
    )
    agenda_parser.add_argument("text", help="Evenements et contraintes du jour")

    agenda_check_parser = subparsers.add_parser(
        "agenda-check",
        help="Recupere les evenements du jour sur Google Calendar et detecte les conflits",
    )
    agenda_check_parser.add_argument(
        "--date", default=None, help="Date a verifier au format AAAA-MM-JJ (defaut: aujourd'hui)"
    )

    crm_parser = subparsers.add_parser(
        "crm", help="Analyse des notes d'echanges client et propose statut/action/risque"
    )
    crm_parser.add_argument("text", help="Notes d'echanges avec le client ou prospect")
    crm_parser.add_argument(
        "--export-xlsx",
        default=None,
        help="Chemin du fichier .xlsx a generer pour cette fiche client (beta, cf. doctor)",
    )

    recherche_parser = subparsers.add_parser(
        "recherche", help="Recherche web en temps reel via Perplexity, avec sources"
    )
    recherche_parser.add_argument("text", help="Question a rechercher sur le web")

    email_parser = subparsers.add_parser(
        "email", help="Analyse un email brut (expediteur/objet/corps) et propose une action"
    )
    email_parser.add_argument("text", help="Texte brut de l'email (expediteur, objet, corps)")

    email_check_parser = subparsers.add_parser(
        "email-check", help="Recupere les emails non lus par IMAP et les triage automatiquement"
    )
    email_check_parser.add_argument(
        "--mailbox", default=None, help="Boite a lire (defaut: EMAIL_MAILBOX ou INBOX)"
    )
    email_check_parser.add_argument(
        "--max", type=int, default=10, help="Nombre max de messages a traiter (defaut: 10)"
    )

    email_send_parser = subparsers.add_parser("email-send", help="Envoie un email via SMTP")
    email_send_parser.add_argument("to", help="Adresse email destinataire")
    email_send_parser.add_argument("subject", help="Objet de l'email")
    email_send_parser.add_argument("body", help="Corps de l'email")

    whatsapp_parser = subparsers.add_parser(
        "whatsapp", help="Envoie un message WhatsApp via l'API Cloud de Meta"
    )
    whatsapp_parser.add_argument("to", help="Numero destinataire (format E.164, ex: +33600000000)")
    whatsapp_parser.add_argument("message", help="Contenu du message a envoyer")

    webhook_parser = subparsers.add_parser(
        "webhook", help="Demarre le serveur qui recoit les messages WhatsApp entrants"
    )
    webhook_parser.add_argument(
        "--port", type=int, default=8000, help="Port d'ecoute (defaut: 8000)"
    )

    subparsers.add_parser(
        "doctor", help="Diagnostique la configuration (.env) et les modules utilisables"
    )

    args = parser.parse_args(argv)

    if args.command == "webhook":
        from src.webhook import run as run_webhook

        run_webhook(port=args.port)
        return

    if args.command == "doctor":
        result = check_environment()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        all_ok = all(m["statut"] == "ok" for m in result["modules"].values())
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
            result = {"conflits": [], "creneaux_libres": [], "suggestions": []}
        notify_if_urgent("agenda", result)
    elif args.command == "whatsapp":
        result = send_whatsapp_message(args.to, args.message)
    elif args.command == "email-send":
        send_email(args.to, args.subject, args.body)
        result = {"statut": "envoye", "to": args.to, "objet": args.subject}
    elif args.command == "facturation":
        result = facturation(args.text)
        if args.export_xlsx:
            chemin = facturation_export_xlsx(result, args.export_xlsx)
            result = {**result, "fichier_xlsx": chemin}
        notify_if_urgent("facturation", result)
    elif args.command == "crm":
        result = crm(args.text)
        if args.export_xlsx:
            chemin = crm_export_xlsx(result, args.export_xlsx)
            result = {**result, "fichier_xlsx": chemin}
        notify_if_urgent("crm", result)
    elif args.command == "resume":
        result = resume(args.text)
        if args.export_docx:
            chemin = resume_export_docx(result, args.export_docx)
            result = {**result, "fichier_docx": chemin}
        notify_if_urgent("resume", result)
    elif args.command == "email-check":
        mailbox = args.mailbox or os.environ.get("EMAIL_MAILBOX") or "INBOX"
        messages = fetch_unread(mailbox=mailbox, max_messages=args.max)
        traites = []
        processed_uids = []
        for message in messages:
            text = f"De: {message['de']}\nObjet: {message['objet']}\n\n{message['corps']}"
            try:
                analyse = email_triage(text)
            except Exception as exc:
                print(
                    f"[email-check] echec de l'analyse pour {message['uid']}: {exc}",
                    file=sys.stderr,
                )
                continue
            traites.append({"de": message["de"], "objet": message["objet"], **analyse})
            processed_uids.append(message["uid"])
        result = {"traites": traites}
        notify_if_urgent("email-check", result)
        if processed_uids:
            try:
                mark_as_read(processed_uids, mailbox=mailbox)
            except EmailClientError as exc:
                print(f"[email-check] echec du marquage comme lu: {exc}", file=sys.stderr)
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
