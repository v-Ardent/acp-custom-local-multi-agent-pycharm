"""
LAB 1 — ÉTAPE 3 (≈ 25 min) : la boucle ReAct

Un agent = un LLM + des outils + une BOUCLE :
    tant que le modèle demande des outils (et qu'on n'a pas dépassé la limite) :
        [PENSÉE]      le modèle explique ce qu'il va faire (s'il l'écrit)
        [ACTION]      il demande un outil
        [OBSERVATION] on exécute l'outil et on lui renvoie le résultat
    sinon :
        [RÉPONSE]     c'est la réponse finale

Nouveautés par rapport à l'étape 2 :
    - 4 outils (tous dans outils_secretariat.py) : TOUS_LES_SCHEMAS et executer_outil(nom, arguments)
    - des raccourcis dans common/llm.py : lire_arguments(appel), message_assistant(reponse),
      message_outil(appel, resultat)   (ils font ce que vous avez écrit à la main à l'étape 2)

Complétez les TODO 1 à 4, puis lancez (depuis le dossier code/) :
    python lab1_premier_agent/enonce/etape3_boucle_react.py
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
        # TODO 1 : appelez le modèle avec la conversation ET tous les outils (TOUS_LES_SCHEMAS).
        #          N'oubliez pas agent=AGENT (pour les traces et le calcul des coûts).
        raise NotImplementedError("TODO 1 : appeler chat() avec les outils.")

        # TODO 2 : si le modèle ne demande aucun outil (reponse.tool_calls est vide),
        #          c'est sa réponse finale : affichez-la avec traces.reponse(AGENT, ...) et renvoyez-la.
        raise NotImplementedError("TODO 2 : détecter la réponse finale.")

        # (fourni) s'il a écrit un raisonnement avant ses appels d'outils, on l'affiche
        if reponse.content:
            traces.pensee(AGENT, reponse.content)

        # TODO 3 : sinon, exécutez les outils demandés :
        #   a) ajoutez la demande du modèle à l'historique : message_assistant(reponse)
        #   b) pour chaque appel de reponse.tool_calls :
        #        arguments = lire_arguments(appel)
        #        traces.action(AGENT, appel.function.name, arguments)
        #        resultat = executer_outil(appel.function.name, arguments)
        #        traces.observation(AGENT, resultat)
        #        ajoutez message_outil(appel, resultat) à l'historique
        #   ... puis la boucle recommence : le modèle voit les résultats et décide de la suite.
        raise NotImplementedError("TODO 3 : exécuter les outils et renvoyer leurs résultats.")

    # TODO 4 : on sort de la boucle sans réponse finale -> limite atteinte.
    #          Affichez une trace "INFO" et renvoyez un message d'excuse à l'utilisateur.
    raise NotImplementedError("TODO 4 : gérer la limite d'itérations.")


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

# ---------------------------------------------------------------------------
# À OBSERVER / À ESSAYER quand ça marche :
#   a) Pour la 2e question, qui a décidé d'appeler DEUX outils, et dans quel ordre ?
#   b) Mettez MAX_ITERATIONS = 1 : que se passe-t-il ?
#   c) Ajoutez votre propre question qui demande 3 outils. L'agent s'en sort-il ?
#   d) Regardez les tokens envoyés à chaque appel (lignes [LLM]) : pourquoi augmentent-ils ?
# ---------------------------------------------------------------------------
