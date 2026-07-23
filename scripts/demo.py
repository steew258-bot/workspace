"""Demo hors-ligne d'Ops Agent : rejoue chaque module avec un exemple realiste,
sans appeler l'API Anthropic ni necessiter aucune configuration.

Usage:
    python scripts/demo.py

Les sorties affichees sont des exemples representatifs (pre-enregistres),
pas de vrais appels reseau - utile pour montrer ce que fait chaque module
avant meme d'avoir configure une cle API.
"""

import json

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

SEPARATOR = "-" * 70


def run() -> None:
    print(SEPARATOR)
    print(" DEMO OPS AGENT (sorties simulees, aucun appel reseau)")
    print(SEPARATOR)

    for demo in DEMOS:
        print(f"\n[{demo['module']}]")
        print(f"$ {demo['commande']}\n")
        print(json.dumps(demo["sortie"], ensure_ascii=False, indent=2))
        if demo.get("note"):
            print(f"\nNote : {demo['note']}")
        print(f"\n{SEPARATOR}")

    print("\nCeci est un apercu. Avec une vraie cle ANTHROPIC_API_KEY configuree")
    print("(voir GETTING_STARTED.md), ces commandes tournent pour de vrai sur")
    print("ton propre texte : `python app.py doctor` te dit ce qu'il reste a")
    print("configurer.")


if __name__ == "__main__":
    run()
