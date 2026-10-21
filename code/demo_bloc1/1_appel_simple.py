"""
DÉMO 1/4 — Un appel LLM brut.

On pose une question qui demande une information du monde réel (la météo de samedi).
Le modèle n'a AUCUN accès au monde extérieur : il ne connaît ni la date du jour
ni la météo. Il va donc inventer, rester vague ou refuser.
Selon le modèle, il invente une météo précise ou avoue qu'il ne sait pas.
=> Dans les deux cas, c'est la limite d'un LLM seul : il ne fait que prédire du texte.

Lancer (depuis le dossier code/) :  python demo_bloc1/1_appel_simple.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common import traces
from common.llm import MODELE, chat, resume_couts

QUESTION = ("J'organise une sortie de classe à Namur ce samedi pour 20 étudiants. "
            "Quel temps fera-t-il samedi à Namur (température, pluie) ? "
            "Réponds précisément, puis conseille-moi une activité.")

traces.titre(f"Démo 1 : un appel LLM brut (modèle : {MODELE})")

# Une conversation = une liste de messages. Ici : une consigne système + la question.
messages = [
    {"role": "system", "content": "Tu es un assistant qui aide un enseignant à organiser des sorties de classe."},
    {"role": "user", "content": QUESTION},
]
traces.tracer("Utilisateur", "DEMANDE", QUESTION)

# Un seul aller-retour avec le modèle, sans outil
reponse = chat(messages)

traces.encadre(reponse, "Réponse du modèle", "magenta")
# Selon le modèle, il invente une météo précise (hallucination) ou avoue qu'il ne sait pas.
# Dans les deux cas, même limite : il n'a accès qu'à ce qu'il a appris pendant son entraînement.
traces.console.print("[bold red]Question à la classe :[/] d'où vient cette météo ? "
                     "Le modèle connaît-il seulement la date d'aujourd'hui ?\n")
resume_couts()
