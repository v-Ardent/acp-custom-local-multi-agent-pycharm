"""
VOS AGENTS ET VOS OUTILS — c'est ce fichier que vous remplacez par votre projet.

Exemple fourni (à jeter) :
    Superviseur ─┬─> Agent recherche  (outil RÉEL : résumé Wikipédia)
                 └─> Agent rédacteur  (outil : proposer_action -> validation humaine dans l'interface)
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common.agent import Agent
from common.llm import schema_outil

# Actions sensibles proposées par les agents, en attente de validation humaine (lues par app.py)
ACTIONS_EN_ATTENTE = []


# --- OUTILS ------------------------------------------------------------------------

def chercher_wikipedia(sujet):
    """Outil réel : résumé de la page Wikipédia (français) d'un sujet."""
    url = "https://fr.wikipedia.org/api/rest_v1/page/summary/" + sujet.replace(" ", "_")
    reponse = requests.get(url, timeout=10, headers={"User-Agent": "labo-agents-henallux/1.0"})
    if reponse.status_code != 200:
        return f"Aucune page Wikipédia trouvée pour '{sujet}'."
    return reponse.json().get("extract", "")


def proposer_action(description):
    """N'exécute RIEN : ajoute l'action à la liste d'attente, un humain décidera."""
    ACTIONS_EN_ATTENTE.append(description)
    return "Action enregistrée : elle sera exécutée seulement si un humain la valide."


def executer_action(description):
    """Appelée par l'interface quand l'humain clique sur Valider. À remplacer par la vraie action."""
    return f"Action exécutée (simulation) : {description}"


SCHEMA_WIKIPEDIA = schema_outil(
    "chercher_wikipedia", "Donne le résumé de l'article Wikipédia (en français) sur un sujet.",
    {"sujet": {"type": "string", "description": "Titre de l'article, ex. 'Namur'"}})

SCHEMA_PROPOSER_ACTION = schema_outil(
    "proposer_action",
    "Propose une action concrète (envoyer, publier, réserver...). Elle devra être validée par un humain.",
    {"description": {"type": "string", "description": "Description précise de l'action à réaliser"}})


# --- AGENTS --------------------------------------------------------------------------

agent_recherche = Agent(
    nom="Agent recherche",
    instructions="Tu cherches des informations factuelles avec l'outil chercher_wikipedia. "
                 "Réponds par un résumé court des faits trouvés, sans rien inventer.",
    outils=[(chercher_wikipedia, SCHEMA_WIKIPEDIA)],
)

agent_redacteur = Agent(
    nom="Agent rédacteur",
    instructions="Tu rédiges des textes clairs et courts en français à partir des informations reçues. "
                 "Si la demande implique une action (envoyer, publier...), appelle proposer_action "
                 "au lieu de dire que c'est fait.",
    outils=[(proposer_action, SCHEMA_PROPOSER_ACTION)],
)


def creer_superviseur():
    """L'orchestrateur (pattern Supervisor) : ses outils sont les agents."""
    return Agent(
        nom="Superviseur",
        instructions="Tu coordonnes une équipe d'agents. Tu ne réponds jamais de toi-même : "
                     "1) demande les faits à l'agent recherche, 2) demande le texte final à l'agent "
                     "rédacteur en lui transmettant ces faits, 3) renvoie le texte du rédacteur.",
        outils=[
            agent_recherche.comme_outil("demander_agent_recherche", "Cherche des informations factuelles."),
            agent_redacteur.comme_outil("demander_agent_redacteur",
                                        "Rédige le texte final (et propose une action si nécessaire)."),
        ],
        max_iterations=8,
    )
