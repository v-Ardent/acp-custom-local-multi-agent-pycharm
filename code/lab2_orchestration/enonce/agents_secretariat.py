"""
Les 3 agents SPÉCIALISÉS du secrétariat, construits avec la classe Agent (common/agent.py)
et les outils du lab 1 (lab1_premier_agent/outils_secretariat.py).

Chaque agent n'a que les outils de sa spécialité : un prompt plus court,
moins de risques de se tromper d'outil, et des responsabilités claires.

Lisez d'abord common/agent.py : la classe Agent contient la boucle ReAct du lab 1.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/ et lab1
from common.agent import Agent
from lab1_premier_agent.outils_secretariat import (
    SCHEMA_ABSENCES_ETUDIANT, SCHEMA_CHERCHER_REGLEMENT, SCHEMA_HORAIRE_DU_JOUR, SCHEMA_INFOS_COURS,
    absences_etudiant, chercher_reglement, horaire_du_jour, infos_cours)

# Exemple (fourni) : l'agent horaires
agent_horaires = Agent(
    nom="Agent horaires",
    instructions="Tu es l'agent des horaires de la Haute École de la Citadelle. "
                 "Tu réponds aux questions sur les cours : jour, heure, local, professeur. "
                 "Utilise tes outils, n'invente rien. Réponds brièvement en français.",
    outils=[(horaire_du_jour, SCHEMA_HORAIRE_DU_JOUR), (infos_cours, SCHEMA_INFOS_COURS)],
)

# TODO 1 : sur le modèle de agent_horaires, créez :
#   - agent_reglement : répond aux questions sur le règlement (outil : chercher_reglement).
#                       Demandez-lui de citer le numéro de l'article.
#   - agent_absences  : donne les absences d'un étudiant à partir de son matricule
#                       (outil : absences_etudiant). Il donne les faits, sans juger.
agent_reglement = None
agent_absences = None

if agent_reglement is None or agent_absences is None:
    raise NotImplementedError("TODO 1 : créez agent_reglement et agent_absences dans agents_secretariat.py.")
