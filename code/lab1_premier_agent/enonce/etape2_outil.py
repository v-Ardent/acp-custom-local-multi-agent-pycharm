"""
LAB 1 — ÉTAPE 2 (≈ 25 min) : donner un OUTIL au modèle

Le modèle ne peut pas lire nos fichiers. On lui décrit un outil (infos_cours) :
s'il en a besoin, il ne répond pas mais DEMANDE l'appel (tool_call).
C'est NOTRE code qui exécute la fonction, puis renvoie le résultat au modèle.

    question -> modèle -> "appelle infos_cours(nom=...)" -> notre code exécute
             -> résultat renvoyé au modèle -> réponse finale

Complétez les TODO 1 à 3, puis lancez (depuis le dossier code/) :
    python lab1_premier_agent/enonce/etape2_outil.py

La fonction infos_cours(nom) existe déjà dans lab1_premier_agent/outils_secretariat.py.
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

# TODO 1 : décrivez l'outil au modèle. C'est sa "notice" : le modèle ne voit QUE ça,
#          jamais le code Python. Complétez les 3 "À COMPLÉTER".
#   - description de l'outil : à quoi sert-il ? (le modèle s'en sert pour décider de l'appeler)
#   - le paramètre "nom" : son type JSON ("string") et sa description
SCHEMA_INFOS_COURS = {
    "type": "function",
    "function": {
        "name": "infos_cours",
        "description": "À COMPLÉTER",
        "parameters": {
            "type": "object",
            "properties": {
                "nom": {"type": "À COMPLÉTER", "description": "À COMPLÉTER"},
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

    # Pour comprendre : voici ce que le modèle a demandé (décommentez)
    # print(reponse.tool_calls)

    # TODO 2 : exécuter chaque outil demandé et renvoyer son résultat au modèle.
    #   a) Ajoutez la demande du modèle à l'historique : messages.append(message_assistant(reponse))
    #   b) Pour chaque appel dans reponse.tool_calls :
    #        - arguments = json.loads(appel.function.arguments)   (texte JSON -> dictionnaire)
    #        - resultat = infos_cours(**arguments)
    #        - affichez-le : traces.action(...) et traces.observation(...) (voir common/traces.py)
    #        - ajoutez à messages un message de rôle "tool" avec 4 clés :
    #            "role": "tool", "tool_call_id": appel.id, "name": appel.function.name,
    #            "content": le résultat en texte (json.dumps(resultat, ensure_ascii=False))
    raise NotImplementedError("TODO 2 : exécuter l'outil demandé et ajouter son résultat aux messages.")

    # TODO 3 : rappelez le modèle avec les messages complétés et renvoyez le texte de sa réponse.
    raise NotImplementedError("TODO 3 : 2e appel à chat() avec le résultat de l'outil.")


if __name__ == "__main__":
    if "À COMPLÉTER" in json.dumps(SCHEMA_INFOS_COURS, ensure_ascii=False):
        raise NotImplementedError("TODO 1 : complétez la description de l'outil (SCHEMA_INFOS_COURS).")

    traces.titre(f"Étape 2 : un outil (modèle : {MODELE})")
    traces.encadre(repondre("Dans quel local a lieu le cours de Bases de données, et qui le donne ?"),
                   "Réponse", "magenta")

# ---------------------------------------------------------------------------
# À OBSERVER / À ESSAYER quand ça marche :
#   a) Qui exécute infos_cours : le modèle ou votre programme ?
#   b) Posez une question sans rapport ("Raconte une blague") : le modèle appelle-t-il l'outil ?
#   c) Mettez une description d'outil vague ("fait un truc") : que se passe-t-il ?
#   d) Combien d'appels au modèle pour UNE question ? Et combien de tokens ?
# ---------------------------------------------------------------------------
