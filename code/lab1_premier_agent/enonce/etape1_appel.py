"""
LAB 1 — ÉTAPE 1 (≈ 20 min) : un premier appel au LLM

Objectif : envoyer une conversation (liste de messages) au modèle et lire sa réponse.
    - message "system" : le rôle et les règles de l'assistant
    - message "user"   : la question de l'étudiant

Complétez les TODO 1 à 3 dans l'ordre, puis lancez (depuis le dossier code/) :
    python lab1_premier_agent/enonce/etape1_appel.py

Aide : la fonction chat() est dans common/llm.py. Elle renvoie un message dont
le texte est dans l'attribut .content
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import JOURNAL, MODELE, chat

# TODO 1 : écrivez le prompt système = la "fiche de poste" de l'assistant.
#   - Qui est-il ? (l'assistant du secrétariat de la Haute École de la Citadelle)
#   - Comment répond-il ? (langue, longueur, ton)
#   - Que fait-il s'il ne sait pas ?
PROMPT_SYSTEME = """À compléter"""


def construire_messages(question):
    """
    TODO 2 : renvoyez la liste des messages à envoyer au modèle.
    Chaque message est un dictionnaire {"role": ..., "content": ...}.
    Il en faut deux : un message "system" (PROMPT_SYSTEME) puis un message "user" (question).
    """
    raise NotImplementedError("TODO 2 : construire_messages() doit renvoyer [message system, message user].")


def demander(question):
    """
    TODO 3 : envoyez la question au modèle et renvoyez le TEXTE de sa réponse.
    Étapes : messages = construire_messages(question)
             reponse = chat(messages, agent="Secrétariat")
             renvoyer reponse.content
    """
    raise NotImplementedError("TODO 3 : demander() doit appeler chat() et renvoyer le texte de la réponse.")


if __name__ == "__main__":
    if "À compléter" in PROMPT_SYSTEME:
        raise NotImplementedError("TODO 1 : écrivez le prompt système (PROMPT_SYSTEME).")

    traces.titre(f"Étape 1 : un appel au LLM (modèle : {MODELE})")
    questions = [
        "Bonjour ! Qui es-tu et à quoi sers-tu ?",
        "Dans quel local a lieu le cours de Bases de données ?",  # le modèle peut-il le savoir ?
    ]
    for question in questions:
        traces.tracer("Étudiant", "DEMANDE", question)
        traces.encadre(demander(question), "Réponse", "magenta")

    dernier_appel = JOURNAL[-1]
    print(f"Dernier appel : {dernier_appel['prompt_tokens']} tokens envoyés, "
          f"{dernier_appel['completion_tokens']} tokens reçus.")

# ---------------------------------------------------------------------------
# À OBSERVER / À ESSAYER quand ça marche :
#   a) La réponse à la 2e question : d'où vient-elle ? Est-elle fiable ?
#   b) Retirez la phrase "si tu ne sais pas, dis-le" du prompt système : que change-t-il ?
#   c) Lancez 2 fois le script : les réponses sont-elles identiques ? Pourquoi ?
#   d) Combien de tokens coûte une question ? Le prompt système est-il compté ?
# ---------------------------------------------------------------------------
