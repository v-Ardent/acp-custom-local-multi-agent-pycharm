"""
LAB 1 — ÉTAPE 1 (≈ 20 min) : un premier appel au LLM            [SOLUTION]

Objectif : envoyer une conversation (liste de messages) au modèle et lire sa réponse.
    - message "system" : le rôle et les règles de l'assistant
    - message "user"   : la question de l'étudiant

Lancer (depuis le dossier code/) :  python lab1_premier_agent/solution/etape1_appel.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import JOURNAL, MODELE, chat

# TODO 1 : le prompt système = la "fiche de poste" de l'assistant
PROMPT_SYSTEME = """Tu es l'assistant du secrétariat de la Haute École de la Citadelle.
Tu réponds aux étudiants en français, de façon brève, polie et précise.
Si tu ne connais pas une information, dis-le clairement au lieu d'inventer."""


def construire_messages(question):
    """TODO 2 : renvoie la liste des messages à envoyer au modèle."""
    return [
        {"role": "system", "content": PROMPT_SYSTEME},
        {"role": "user", "content": question},
    ]


def demander(question):
    """TODO 3 : envoie la question au modèle et renvoie le texte de sa réponse."""
    messages = construire_messages(question)
    reponse = chat(messages, agent="Secrétariat")
    return reponse.content


if __name__ == "__main__":
    traces.titre(f"Étape 1 : un appel au LLM (modèle : {MODELE})")
    questions = [
        "Bonjour ! Qui es-tu et à quoi sers-tu ?",
        "Dans quel local a lieu le cours de Bases de données ?",  # le modèle ne peut pas le savoir !
    ]
    for question in questions:
        traces.tracer("Étudiant", "DEMANDE", question)
        traces.encadre(demander(question), "Réponse", "magenta")

    dernier_appel = JOURNAL[-1]
    print(f"Dernier appel : {dernier_appel['prompt_tokens']} tokens envoyés, "
          f"{dernier_appel['completion_tokens']} tokens reçus.")
