"""
Les 3 agents SPÉCIALISÉS du secrétariat, construits avec la classe Agent (common/agent.py)
et les outils du lab 1 (lab1_premier_agent/outils_secretariat.py).        [SOLUTION]

Chaque agent n'a que les outils de sa spécialité : un prompt plus court,
moins de risques de se tromper d'outil, et des responsabilités claires.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/ et lab1
from common.agent import Agent
from lab1_premier_agent.outils_secretariat import (
    SCHEMA_ABSENCES_ETUDIANT, SCHEMA_CHERCHER_REGLEMENT, SCHEMA_HORAIRE_DU_JOUR, SCHEMA_INFOS_COURS,
    absences_etudiant, chercher_reglement, horaire_du_jour, infos_cours)

# Exemple : l'agent horaires
agent_horaires = Agent(
    nom="Agent horaires",
    instructions="Tu es l'agent des horaires de la Haute École de la Citadelle. "
                 "Tu réponds aux questions sur les cours : jour, heure, local, professeur. "
                 "Utilise tes outils, n'invente rien. Réponds brièvement en français.",
    outils=[(horaire_du_jour, SCHEMA_HORAIRE_DU_JOUR), (infos_cours, SCHEMA_INFOS_COURS)],
)

# TODO 1 : l'agent règlement
agent_reglement = Agent(
    nom="Agent règlement",
    instructions="Tu es l'agent du règlement des études de la Haute École de la Citadelle. "
                 "Tu réponds aux questions sur les règles (absences, retards, examens, plagiat, IA) "
                 "en cherchant dans le règlement avec ton outil. Cite toujours le numéro de l'article. "
                 "Réponds brièvement en français.",
    outils=[(chercher_reglement, SCHEMA_CHERCHER_REGLEMENT)],
)

# TODO 1 : l'agent absences
agent_absences = Agent(
    nom="Agent absences",
    instructions="Tu es l'agent des absences de la Haute École de la Citadelle. "
                 "À partir d'un matricule (ex. E24003), tu donnes les absences d'un étudiant : "
                 "nombre, cours concernés, justifiées ou non. Tu ne juges pas : tu donnes les faits. "
                 "Réponds brièvement en français.",
    outils=[(absences_etudiant, SCHEMA_ABSENCES_ETUDIANT)],
)
