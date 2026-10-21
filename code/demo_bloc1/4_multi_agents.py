"""
DÉMO 4/4 — Plusieurs agents coordonnés par un orchestrateur (pattern Supervisor).

  Superviseur ─┬─> Agent météo      (outil : meteo)
               ├─> Agent activités  (outils : chercher_activites, calculer_budget)
               └─> Agent rédacteur  (pas d'outil : il écrit le mail à la classe)

Le superviseur est lui-même un agent : ses "outils" sont les autres agents.
Il décide qui appeler, dans quel ordre, et assemble le tout.
Avant "l'envoi" du mail, un HUMAIN valide (human-in-the-loop).

Lancer (depuis le dossier code/) :  python demo_bloc1/4_multi_agents.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common import traces
from common.agent import Agent
from common.llm import MODELE, resume_couts
from outils_sortie import (SCHEMA_CALCULER_BUDGET, SCHEMA_CHERCHER_ACTIVITES, SCHEMA_METEO,
                           calculer_budget, chercher_activites, meteo)

DEMANDE = ("Organise la sortie de classe de samedi à Namur pour 22 étudiants "
           "(15 euros maximum par personne) et prépare le mail pour prévenir la classe.")

# --- Les 3 agents spécialisés ---------------------------------------------------

agent_meteo = Agent(
    nom="Agent météo",
    instructions="Tu es météorologue. Utilise l'outil meteo et résume la prévision en 2 phrases "
                 "(ciel, températures, pluie). Termine par 'beau' ou 'mauvais' temps.",
    outils=[(meteo, SCHEMA_METEO)],
)

agent_activites = Agent(
    nom="Agent activités",
    instructions="Tu choisis UNE activité de groupe adaptée à la météo et au budget. "
                 "1) Appelle chercher_activites (meteo='mauvais' seulement si de la pluie est annoncée). "
                 "2) Choisis une activité dans le budget. "
                 "3) Appelle TOUJOURS calculer_budget (ne calcule jamais de tête). "
                 "Réponds : nom de l'activité, durée, prix par personne, coût total.",
    outils=[(chercher_activites, SCHEMA_CHERCHER_ACTIVITES), (calculer_budget, SCHEMA_CALCULER_BUDGET)],
)

agent_redacteur = Agent(
    nom="Agent rédacteur",
    instructions="Tu rédiges des mails courts, clairs et sympathiques pour une classe d'étudiants. "
                 "Commence par une ligne 'Objet : ...'. Utilise uniquement les informations fournies : "
                 "n'invente ni heure ni lieu de rendez-vous, écris [à compléter] si une info manque.",
)

# --- Le superviseur : ses outils sont les 3 agents -------------------------------

brouillon = {"mail": None}   # on garde le dernier mail rédigé, pour la validation humaine


def deleguer_redaction(demande):
    """Appelle l'agent rédacteur et garde son mail de côté (pour la validation humaine)."""
    brouillon["mail"] = agent_redacteur.run(demande)
    return brouillon["mail"]


_, schema_redacteur = agent_redacteur.comme_outil(
    "demander_agent_redacteur",
    "Rédige le mail à la classe. Donne-lui TOUTES les infos : date, météo, activité, coût.")

superviseur = Agent(
    nom="Superviseur",
    instructions="""Tu coordonnes une équipe d'agents pour organiser une sortie de classe.
Étapes, dans l'ordre, en appelant UN agent à la fois :
1. demander_agent_meteo : la météo du jour de la sortie.
2. demander_agent_activites : une activité adaptée (transmets la météo, la ville, le nombre d'étudiants et le budget).
3. demander_agent_redacteur : le mail à la classe (transmets toutes les informations obtenues).
Quand le mail est rédigé, réponds simplement 'Mail prêt pour validation.'""",
    outils=[
        agent_meteo.comme_outil("demander_agent_meteo", "Donne la météo prévue pour une ville et un jour."),
        agent_activites.comme_outil("demander_agent_activites",
                                    "Choisit une activité de groupe adaptée à la météo et au budget, avec le coût total."),
        (deleguer_redaction, schema_redacteur),
    ],
    max_iterations=8,
)

# --- Exécution --------------------------------------------------------------------

traces.titre(f"Démo 4 : orchestrateur + 3 agents (modèle : {MODELE})")
superviseur.run(DEMANDE)   # affiche lui-même la demande dans les traces

# --- Validation humaine avant l'action "sensible" (envoyer un mail) --------------
if brouillon["mail"] is None:
    traces.tracer("Superviseur", "INFO", "Aucun mail n'a été rédigé : rien à envoyer.")
else:
    traces.encadre(brouillon["mail"], "Brouillon du mail", "magenta")
    try:
        choix = input("Valider l'envoi ? o/n : ").strip().lower()
    except EOFError:
        choix = "n"
    if choix == "o":
        traces.tracer("Humain", "HUMAIN", "Envoi validé.")
        traces.console.print("[bold green]Mail envoyé à classe-3intar@exemple.be (simulation).[/]")
    else:
        traces.tracer("Humain", "HUMAIN", "Envoi refusé : le mail n'est pas parti.")

resume_couts()
