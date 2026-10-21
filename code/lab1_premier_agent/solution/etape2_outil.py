"""
LAB 1 — ÉTAPE 2 (≈ 25 min) : donner un OUTIL au modèle           [SOLUTION]

Le modèle ne peut pas lire nos fichiers. On lui décrit un outil (infos_cours) :
s'il en a besoin, il ne répond pas mais DEMANDE l'appel (tool_call).
C'est notre code qui exécute la fonction, puis renvoie le résultat au modèle.

    question -> modèle -> "appelle infos_cours(nom=...)" -> notre code exécute
             -> résultat renvoyé au modèle -> réponse finale

Lancer (depuis le dossier code/) :  python lab1_premier_agent/solution/etape2_outil.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, message_assistant
from lab1_premier_agent.outils_secretariat import infos_cours

PROMPT_SYSTEME = """Tu es l'assistant du secrétariat de la Haute École de la Citadelle.
Tu réponds en français, brièvement. Pour toute question sur un cours, utilise l'outil infos_cours.
N'invente jamais d'information."""

# TODO 1 : décrire l'outil au modèle (nom, description, paramètres au format JSON Schema)
SCHEMA_INFOS_COURS = {
    "type": "function",
    "function": {
        "name": "infos_cours",
        "description": "Donne les informations d'un cours : professeur, local, jour et heures.",
        "parameters": {
            "type": "object",
            "properties": {
                "nom": {"type": "string", "description": "Nom du cours ou une partie du nom"},
            },
            "required": ["nom"],
        },
    },
}


def repondre(question):
    messages = [
        {"role": "system", "content": PROMPT_SYSTEME},
        {"role": "user", "content": question},
    ]
    traces.tracer("Étudiant", "DEMANDE", question)

    # 1er appel : on envoie la question ET la liste des outils disponibles
    reponse = chat(messages, tools=[SCHEMA_INFOS_COURS], agent="Secrétariat")

    if not reponse.tool_calls:
        traces.tracer("Secrétariat", "INFO", "Le modèle a répondu sans utiliser d'outil.")
        return reponse.content

    # TODO 2 : exécuter chaque outil demandé et renvoyer son résultat au modèle
    messages.append(message_assistant(reponse))  # on garde la demande d'outil dans l'historique
    for appel in reponse.tool_calls:
        arguments = json.loads(appel.function.arguments)        # texte JSON -> dictionnaire
        traces.action("Secrétariat", appel.function.name, arguments)
        resultat = infos_cours(**arguments)                      # ex. infos_cours(nom="bases de données")
        traces.observation("Secrétariat", resultat)
        messages.append({
            "role": "tool",
            "tool_call_id": appel.id,           # relie le résultat à la demande
            "name": appel.function.name,        # nom de l'outil (exigé par certains fournisseurs, dont Mistral)
            "content": json.dumps(resultat, ensure_ascii=False),
        })

    # TODO 3 : 2e appel au modèle, qui a maintenant le résultat de l'outil
    reponse_finale = chat(messages, tools=[SCHEMA_INFOS_COURS], agent="Secrétariat")
    return reponse_finale.content


if __name__ == "__main__":
    traces.titre(f"Étape 2 : un outil (modèle : {MODELE})")
    traces.encadre(repondre("Dans quel local a lieu le cours de Bases de données, et qui le donne ?"),
                   "Réponse", "magenta")
