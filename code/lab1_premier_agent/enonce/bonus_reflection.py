"""
LAB 1 — BONUS : le pattern Reflection

Après la réponse de l'agent, un 2e appel au LLM joue le rôle de RELECTEUR :
il compare la réponse aux faits renvoyés par les outils et signale les problèmes.
S'il y en a, on renvoie la critique à l'agent, qui CORRIGE sa réponse
(en rappelant des outils si nécessaire). Au plus MAX_CORRECTIONS corrections.

    agent -> réponse -> relecteur -> "VERDICT : OK" ?  oui -> fin
                                        non -> critique renvoyée à l'agent -> nouvelle réponse -> relecteur...

Complétez les TODO 1 à 3, puis lancez (depuis le dossier code/) :
    python lab1_premier_agent/enonce/bonus_reflection.py
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


# TODO 1 : écrivez les consignes du relecteur.
#   - Qu'est-ce qu'il vérifie ? (pas d'invention par rapport aux faits, la question est-elle
#     vraiment traitée pour CETTE personne, l'article du règlement est-il cité...)
#   - Imposez un format de réponse qui se termine par une ligne
#         VERDICT : OK      ou      VERDICT : À CORRIGER
#     (le code teste la présence de "VERDICT : OK", voir est_valide())
PROMPT_CRITIQUE = """À compléter"""


def critiquer(question, observations, reponse):
    """
    TODO 2 : demandez au LLM relecteur son avis sur la réponse et renvoyez-le (texte).
      a) construisez un texte qui contient la QUESTION, les FAITS ("\n".join(observations))
         et la RÉPONSE À VÉRIFIER ;
      b) messages = [message system (PROMPT_CRITIQUE), message user (ce texte)]
         Attention : ne terminez jamais par un message "assistant" (certains fournisseurs, dont Mistral, le refusent) ;
      c) critique = chat(messages, agent="Relecteur", temperature=0).content
      d) affichez-la : traces.tracer("Relecteur", "PENSÉE", critique) et renvoyez-la.
    """
    raise NotImplementedError("TODO 2 : appeler le LLM relecteur.")


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
        # TODO 3 : renvoyez la critique à l'agent pour qu'il corrige sa réponse.
        #   a) ajoutez à `messages` un message "user" qui contient la critique et demande
        #      une réponse corrigée (en l'autorisant à utiliser les outils si des infos manquent) ;
        #   b) la ligne suivante relance l'agent sur la conversation complétée.
        raise NotImplementedError("TODO 3 : renvoyer la critique à l'agent.")
        reponse = agent(messages, observations)
    return reponse


if __name__ == "__main__":
    if "À compléter" in PROMPT_CRITIQUE:
        raise NotImplementedError("TODO 1 : écrivez les consignes du relecteur (PROMPT_CRITIQUE).")
    traces.titre(f"Bonus : Reflection (modèle : {MODELE})")
    question = "Emma (matricule E24003) pourra-t-elle passer l'examen de Réseaux et sécurité ?"
    traces.tracer("Étudiant", "DEMANDE", question)
    traces.encadre(agent_avec_reflection(question), "Réponse finale", "magenta")
    resume_couts()

# ---------------------------------------------------------------------------
# À OBSERVER / À ESSAYER quand ça marche :
#   a) Combien d'appels au modèle en plus coûte la Reflection ? Est-ce rentable ?
#   b) Le relecteur est-il toujours d'accord avec lui-même ? Relancez plusieurs fois.
#   c) Et si le relecteur se trompe ? Qui relit le relecteur ?
# ---------------------------------------------------------------------------
