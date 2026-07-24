"""Demo hors-ligne d'Ops Agent : rejoue chaque module avec un exemple realiste,
sans appeler l'API Anthropic ni necessiter aucune configuration.

Usage:
    python scripts/demo.py
    OPS_AGENT_LANG=en python scripts/demo.py

Les sorties affichees sont des exemples representatifs (pre-enregistres),
pas de vrais appels reseau - utile pour montrer ce que fait chaque module
avant meme d'avoir configure une cle API.
"""

import json
import os

_DEFAULT_LANG = "fr"


def _get_lang(lang: str | None = None) -> str:
    return lang or os.environ.get("OPS_AGENT_LANG", _DEFAULT_LANG)


DEMOS = [
    {
        "module": "triage",
        "commande": 'python app.py triage "Le client X demande un geste commercial avant vendredi"',
        "sortie": {
            "action": "Rappeler le client X avant vendredi avec une proposition concrete",
            "urgence": "haute",
            "brouillon_reponse": (
                "Bonjour, je comprends votre demande et je reviens vers vous avant "
                "vendredi avec une proposition."
            ),
        },
    },
    {
        "module": "veille",
        "commande": 'python app.py veille "$(cat docs/veille-sources.txt)"',
        "sortie": {
            "a_traiter": [
                {
                    "titre": "Lindy leve des fonds et cible l'automatisation cross-app",
                    "raison": "concurrent direct, evolution du positionnement prix",
                }
            ],
            "archive": ["Annonce mineure sans impact direct"],
        },
    },
    {
        "module": "planification",
        "commande": (
            'python app.py planification "Repondre a 3 clients, preparer un devis, '
            'relancer un impaye"'
        ),
        "sortie": {
            "ordre": ["Relancer l'impaye", "Repondre aux 3 clients", "Preparer le devis"],
            "tache_prioritaire": "Relancer l'impaye",
            "justification": "Impact direct sur la tresorerie, delai deja depasse",
        },
    },
    {
        "module": "resume",
        "commande": 'python app.py resume "$(cat compte-rendu.txt)"',
        "sortie": {
            "resume": (
                "Le projet avance conformement au planning ; deux points de blocage "
                "restent a lever avant la livraison."
            ),
            "points_cles": ["Budget valide", "Delai serre sur le lot 2"],
        },
    },
    {
        "module": "resume",
        "commande": ('python app.py resume "$(cat compte-rendu.txt)" --export-docx rapport.docx'),
        "sortie": {
            "resume": (
                "Le projet avance conformement au planning ; deux points de blocage "
                "restent a lever avant la livraison."
            ),
            "points_cles": ["Budget valide", "Delai serre sur le lot 2"],
            "fichier_docx": "rapport.docx",
        },
        "note": (
            "--export-docx genere un vrai document Word via les Agent Skills Anthropic "
            "(fonctionnalite beta, cf. `python app.py doctor`)."
        ),
    },
    {
        "module": "email",
        "commande": (
            'python app.py email "De: client@exemple.com\\nObjet: Panne serveur\\n\\n'
            'Le serveur est down depuis 10 minutes."'
        ),
        "sortie": {
            "urgence": "haute",
            "necessite_reponse": True,
            "action": "Rappeler le client dans l'heure",
            "brouillon_reponse": "Bonjour, nous prenons en charge l'incident immediatement.",
        },
    },
    {
        "module": "recherche",
        "commande": 'python app.py recherche "Quelles sont les dernieres annonces d\'Anthropic ?"',
        "sortie": {
            "reponse": "Anthropic a annonce plusieurs nouveaux modeles et partenariats recemment.",
            "sources": ["https://www.anthropic.com/news"],
        },
    },
    {
        "module": "crm",
        "commande": (
            'python app.py crm "Appel du 12/07 : interesse mais budget pas encore '
            'valide, doit revenir vers nous."'
        ),
        "sortie": {
            "statut": "a relancer",
            "relance_a_faire": True,
            "action": "Relancer par email dans 5 jours si pas de nouvelles",
            "risque_churn": "moyen",
        },
    },
    {
        "module": "crm",
        "commande": (
            'python app.py crm "Appel du 12/07 : interesse mais budget pas encore '
            'valide, doit revenir vers nous." --export-xlsx fiches/dupont.xlsx'
        ),
        "sortie": {
            "statut": "a relancer",
            "relance_a_faire": True,
            "action": "Relancer par email dans 5 jours si pas de nouvelles",
            "risque_churn": "moyen",
            "fichier_xlsx": "fiches/dupont.xlsx",
        },
        "note": (
            "--export-xlsx genere une vraie fiche de suivi client Excel via les Agent "
            "Skills Anthropic (fonctionnalite beta, cf. `python app.py doctor`)."
        ),
    },
    {
        "module": "agenda",
        "commande": (
            'python app.py agenda "RDV client 14h-15h ; appel fournisseur 14h30 ; dentiste 17h"'
        ),
        "sortie": {
            "conflits": [
                {
                    "evenements": ["RDV client 14h-15h", "Appel fournisseur 14h30"],
                    "raison": "chevauchement direct",
                }
            ],
            "creneaux_libres": ["9h-14h", "15h-17h"],
            "suggestions": ["Decaler l'appel fournisseur a 15h30"],
        },
    },
    {
        "module": "facturation",
        "commande": 'python app.py facturation "2 jours de dev a 500e/jour pour le client Dupont"',
        "sortie": {
            "client": "Dupont",
            "lignes": [
                {"designation": "Journee de developpement", "quantite": 2, "prix_unitaire": 500}
            ],
            "total_estime": 1000,
            "notes": "",
        },
    },
    {
        "module": "facturation",
        "commande": (
            'python app.py facturation "2 jours de dev a 500e/jour pour le client Dupont" '
            "--export-xlsx factures/dupont.xlsx"
        ),
        "sortie": {
            "client": "Dupont",
            "lignes": [
                {"designation": "Journee de developpement", "quantite": 2, "prix_unitaire": 500}
            ],
            "total_estime": 1000,
            "notes": "",
            "fichier_xlsx": "factures/dupont.xlsx",
        },
        "note": (
            "--export-xlsx genere un vrai fichier Excel via les Agent Skills Anthropic "
            "(fonctionnalite beta, cf. `python app.py doctor`)."
        ),
    },
]

DEMOS_EN = [
    {
        "module": "triage",
        "commande": (
            'python app.py triage "Client X is asking for a goodwill gesture before Friday"'
        ),
        "sortie": {
            "action": "Call client X back before Friday with a concrete proposal",
            "urgency": "high",
            "reply_draft": (
                "Hi, I understand your request and will get back to you before Friday "
                "with a proposal."
            ),
        },
    },
    {
        "module": "veille",
        "commande": 'python app.py veille "$(cat docs/veille-sources.txt)"',
        "sortie": {
            "to_review": [
                {
                    "title": "Lindy raises funding and targets cross-app automation",
                    "reason": "direct competitor, pricing positioning shift",
                }
            ],
            "archived": ["Minor announcement with no direct impact"],
        },
    },
    {
        "module": "planification",
        "commande": (
            'python app.py planification "Reply to 3 clients, prepare a quote, '
            'chase an unpaid invoice"'
        ),
        "sortie": {
            "order": [
                "Chase the unpaid invoice",
                "Reply to the 3 clients",
                "Prepare the quote",
            ],
            "priority_task": "Chase the unpaid invoice",
            "justification": "Direct impact on cash flow, deadline already passed",
        },
    },
    {
        "module": "resume",
        "commande": 'python app.py resume "$(cat report.txt)"',
        "sortie": {
            "summary": (
                "The project is on track; two blocking points still need to be "
                "resolved before delivery."
            ),
            "key_points": ["Budget approved", "Tight deadline on lot 2"],
        },
    },
    {
        "module": "resume",
        "commande": ('python app.py resume "$(cat report.txt)" --export-docx report.docx'),
        "sortie": {
            "summary": (
                "The project is on track; two blocking points still need to be "
                "resolved before delivery."
            ),
            "key_points": ["Budget approved", "Tight deadline on lot 2"],
            "docx_file": "report.docx",
        },
        "note": (
            "--export-docx generates a real Word document via Anthropic Agent Skills "
            "(beta feature, see `python app.py doctor`)."
        ),
    },
    {
        "module": "email",
        "commande": (
            'python app.py email "From: client@example.com\\nSubject: Server outage\\n\\n'
            'The server has been down for 10 minutes."'
        ),
        "sortie": {
            "urgency": "high",
            "requires_reply": True,
            "action": "Call the client back within the hour",
            "reply_draft": "Hi, we're handling the incident immediately.",
        },
    },
    {
        "module": "recherche",
        "commande": 'python app.py recherche "What are Anthropic\'s latest announcements?"',
        "sortie": {
            "response": "Anthropic recently announced several new models and partnerships.",
            "sources": ["https://www.anthropic.com/news"],
        },
    },
    {
        "module": "crm",
        "commande": (
            'python app.py crm "Call on 07/12: interested but budget not yet '
            'approved, will get back to us."'
        ),
        "sortie": {
            "status": "needs follow-up",
            "follow_up_needed": True,
            "action": "Follow up by email in 5 days if no news",
            "churn_risk": "medium",
        },
    },
    {
        "module": "crm",
        "commande": (
            'python app.py crm "Call on 07/12: interested but budget not yet '
            'approved, will get back to us." --export-xlsx sheets/smith.xlsx'
        ),
        "sortie": {
            "status": "needs follow-up",
            "follow_up_needed": True,
            "action": "Follow up by email in 5 days if no news",
            "churn_risk": "medium",
            "xlsx_file": "sheets/smith.xlsx",
        },
        "note": (
            "--export-xlsx generates a real Excel customer follow-up sheet via "
            "Anthropic Agent Skills (beta feature, see `python app.py doctor`)."
        ),
    },
    {
        "module": "agenda",
        "commande": (
            'python app.py agenda "Client meeting 2-3pm ; supplier call 2:30pm ; dentist 5pm"'
        ),
        "sortie": {
            "conflicts": [
                {
                    "events": ["Client meeting 2-3pm", "Supplier call 2:30pm"],
                    "reason": "direct overlap",
                }
            ],
            "free_slots": ["9am-2pm", "3pm-5pm"],
            "suggestions": ["Move the supplier call to 3:30pm"],
        },
    },
    {
        "module": "facturation",
        "commande": 'python app.py facturation "2 days of dev at $500/day for client Smith"',
        "sortie": {
            "client": "Smith",
            "line_items": [{"description": "Day of development", "quantity": 2, "unit_price": 500}],
            "estimated_total": 1000,
            "notes": "",
        },
    },
    {
        "module": "facturation",
        "commande": (
            'python app.py facturation "2 days of dev at $500/day for client Smith" '
            "--export-xlsx invoices/smith.xlsx"
        ),
        "sortie": {
            "client": "Smith",
            "line_items": [{"description": "Day of development", "quantity": 2, "unit_price": 500}],
            "estimated_total": 1000,
            "notes": "",
            "xlsx_file": "invoices/smith.xlsx",
        },
        "note": (
            "--export-xlsx generates a real Excel file via Anthropic Agent Skills "
            "(beta feature, see `python app.py doctor`)."
        ),
    },
]

SEPARATOR = "-" * 70

_BANNER = {
    "fr": " DEMO OPS AGENT (sorties simulees, aucun appel reseau)",
    "en": " OPS AGENT DEMO (simulated outputs, no network calls)",
}
_NOTE_LABEL = {"fr": "Note : {note}", "en": "Note: {note}"}
_CLOSING = {
    "fr": (
        "\nCeci est un apercu. Avec une vraie cle ANTHROPIC_API_KEY configuree\n"
        "(voir GETTING_STARTED.md), ces commandes tournent pour de vrai sur\n"
        "ton propre texte : `python app.py doctor` te dit ce qu'il reste a\n"
        "configurer."
    ),
    "en": (
        "\nThis is a preview. With a real ANTHROPIC_API_KEY configured\n"
        "(see GETTING_STARTED.en.md), these commands run for real on\n"
        "your own text: `python app.py doctor` tells you what's left to\n"
        "configure."
    ),
}


def run(lang: str | None = None) -> None:
    lang = _get_lang(lang)
    demos = DEMOS if lang == "fr" else DEMOS_EN

    print(SEPARATOR)
    print(_BANNER[lang])
    print(SEPARATOR)

    for demo in demos:
        print(f"\n[{demo['module']}]")
        print(f"$ {demo['commande']}\n")
        print(json.dumps(demo["sortie"], ensure_ascii=False, indent=2))
        if demo.get("note"):
            print(f"\n{_NOTE_LABEL[lang].format(note=demo['note'])}")
        print(f"\n{SEPARATOR}")

    print(_CLOSING[lang])


if __name__ == "__main__":
    run()
