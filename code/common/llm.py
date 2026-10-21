"""
Accès au modèle de langage (LLM), partagé par tous les scripts du labo.

- La configuration vient du fichier .env (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL).
- On utilise le SDK "openai" car Groq, Ollama (et beaucoup d'autres) parlent
  le même "dialecte" : changer de fournisseur = changer le .env, pas le code.
- Chaque appel est enregistré (tokens, agent, durée) dans JOURNAL (en mémoire)
  et dans le fichier traces.jsonl (utilisé par lab3_couts_securite/mesure_couts.py).

Fonctions principales :
    chat(messages, tools=None, agent="?")  -> message renvoyé par le modèle
    resume_couts(prix_input, prix_output)  -> affiche les tokens et le coût
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
import ollama
from dotenv import load_dotenv
from rich.markup import escape
from rich.table import Table
from common import traces

# --- Configuration ----------------------------------------------------------

RACINE = Path(__file__).resolve().parent.parent      # le dossier code/
load_dotenv(RACINE / ".env")                           # les variables déjà définies gardent la priorité

BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/api/generate")
MODELE = os.getenv("LLM_MODEL", "deepseek-r1:8b")

FICHIER_TRACES = RACINE / "traces.jsonl"
JOURNAL = []                                 # un dictionnaire par appel au modèle
ATTENTES_429 = [2, 5, 10, 20]                # secondes d'attente entre les essais si 429

# Identifiant de la "demande utilisateur" en cours (pour calculer un coût par demande)
demande_en_cours = uuid.uuid4().hex[:8]


class ErreurLLM(Exception):
    """Erreur de configuration ou d'appel au LLM, avec un message clair en français."""


def nouvelle_demande():
    """À appeler au début de chaque nouvelle demande de l'utilisateur."""
    global demande_en_cours
    demande_en_cours = uuid.uuid4().hex[:8]
    return demande_en_cours

# --- Appel au modèle --------------------------------------------------------

def chat(message):
    stream = ollama.chat(
        model="deepseek-r1:8b",
        messages=message,
    )
    return stream


def _enregistrer_usage(reponse, agent, duree):
    """Note les tokens consommés dans JOURNAL et dans traces.jsonl."""
    usage = reponse.usage
    entree = {
        "horodatage": datetime.now().isoformat(timespec="seconds"),
        "demande": demande_en_cours,
        "agent": agent,
        "modele": MODELE,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "duree_s": round(duree, 2),
    }
    JOURNAL.append(entree)
    try:
        with open(FICHIER_TRACES, "a", encoding="utf-8") as fichier:
            fichier.write(json.dumps(entree, ensure_ascii=False) + "\n")
    except OSError:
        pass  # pas grave si le fichier ne peut pas être écrit

    traces.tracer(agent, "LLM",
                  f"appel au modèle : {entree['prompt_tokens']} tokens envoyés, "
                  f"{entree['completion_tokens']} reçus, {entree['duree_s']} s",
                  prompt_tokens=entree["prompt_tokens"],
                  completion_tokens=entree["completion_tokens"])


# --- Petites aides pour construire les messages -----------------------------

def schema_outil(nom, description, proprietes, requis=None):
    """
    Construit la description d'un outil au format attendu par le modèle.
    proprietes : {"ville": {"type": "string", "description": "..."}, ...}
    requis     : liste des paramètres obligatoires (par défaut : tous)
    """
    return {
        "type": "function",
        "function": {
            "name": nom,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": proprietes,
                "required": list(proprietes) if requis is None else requis,
            },
        },
    }


def lire_arguments(appel):
    """Transforme les arguments d'un appel d'outil (texte JSON) en dictionnaire."""
    try:
        arguments = json.loads(appel.function.arguments or "{}")
        return arguments if isinstance(arguments, dict) else {}
    except json.JSONDecodeError:
        return {}


def message_assistant(message):
    """Convertit le message du modèle en dictionnaire à remettre dans l'historique."""
    resultat = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        resultat["tool_calls"] = [
            {"id": appel.id, "type": "function",
             "function": {"name": appel.function.name, "arguments": appel.function.arguments}}
            for appel in message.tool_calls
        ]
    return resultat


def message_outil(appel, resultat):
    """Message qui renvoie au modèle le résultat d'un outil (tool_call_id ET name : certains fournisseurs, dont Mistral, exigent les deux)."""
    if not isinstance(resultat, str):
        resultat = json.dumps(resultat, ensure_ascii=False)
    return {"role": "tool", "tool_call_id": appel.id, "name": appel.function.name, "content": resultat}


# --- Coûts ------------------------------------------------------------------

def resume_couts(prix_input_par_million=0.80, prix_output_par_million=4.00):
    """
    Affiche les tokens consommés depuis le lancement du script, agent par agent,
    et le coût estimé. Prix en dollars par million de tokens (par défaut : prix de
    qwen3.8-27b chez Groq, à vérifier sur le site du fournisseur).
    Renvoie le coût total estimé.
    """
    par_agent = {}
    for entree in JOURNAL:
        stats = par_agent.setdefault(entree["agent"], {"appels": 0, "in": 0, "out": 0})
        stats["appels"] += 1
        stats["in"] += entree["prompt_tokens"]
        stats["out"] += entree["completion_tokens"]

    tableau = Table(title=f"Consommation (modèle : {MODELE})")
    for colonne in ["Agent", "Appels", "Tokens entrée", "Tokens sortie", "Coût estimé ($)"]:
        tableau.add_column(colonne, justify="left" if colonne == "Agent" else "right")

    total = {"appels": 0, "in": 0, "out": 0, "cout": 0.0}
    for agent, stats in par_agent.items():
        cout = (stats["in"] * prix_input_par_million + stats["out"] * prix_output_par_million) / 1_000_000
        tableau.add_row(agent, str(stats["appels"]), str(stats["in"]), str(stats["out"]), f"{cout:.6f}")
        total["appels"] += stats["appels"]
        total["in"] += stats["in"]
        total["out"] += stats["out"]
        total["cout"] += cout
    tableau.add_row("TOTAL", str(total["appels"]), str(total["in"]), str(total["out"]),
                    f"{total['cout']:.6f}", style="bold")
    traces.console.print(tableau)
    return total["cout"]


# --- Messages d'erreur lisibles ----------------------------------------------

def _afficher_erreur(type_erreur, erreur, pile):
    """Remplace la longue pile d'erreur Python par un message clair pour nos erreurs."""
    if isinstance(erreur, ErreurLLM):
        traces.console.print(f"\n[bold red]Problème avec le LLM :[/] {escape(str(erreur))}")
    elif isinstance(erreur, NotImplementedError):
        traces.console.print(f"\n[bold yellow]À compléter :[/] {escape(str(erreur))}")
    elif isinstance(erreur, KeyboardInterrupt):
        traces.console.print("\n[dim]Interrompu.[/]")
    else:
        sys.__excepthook__(type_erreur, erreur, pile)


sys.excepthook = _afficher_erreur
