"""
LAB 2 — Orchestration, pattern SUPERVISOR                                 [SOLUTION]

    demande -> Superviseur (un agent dont les OUTILS sont les autres agents)
                  -> appelle un agent, lit sa réponse, en appelle un autre si besoin...
                  -> SYNTHÈSE finale

Plus souple que le router (plusieurs agents, dans l'ordre qu'il choisit),
mais plus d'appels au LLM : plus lent et plus cher.

Lancer (depuis le dossier code/) :  python lab2_orchestration/solution/orchestrateur_supervisor.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.agent import Agent
from common.llm import MODELE, nouvelle_demande, resume_couts
from agents_secretariat import agent_absences, agent_horaires, agent_reglement

# TODO 5 : transformer chaque agent en outil pour le superviseur (méthode comme_outil)
OUTILS_SUPERVISEUR = [
    agent_horaires.comme_outil(
        "demander_agent_horaires", "Questions sur les cours : jour, heure, local, professeur."),
    agent_reglement.comme_outil(
        "demander_agent_reglement", "Questions sur le règlement des études (absences, retards, examens, plagiat, IA)."),
    agent_absences.comme_outil(
        "demander_agent_absences", "Absences d'un étudiant précis, à partir de son matricule."),
]

# TODO 6 : les instructions du superviseur
PROMPT_SUPERVISEUR = """Tu es le superviseur du secrétariat de la Haute École de la Citadelle.
Tu ne sais rien toi-même : tu délègues aux agents spécialisés (tes outils).
- demander_agent_absences : le SEUL qui connaît les absences d'un étudiant (donne-lui le matricule)
- demander_agent_reglement : connaît le règlement, mais pas les étudiants
- demander_agent_horaires : connaît les cours (jour, heure, local), mais pas les étudiants
Méthode :
1. Découpe la demande en sous-questions.
2. Appelle les agents utiles, un à la fois. Chaque agent ne voit QUE le message que tu lui écris :
   mets-y toutes les informations utiles (matricule, nom du cours, nombre d'absences...).
3. Quand tu as toutes les informations, écris une synthèse claire et brève en français."""

superviseur = Agent(
    nom="Superviseur",
    instructions=PROMPT_SUPERVISEUR,
    outils=OUTILS_SUPERVISEUR,
    max_iterations=8,
)

if __name__ == "__main__":
    traces.titre(f"Lab 2 : orchestrateur SUPERVISOR (modèle : {MODELE})")
    demande = ("L'étudiante E24003 a-t-elle trop d'absences pour passer ses examens selon le règlement ? "
               "Et quand a lieu le cours concerné ?")
    nouvelle_demande()
    traces.encadre(superviseur.run(demande), "Synthèse du superviseur", "magenta")
    resume_couts()
