"""
LAB 2 — Orchestration, pattern ROUTER

    demande -> Routeur (1 appel LLM : "quelle catégorie ?") -> UN SEUL agent -> réponse

Simple, rapide et peu coûteux. Mais si la demande concerne plusieurs agents,
un seul sera appelé : la réponse sera incomplète (voir la dernière demande de test).

Complétez d'abord agents_secretariat.py (TODO 1), puis les TODO 2 à 4 ci-dessous.
Lancer (depuis le dossier code/) :  python lab2_orchestration/enonce/orchestrateur_router.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, nouvelle_demande, resume_couts
from agents_secretariat import agent_absences, agent_horaires, agent_reglement

# Catégorie -> agent spécialisé
AGENTS = {
    "horaires": agent_horaires,
    "reglement": agent_reglement,
    "absences": agent_absences,
}

# TODO 2 : écrivez le prompt du routeur.
#   - Listez les 3 catégories (horaires, reglement, absences) et ce que chacune couvre.
#   - Imposez un format de réponse STRICT : un seul mot, le nom de la catégorie.
#     (Votre code devra lire cette réponse : plus elle est prévisible, plus c'est simple.)
PROMPT_ROUTEUR = """À compléter"""


def classer(demande):
    """
    TODO 3 : demandez au LLM la catégorie de la demande et renvoyez une clé de AGENTS (ou None).
      a) messages = [system (PROMPT_ROUTEUR), user (demande)]
      b) texte = chat(messages, agent="Routeur", temperature=0).content
      c) le modèle peut répondre "Règlement." ou "horaires\n" : mettez en minuscules,
         remplacez "è" par "e", puis cherchez quelle catégorie de AGENTS apparaît dans le texte.
    """
    raise NotImplementedError("TODO 3 : classer() doit renvoyer 'horaires', 'reglement', 'absences' ou None.")


def router(demande):
    """
    TODO 4 : classez la demande puis transmettez-la à l'agent choisi.
      - catégorie = classer(demande)
      - si None : renvoyez un message d'excuse
      - sinon : tracez le choix (traces.tracer("Routeur", "ACTION", ...))
                et renvoyez AGENTS[categorie].run(demande)
    """
    nouvelle_demande()  # pour mesurer le coût de chaque demande (lab 3)
    traces.tracer("Routeur", "DEMANDE", demande)
    raise NotImplementedError("TODO 4 : transmettre la demande au bon agent.")


if __name__ == "__main__":
    if "À compléter" in PROMPT_ROUTEUR:
        raise NotImplementedError("TODO 2 : écrivez le prompt du routeur (PROMPT_ROUTEUR).")

    traces.titre(f"Lab 2 : orchestrateur ROUTER (modèle : {MODELE})")
    demandes = [
        "Dans quel local a lieu le cours d'Anglais technique ?",
        "Que dit le règlement sur l'utilisation de ChatGPT ?",
        "Combien d'absences a l'étudiant E24002 ?",
        # Demande qui concerne DEUX agents : que va faire le routeur ?
        "L'étudiante E24003 a-t-elle trop d'absences pour passer ses examens selon le règlement ?",
    ]
    for demande in demandes:
        router(demande)  # la réponse de l'agent choisi s'affiche dans les traces ([RÉPONSE])
        print()
    resume_couts()

# À OBSERVER : la dernière demande est-elle bien traitée ? Combien d'appels LLM coûte le routage ?
