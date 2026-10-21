"""
LAB 1 — BONUS : le pattern Reflection                               [SOLUTION]

Après la réponse de l'agent, un 2e appel au LLM joue le rôle de RELECTEUR :
il compare la réponse aux faits renvoyés par les outils et signale les problèmes.
S'il y en a, on renvoie la critique à l'agent, qui CORRIGE sa réponse
(en rappelant des outils si nécessaire). Au plus MAX_CORRECTIONS corrections.

    agent -> réponse -> relecteur -> "VERDICT : OK" ?  oui -> fin
                                        non -> critique renvoyée à l'agent -> nouvelle réponse -> relecteur...

Lancer (depuis le dossier code/) :  python lab1_premier_agent/solution/bonus_reflection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, lire_arguments, message_assistant, message_outil, resume_couts
from lab1_premier_agent.outils_secretariat import TOUS_LES_SCHEMAS, executer_outil

MAX_ITERATIONS = 5
MAX_CORRECTIONS = 2

PROMPT_AGENT = """Tu es l'agent du secrétariat de la Haute École de la Citadelle.
Tu réponds aux questions des étudiants en français, en 2 ou 3 phrases maximum.
Utilise les outils horaire_du_jour, infos_cours, chercher_reglement, absences_etudiant."""


def agent(messages, observations):
    """
    Boucle ReAct (fournie) sur la conversation `messages`.
    Chaque résultat d'outil est aussi ajouté à `observations` (les faits, pour le relecteur).
    """
    for _ in range(MAX_ITERATIONS):
        reponse = chat(messages, tools=TOUS_LES_SCHEMAS, agent="Agent")
        messages.append(message_assistant(reponse))
        if not reponse.tool_calls:
            traces.reponse("Agent", reponse.content)
            return reponse.content
        for appel in reponse.tool_calls:
            arguments = lire_arguments(appel)
            traces.action("Agent", appel.function.name, arguments)
            resultat = executer_outil(appel.function.name, arguments)
            traces.observation("Agent", resultat)
            observations.append(f"{appel.function.name}({arguments}) -> {resultat}")
            messages.append(message_outil(appel, resultat))
    return "Je n'ai pas pu terminer."


# TODO 1 : les consignes du relecteur (critères précis + format de réponse imposé)
PROMPT_CRITIQUE = """Tu es un relecteur exigeant au secrétariat d'une haute école.
On te donne une question d'étudiant, les FAITS obtenus par les outils, et une RÉPONSE.
Réponds exactement dans ce format :
1. Inventions : les informations de la réponse absentes des faits (ou "aucune")
2. Question traitée : la réponse concerne-t-elle précisément la personne ou le cours demandé ? (oui/non + ce qui manque)
3. Article cité : le numéro de l'article du règlement est-il cité ? (oui/non/sans objet)
VERDICT : OK      (si les 3 points sont bons)
VERDICT : À CORRIGER   (sinon)"""


def critiquer(question, observations, reponse):
    """TODO 2 : demande au LLM relecteur son avis sur la réponse."""
    faits = "\n".join(observations) or "(aucun outil n'a été appelé)"
    contenu = f"QUESTION :\n{question}\n\nFAITS :\n{faits}\n\nRÉPONSE À VÉRIFIER :\n{reponse}"
    messages = [
        {"role": "system", "content": PROMPT_CRITIQUE},
        {"role": "user", "content": contenu},  # la réponse est DANS un message user : on ne termine pas par "assistant"
    ]
    critique = chat(messages, agent="Relecteur", temperature=0).content.strip()
    traces.tracer("Relecteur", "PENSÉE", critique)
    return critique


def est_valide(critique):
    """Le relecteur a-t-il écrit 'VERDICT : OK' ?"""
    return "VERDICT : OK" in critique.upper().replace("VERDICT:", "VERDICT :")


def agent_avec_reflection(question):
    messages = [{"role": "system", "content": PROMPT_AGENT}, {"role": "user", "content": question}]
    observations = []
    reponse = agent(messages, observations)

    for tour in range(1, MAX_CORRECTIONS + 1):
        critique = critiquer(question, observations, reponse)
        if est_valide(critique):
            traces.tracer("Relecteur", "INFO", "Réponse validée.")
            break
        # TODO 3 : renvoyer la critique à l'agent pour qu'il corrige (il peut rappeler des outils)
        traces.tracer("Relecteur", "INFO", f"Correction n°{tour} demandée à l'agent.")
        messages.append({"role": "user", "content":
                         f"Un relecteur a relu ta réponse et signale ceci :\n{critique}\n"
                         "Corrige ta réponse. Si des informations manquent, utilise les outils."})
        reponse = agent(messages, observations)
    return reponse


if __name__ == "__main__":
    traces.titre(f"Bonus : Reflection (modèle : {MODELE})")
    question = "Emma (matricule E24003) pourra-t-elle passer l'examen de Réseaux et sécurité ?"
    traces.tracer("Étudiant", "DEMANDE", question)
    traces.encadre(agent_avec_reflection(question), "Réponse finale", "magenta")
    resume_couts()
