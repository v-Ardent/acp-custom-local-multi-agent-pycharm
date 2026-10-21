"""
Affichage des traces d'un agent dans le terminal (avec la bibliothèque rich).

Chaque ligne affichée ressemble à :

    Agent météo  [ACTION]  meteo(ville='Namur', jour='samedi')

- le nom de l'agent a toujours la même couleur (une couleur par agent) ;
- le type d'événement a sa propre couleur : [PENSÉE], [ACTION], [OBSERVATION], [RÉPONSE]...

On peut aussi "écouter" les traces depuis un autre programme (ex. l'interface
Streamlit du template de projet) avec definir_ecouteur(fonction).
"""

import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Couleur de chaque type d'événement
COULEURS_TYPES = {
    "DEMANDE": "bold white",
    "PENSÉE": "yellow",
    "ACTION": "cyan",
    "OBSERVATION": "green",
    "RÉPONSE": "bold magenta",
    "LLM": "dim",          # un appel au modèle (tokens consommés)
    "HUMAIN": "bold red",  # intervention humaine (validation, refus...)
    "INFO": "blue",
}

# Palette de couleurs attribuées aux agents, dans l'ordre d'apparition
PALETTE_AGENTS = ["bright_blue", "bright_magenta", "orange1", "bright_cyan",
                  "bright_green", "deep_pink2", "gold1", "medium_purple1"]
_couleurs_agents = {}

# Fonction appelée à chaque événement (None = personne n'écoute)
_ecouteur = None


def definir_ecouteur(fonction):
    """Enregistre une fonction appelée à chaque trace : fonction(evenement: dict)."""
    global _ecouteur
    _ecouteur = fonction


def couleur_agent(agent):
    """Donne toujours la même couleur au même agent."""
    if agent not in _couleurs_agents:
        index = len(_couleurs_agents) % len(PALETTE_AGENTS)
        _couleurs_agents[agent] = PALETTE_AGENTS[index]
    return _couleurs_agents[agent]


def raccourcir(texte, longueur_max=400):
    """Coupe les textes trop longs pour garder un affichage lisible."""
    texte = str(texte).strip()
    if len(texte) > longueur_max:
        return texte[:longueur_max] + " [...]"
    return texte


def tracer(agent, type_evenement, texte, **details):
    """Affiche une ligne de trace et prévient l'écouteur éventuel."""
    ligne = Text()
    ligne.append(f"{agent:<18}", style=f"bold {couleur_agent(agent)}")
    ligne.append(f" [{type_evenement}] ", style=COULEURS_TYPES.get(type_evenement, "white"))
    # Text.append n'interprète pas les crochets : pas de risque avec du JSON
    style_texte = "dim" if type_evenement == "LLM" else ""
    # Les résultats d'outils peuvent être très longs : on les coupe à l'affichage
    ligne.append(raccourcir(texte) if type_evenement == "OBSERVATION" else str(texte), style=style_texte)
    console.print(ligne)

    if _ecouteur is not None:
        _ecouteur({
            "heure": datetime.now().strftime("%H:%M:%S"),
            "agent": agent,
            "type": type_evenement,
            "texte": str(texte),
            **details,
        })


# --- Raccourcis pour les événements les plus fréquents -----------------------

def pensee(agent, texte):
    tracer(agent, "PENSÉE", texte)


def action(agent, nom_outil, arguments):
    args = ", ".join(f"{cle}={valeur!r}" for cle, valeur in arguments.items())
    tracer(agent, "ACTION", f"{nom_outil}({args})", outil=nom_outil)


def observation(agent, resultat):
    if not isinstance(resultat, str):
        resultat = json.dumps(resultat, ensure_ascii=False)
    tracer(agent, "OBSERVATION", resultat)


def reponse(agent, texte):
    tracer(agent, "RÉPONSE", texte)


def titre(texte):
    """Grande ligne de séparation avec un titre."""
    console.rule(f"[bold]{texte}")


def encadre(texte, titre_cadre="", couleur="white"):
    """Affiche un texte (souvent la réponse finale) dans un cadre."""
    console.print(Panel(Text(str(texte)), title=titre_cadre, border_style=couleur))
