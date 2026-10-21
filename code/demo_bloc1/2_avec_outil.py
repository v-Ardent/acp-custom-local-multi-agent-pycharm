"""
DÉMO 2/4 — Le même LLM, avec UN outil : la vraie météo (API Open-Meteo).

Déroulé, étape par étape (un seul aller-retour d'outil) :
  1. On envoie la question + la description de l'outil "meteo".
  2. Le modèle ne répond pas : il DEMANDE d'appeler meteo(ville, jour).
  3. C'est NOTRE code qui exécute l'outil (appel HTTP réel) et renvoie le résultat.
  4. On rappelle le modèle avec ce résultat : il rédige la réponse finale.

Lancer (depuis le dossier code/) :  python demo_bloc1/2_avec_outil.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, lire_arguments, message_assistant, message_outil, resume_couts
from outils_sortie import SCHEMA_METEO, meteo

QUESTION = ("J'organise une sortie de classe à Namur ce samedi pour 20 étudiants. "
            "Quel temps fera-t-il samedi à Namur, et quelle activité me conseilles-tu ?")

traces.titre(f"Démo 2 : un LLM + un outil météo (modèle : {MODELE})")
messages = [
    {"role": "system", "content": "Tu es un assistant qui aide un enseignant à organiser des sorties de classe. "
                                  "Utilise l'outil meteo pour connaître la météo, n'invente jamais."},
    {"role": "user", "content": QUESTION},
]
traces.tracer("Utilisateur", "DEMANDE", QUESTION)

# --- Étape 1 : premier appel, avec la liste des outils disponibles -------------
reponse = chat(messages, tools=[SCHEMA_METEO], agent="Assistant")

if not reponse.tool_calls:
    # Cas possible avec un petit modèle : il répond sans utiliser l'outil
    traces.encadre(reponse.content, "Le modèle a répondu SANS appeler l'outil", "red")
    sys.exit()

# --- Étape 2 : le modèle demande un outil -> on l'exécute nous-mêmes -----------
messages.append(message_assistant(reponse))          # on garde sa demande dans l'historique
for appel in reponse.tool_calls:
    arguments = lire_arguments(appel)                 # ex. {"ville": "Namur", "jour": "samedi"}
    traces.action("Assistant", appel.function.name, arguments)
    resultat = meteo(**arguments)                     # VRAI appel à l'API Open-Meteo
    traces.observation("Assistant", resultat)
    messages.append(message_outil(appel, resultat))  # on renvoie le résultat au modèle

# --- Étape 3 : second appel, le modèle a maintenant les faits ------------------
reponse_finale = chat(messages, tools=[SCHEMA_METEO], agent="Assistant")
traces.encadre(reponse_finale.content, "Réponse finale (basée sur la vraie météo)", "magenta")
resume_couts()
