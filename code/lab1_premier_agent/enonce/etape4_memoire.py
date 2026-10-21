"""
LAB 1 — ÉTAPE 4 (≈ 25 min) : la mémoire de conversation

Le modèle n'a AUCUNE mémoire : à chaque appel, il ne voit que les messages qu'on lui envoie.
Pour qu'il se souvienne, on garde l'historique et on le renvoie à chaque fois.
Conséquence : plus la conversation est longue, plus chaque appel coûte de tokens.

On construit un petit "chat" dans le terminal (une REPL) avec 3 commandes :
    /historique  -> afficher la mémoire
    /reset       -> l'effacer
    /quitter

Complétez les TODO 1 à 4, puis lancez (depuis le dossier code/) :
    python lab1_premier_agent/enonce/etape4_memoire.py
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
    (FOURNI) Boucle ReAct de l'étape 3, mais sur un historique PARTAGÉ :
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
    """TODO 1 : renvoyez une conversation neuve : une liste qui ne contient que le message système."""
    raise NotImplementedError("TODO 1 : nouvel_historique() doit renvoyer [message system].")


def afficher_historique(historique):
    """
    TODO 3 : affichez chaque message de la mémoire, une ligne par message :
        numéro, rôle (system/user/assistant/tool) et le début du contenu.
    Astuces : enumerate(historique), message.get("content") or "",
              traces.raccourcir(texte, 90) pour couper les textes longs.
    Bonus : pour un message assistant qui demande des outils (message.get("tool_calls")),
            affichez le nom des outils demandés.
    Terminez par le nombre total de messages.
    """
    raise NotImplementedError("TODO 3 : afficher le contenu de l'historique.")


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
        if question == "/reset":
            # TODO 2 : effacez la mémoire (repartez d'un nouvel historique) et affichez "Mémoire effacée."
            raise NotImplementedError("TODO 2 : commande /reset.")
        if question == "/historique":
            afficher_historique(historique)
            continue

        # TODO 4 : a) ajoutez la question à l'historique (message "user")
        #          b) reponse = tour_agent(historique)
        #          c) affichez la réponse : traces.encadre(reponse, "Agent", "magenta")
        #          d) affichez la taille de la mémoire (len(historique)) et les tokens envoyés
        #             lors du dernier appel : JOURNAL[-1]["prompt_tokens"]
        raise NotImplementedError("TODO 4 : envoyer la question à l'agent avec la mémoire.")

    resume_couts()


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# À ESSAYER quand ça marche :
#   1) "Quels cours ai-je le lundi ?"  puis  "Et qui donne le deuxième ?"
#      -> l'agent comprend "le deuxième" grâce à la mémoire.
#   2) /historique : combien de messages ? Lesquels n'avez-vous pas tapés vous-même ?
#   3) /reset puis "Et qui donne le deuxième ?" -> que répond-il ?
#   4) Après 10 questions, combien de tokens envoie-t-on à chaque appel ?
#      Proposez une stratégie pour limiter cette croissance (et écrivez-la si vous avez le temps).
# ---------------------------------------------------------------------------
