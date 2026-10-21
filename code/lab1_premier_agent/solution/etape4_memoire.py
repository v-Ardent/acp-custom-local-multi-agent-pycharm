"""
LAB 1 — ÉTAPE 4 (≈ 25 min) : la mémoire de conversation            [SOLUTION]

Le modèle n'a AUCUNE mémoire : à chaque appel, il ne voit que les messages qu'on lui envoie.
Pour qu'il se souvienne, on garde l'historique et on le renvoie à chaque fois.
Conséquence : plus la conversation est longue, plus chaque appel coûte de tokens.

Commandes : /historique (voir la mémoire), /reset (l'effacer), /quitter

Lancer (depuis le dossier code/) :  python lab1_premier_agent/solution/etape4_memoire.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import JOURNAL, MODELE, chat, lire_arguments, message_assistant, message_outil, resume_couts
from lab1_premier_agent.outils_secretariat import TOUS_LES_SCHEMAS, executer_outil

AGENT = "Secrétariat"
MAX_ITERATIONS = 5

PROMPT_SYSTEME = """Tu es l'agent du secrétariat de la Haute École de la Citadelle.
Tu réponds aux questions des étudiants en français, brièvement.
Outils : horaire_du_jour, infos_cours, chercher_reglement, absences_etudiant.
Base-toi uniquement sur les résultats des outils et sur la conversation."""


def tour_agent(historique):
    """
    Boucle ReAct de l'étape 3 (fournie), mais sur un historique PARTAGÉ :
    les demandes d'outils, les résultats et la réponse finale y sont ajoutés.
    """
    for _ in range(MAX_ITERATIONS):
        reponse = chat(historique, tools=TOUS_LES_SCHEMAS, agent=AGENT)
        historique.append(message_assistant(reponse))
        if not reponse.tool_calls:
            return reponse.content
        for appel in reponse.tool_calls:
            arguments = lire_arguments(appel)
            traces.action(AGENT, appel.function.name, arguments)
            resultat = executer_outil(appel.function.name, arguments)
            traces.observation(AGENT, resultat)
            historique.append(message_outil(appel, resultat))
    return "Désolé, je n'ai pas pu terminer : trop d'étapes nécessaires."


def nouvel_historique():
    """TODO 1 : une conversation neuve ne contient que le message système."""
    return [{"role": "system", "content": PROMPT_SYSTEME}]


def afficher_historique(historique):
    """TODO 3 : affiche chaque message de la mémoire (rôle + début du contenu)."""
    for numero, message in enumerate(historique):
        contenu = message.get("content") or ""
        if message.get("tool_calls"):
            contenu = "demande d'outil : " + ", ".join(a["function"]["name"] for a in message["tool_calls"])
        print(f"{numero:>2}. {message['role']:<9} | {traces.raccourcir(contenu.replace(chr(10), ' '), 90)}")
    print(f"=> {len(historique)} messages renvoyés au modèle à chaque appel.")


def main():
    traces.titre(f"Étape 4 : agent avec mémoire (modèle : {MODELE})")
    print("Posez vos questions. Commandes : /historique, /reset, /quitter")
    historique = nouvel_historique()

    while True:
        try:
            question = input("\nVous > ").strip()
        except EOFError:  # fin de l'entrée (Ctrl+D ou texte envoyé par un pipe)
            break
        if not question:
            continue
        if question == "/quitter":
            break
        # TODO 2 : la commande /reset efface la mémoire
        if question == "/reset":
            historique = nouvel_historique()
            print("Mémoire effacée.")
            continue
        if question == "/historique":
            afficher_historique(historique)
            continue

        # TODO 4 : ajouter la question à l'historique, faire tourner l'agent, afficher la réponse
        historique.append({"role": "user", "content": question})
        reponse = tour_agent(historique)
        traces.encadre(reponse, "Agent", "magenta")
        print(f"(mémoire : {len(historique)} messages, dernier appel : "
              f"{JOURNAL[-1]['prompt_tokens']} tokens envoyés)")

    resume_couts()


if __name__ == "__main__":
    main()
