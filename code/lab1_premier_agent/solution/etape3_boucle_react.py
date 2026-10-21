"""
LAB 1 — ÉTAPE 3 (≈ 25 min) : la boucle ReAct                       [SOLUTION]

Un agent = un LLM + des outils + une BOUCLE :
    tant que le modèle demande des outils (et qu'on n'a pas dépassé la limite) :
        [PENSÉE]      le modèle explique ce qu'il va faire (s'il l'écrit)
        [ACTION]      il demande un outil
        [OBSERVATION] on exécute l'outil et on lui renvoie le résultat
    sinon :
        [RÉPONSE]     c'est la réponse finale

Lancer (depuis le dossier code/) :  python lab1_premier_agent/solution/etape3_boucle_react.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, lire_arguments, message_assistant, message_outil, resume_couts
from lab1_premier_agent.outils_secretariat import TOUS_LES_SCHEMAS, executer_outil

AGENT = "Secrétariat"
MAX_ITERATIONS = 5  # garde-fou contre les boucles infinies (et les factures infinies)

PROMPT_SYSTEME = """Tu es l'agent du secrétariat de la Haute École de la Citadelle.
Tu réponds aux questions des étudiants en français, brièvement.
Outils : horaire_du_jour, infos_cours, chercher_reglement, absences_etudiant.
Avant d'appeler un outil, écris en une phrase ce que tu cherches.
Base-toi uniquement sur les résultats des outils ; cite l'article du règlement si tu l'utilises."""


def agent(question):
    """Fait tourner la boucle ReAct et renvoie la réponse finale."""
    messages = [
        {"role": "system", "content": PROMPT_SYSTEME},
        {"role": "user", "content": question},
    ]
    traces.tracer("Étudiant", "DEMANDE", question)

    for iteration in range(1, MAX_ITERATIONS + 1):
        # TODO 1 : appeler le modèle en lui donnant tous les outils
        reponse = chat(messages, tools=TOUS_LES_SCHEMAS, agent=AGENT)

        # TODO 2 : pas d'outil demandé -> c'est la réponse finale
        if not reponse.tool_calls:
            traces.reponse(AGENT, reponse.content)
            return reponse.content

        if reponse.content:
            traces.pensee(AGENT, reponse.content)

        # TODO 3 : exécuter les outils demandés et renvoyer les résultats au modèle
        messages.append(message_assistant(reponse))
        for appel in reponse.tool_calls:
            arguments = lire_arguments(appel)
            traces.action(AGENT, appel.function.name, arguments)
            resultat = executer_outil(appel.function.name, arguments)
            traces.observation(AGENT, resultat)
            messages.append(message_outil(appel, resultat))

    # TODO 4 : la limite est atteinte -> on s'arrête proprement
    traces.tracer(AGENT, "INFO", f"Limite de {MAX_ITERATIONS} itérations atteinte.")
    return "Désolé, je n'ai pas pu terminer : trop d'étapes nécessaires."


if __name__ == "__main__":
    traces.titre(f"Étape 3 : boucle ReAct (modèle : {MODELE})")
    questions = [
        "Quels cours ai-je lundi, et dans quels locaux ?",
        "L'étudiante E24003 risque-t-elle de ne pas pouvoir passer un examen ?",
    ]
    for question in questions:
        agent(question)  # la réponse s'affiche dans les traces ([RÉPONSE])
        print()
    resume_couts()
