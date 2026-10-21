"""
DÉMO 3/4 — Un agent : le LLM + plusieurs outils + une BOUCLE (pattern ReAct).

À chaque tour de boucle :
  PENSÉE      : le modèle décide quoi faire (parfois il l'écrit)
  ACTION      : il demande un outil (météo, activités, budget)
  OBSERVATION : notre code exécute l'outil et lui renvoie le résultat
... et on recommence jusqu'à ce qu'il donne une RÉPONSE (ou qu'on atteigne la limite).

C'est le modèle qui choisit l'ordre des outils : on ne l'a pas programmé.

Lancer (depuis le dossier code/) :  python demo_bloc1/3_agent_boucle.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, lire_arguments, message_assistant, message_outil, resume_couts
from outils_sortie import TOUS_LES_OUTILS

MAX_ITERATIONS = 8   # garde-fou : sans lui, un agent peut boucler (et coûter) indéfiniment
AGENT = "Agent sorties"

DEMANDE = ("Organise une sortie de classe à Namur ce samedi pour 22 étudiants, "
           "avec un budget de 15 euros maximum par personne. Adapte l'activité à la météo "
           "et donne-moi le coût total.")

INSTRUCTIONS = """Tu es un agent qui organise des sorties de classe.
Méthode :
1. Vérifie la météo avec l'outil meteo.
2. Cherche les activités adaptées avec chercher_activites.
3. Calcule le budget avec calculer_budget (ne calcule jamais de tête).
4. Réponds en français : activité choisie, pourquoi, météo, coût total.
Avant chaque appel d'outil, écris en une phrase ce que tu vas faire et pourquoi.
N'invente aucune information : utilise uniquement les résultats des outils."""

# Dictionnaire nom de l'outil -> fonction Python, et liste des schémas pour le modèle
FONCTIONS = {schema["function"]["name"]: fonction for fonction, schema in TOUS_LES_OUTILS}
SCHEMAS = [schema for _, schema in TOUS_LES_OUTILS]

traces.titre(f"Démo 3 : un agent qui boucle (modèle : {MODELE})")
messages = [
    {"role": "system", "content": INSTRUCTIONS},
    {"role": "user", "content": DEMANDE},
]
traces.tracer("Utilisateur", "DEMANDE", DEMANDE)

for iteration in range(1, MAX_ITERATIONS + 1):
    traces.console.print(f"[dim]--- itération {iteration}/{MAX_ITERATIONS} ---[/]")
    reponse = chat(messages, tools=SCHEMAS, agent=AGENT)

    # Plus d'outil demandé : l'agent a fini
    if not reponse.tool_calls:
        traces.reponse(AGENT, "(voir ci-dessous)")
        traces.encadre(reponse.content, "Proposition de sortie", "magenta")
        break

    if reponse.content:
        traces.pensee(AGENT, reponse.content)

    messages.append(message_assistant(reponse))
    for appel in reponse.tool_calls:
        nom, arguments = appel.function.name, lire_arguments(appel)
        traces.action(AGENT, nom, arguments)
        try:
            resultat = FONCTIONS[nom](**arguments)
        except Exception as erreur:          # outil inconnu, mauvais arguments...
            resultat = f"Erreur : {erreur}"  # on le dit au modèle, il peut se corriger
        traces.observation(AGENT, resultat)
        messages.append(message_outil(appel, resultat))
else:
    traces.tracer(AGENT, "INFO", f"Arrêt : limite de {MAX_ITERATIONS} itérations atteinte.")

resume_couts()
