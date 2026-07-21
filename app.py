import argparse
import json

from src.modules.feeds import fetch_items_text
from src.modules.planification import planification
from src.modules.resume import resume
from src.modules.triage import triage
from src.modules.veille import veille
from src.modules.whatsapp import send_whatsapp_message
from src.notifications import notify_if_urgent


def main(argv=None):
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

    args = parser.parse_args(argv)

    if args.command == "webhook":
        from src.webhook import run as run_webhook

        run_webhook(port=args.port)
        return

    if args.command == "veille-feeds":
        result = veille(fetch_items_text(args.feeds_file))
        notify_if_urgent("veille-feeds", result)
    elif args.command == "whatsapp":
        result = send_whatsapp_message(args.to, args.message)
    else:
        handlers = {
            "triage": triage,
            "veille": veille,
            "planification": planification,
            "resume": resume,
        }
        result = handlers[args.command](args.text)
        notify_if_urgent(args.command, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
