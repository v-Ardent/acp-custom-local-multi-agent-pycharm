"""
LAB 2 — Orchestration, pattern ROUTER                                     [SOLUTION]

    demande -> Routeur (1 appel LLM : "quelle catégorie ?") -> UN SEUL agent -> réponse

Simple, rapide et peu coûteux. Mais si la demande concerne plusieurs agents,
un seul sera appelé : la réponse sera incomplète (voir la dernière demande de test).

Lancer (depuis le dossier code/) :  python lab2_orchestration/solution/orchestrateur_router.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, nouvelle_demande, resume_couts
from agents_secretariat import agent_absences, agent_horaires, agent_reglement

# Catégorie -> agent spécialisé
AGENTS = {
    "horaires": agent_horaires,
    "reglement": agent_reglement,
    "absences": agent_absences,
}

# TODO 2 : le prompt du routeur : les catégories possibles et un format de réponse strict
PROMPT_ROUTEUR = """Tu es le routeur du secrétariat d'une haute école.
Classe la demande de l'étudiant dans UNE seule catégorie :
- horaires  : jours, heures, locaux, professeurs des cours
- reglement : règles des études (absences en général, retards, examens, plagiat, IA)
- absences  : les absences d'un étudiant précis (avec un matricule)
Réponds uniquement par le nom de la catégorie, en un seul mot, sans rien d'autre."""


def classer(demande):
    """TODO 3 : demande au LLM la catégorie et renvoie une clé de AGENTS (ou None)."""
    messages = [
        {"role": "system", "content": PROMPT_ROUTEUR},
        {"role": "user", "content": demande},
    ]
    texte = chat(messages, agent="Routeur", temperature=0).content or ""
    texte = texte.lower().replace("è", "e")      # "Règlement" -> "reglement"
    for categorie in AGENTS:                      # on tolère un peu de texte autour du mot
        if categorie in texte:
            return categorie
    return None


def router(demande):
    """TODO 4 : classe la demande puis la transmet à l'agent choisi."""
    nouvelle_demande()  # pour mesurer le coût de chaque demande (lab 3)
    traces.tracer("Routeur", "DEMANDE", demande)
    categorie = classer(demande)
    if categorie is None:
        traces.tracer("Routeur", "INFO", "Catégorie inconnue : demande non transmise.")
        return "Désolé, je ne sais pas à quel service transmettre votre demande."
    traces.tracer("Routeur", "ACTION", f"transmission à : {AGENTS[categorie].nom}")
    return AGENTS[categorie].run(demande)


if __name__ == "__main__":
    traces.titre(f"Lab 2 : orchestrateur ROUTER (modèle : {MODELE})")
    demandes = [
        "Dans quel local a lieu le cours d'Anglais technique ?",
        "Que dit le règlement sur l'utilisation de ChatGPT ?",
        "Combien d'absences a l'étudiant E24002 ?",
        # Demande qui concerne DEUX agents : que va faire le routeur ?
        "L'étudiante E24003 a-t-elle trop d'absences pour passer ses examens selon le règlement ?",
    ]
    for demande in demandes:
        router(demande)  # la réponse de l'agent choisi s'affiche dans les traces ([RÉPONSE])
        print()
    resume_couts()
