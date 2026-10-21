"""
LAB 2 — Orchestration, pattern SUPERVISOR

    demande -> Superviseur (un agent dont les OUTILS sont les autres agents)
                  -> appelle un agent, lit sa réponse, en appelle un autre si besoin...
                  -> SYNTHÈSE finale

Plus souple que le router (plusieurs agents, dans l'ordre qu'il choisit),
mais plus d'appels au LLM : plus lent et plus cher.

Complétez les TODO 5 et 6, puis lancez (depuis le dossier code/) :
    python lab2_orchestration/enonce/orchestrateur_supervisor.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.agent import Agent
from common.llm import MODELE, nouvelle_demande, resume_couts
from agents_secretariat import agent_absences, agent_horaires, agent_reglement

# TODO 5 : transformez chaque agent en outil pour le superviseur.
#   La méthode agent.comme_outil(nom_outil, description) renvoie un couple (fonction, schéma).
#   Exemple pour le premier :
#       agent_horaires.comme_outil("demander_agent_horaires",
#                                  "Questions sur les cours : jour, heure, local, professeur.")
#   La description est capitale : c'est ce que lit le superviseur pour choisir à qui déléguer.
OUTILS_SUPERVISEUR = [
    # ... les 3 agents ici
]

# TODO 6 : écrivez les instructions du superviseur.
#   - Il ne répond jamais lui-même : il délègue.
#   - Qui sait quoi ? (seul l'agent absences connaît les étudiants, etc.)
#   - IMPORTANT : chaque agent ne voit QUE le message que le superviseur lui écrit.
#     Il doit donc y mettre toutes les infos utiles (matricule, nom du cours...).
#   - À la fin : une synthèse claire et brève.
PROMPT_SUPERVISEUR = """À compléter"""

if __name__ == "__main__":
    if not OUTILS_SUPERVISEUR:
        raise NotImplementedError("TODO 5 : transformez les 3 agents en outils (OUTILS_SUPERVISEUR).")
    if "À compléter" in PROMPT_SUPERVISEUR:
        raise NotImplementedError("TODO 6 : écrivez les instructions du superviseur (PROMPT_SUPERVISEUR).")

    superviseur = Agent(
        nom="Superviseur",
        instructions=PROMPT_SUPERVISEUR,
        outils=OUTILS_SUPERVISEUR,
        max_iterations=8,
    )

    traces.titre(f"Lab 2 : orchestrateur SUPERVISOR (modèle : {MODELE})")
    demande = ("L'étudiante E24003 a-t-elle trop d'absences pour passer ses examens selon le règlement ? "
               "Et quand a lieu le cours concerné ?")
    nouvelle_demande()
    traces.encadre(superviseur.run(demande), "Synthèse du superviseur", "magenta")
    resume_couts()

# À OBSERVER / COMPARER avec le router :
#   - Combien d'agents ont été appelés ? Dans quel ordre ? Qui l'a décidé ?
#   - Combien d'appels LLM et de tokens au total, comparé au router ?
#   - Relancez 2-3 fois : le superviseur suit-il toujours le même chemin ?
