"""
Les outils de la démo "Organiser une sortie de classe à Namur samedi".

- meteo(ville, jour)                : VRAIE météo, via l'API gratuite Open-Meteo (sans clé)
- chercher_activites(ville, meteo)  : activités à Namur, lues dans data/activites_namur.json
- calculer_budget(prix_par_personne, nb_personnes, frais_fixes) : un simple calcul

Pour chaque outil, on a :
  1. la fonction Python (ce qui s'exécute vraiment sur notre machine) ;
  2. son SCHEMA (la "notice" envoyée au modèle pour qu'il sache quand et comment l'appeler).
"""

import json
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common.llm import schema_outil

DOSSIER_DATA = Path(__file__).resolve().parent / "data"
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# Codes météo WMO utilisés par Open-Meteo -> description en français
CODES_METEO = {
    0: "ciel dégagé", 1: "plutôt dégagé", 2: "partiellement nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine", 55: "bruine forte",
    61: "pluie faible", 63: "pluie", 65: "pluie forte",
    71: "neige faible", 73: "neige", 75: "neige forte",
    80: "averses faibles", 81: "averses", 82: "averses violentes",
    95: "orage", 96: "orage avec grêle", 99: "orage violent avec grêle",
}


def _normaliser(texte):
    """'Samedi ' -> 'samedi', 'Intérieur' -> 'interieur' (minuscules, sans accents)."""
    texte = unicodedata.normalize("NFD", str(texte).strip().lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def _date_cible(jour):
    """Transforme 'samedi', 'demain', '2026-10-03'... en une date."""
    aujourd_hui = date.today()
    jour = _normaliser(jour)
    if jour in ("aujourd'hui", "aujourdhui", "today"):
        return aujourd_hui
    if jour == "demain":
        return aujourd_hui + timedelta(days=1)
    if jour in JOURS:
        ecart = (JOURS.index(jour) - aujourd_hui.weekday()) % 7
        return aujourd_hui + timedelta(days=ecart)
    return date.fromisoformat(jour)  # lève une erreur si le format est inconnu


# --- Outil 1 : météo réelle --------------------------------------------------

def meteo(ville, jour="samedi"):
    """Prévisions météo réelles pour une ville et un jour (7 jours à l'avance max)."""
    try:
        cible = _date_cible(jour)
    except ValueError:
        return {"erreur": f"Jour '{jour}' non compris. Utilise un jour de la semaine ou AAAA-MM-JJ."}

    try:
        # 1) Géocodage : nom de ville -> latitude / longitude
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": ville, "count": 1, "language": "fr"}, timeout=10).json()
        if not geo.get("results"):
            return {"erreur": f"Ville '{ville}' introuvable."}
        lieu = geo["results"][0]

        # 2) Prévisions journalières
        prevision = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lieu["latitude"], "longitude": lieu["longitude"],
            "daily": "weather_code,temperature_2m_min,temperature_2m_max,precipitation_probability_max",
            "timezone": "Europe/Brussels", "forecast_days": 16,
        }, timeout=10).json()
    except requests.RequestException as erreur:
        return {"erreur": f"API météo injoignable : {erreur}"}

    jours = prevision["daily"]
    if cible.isoformat() not in jours["time"]:
        return {"erreur": f"Pas de prévision disponible pour le {cible.isoformat()}."}
    i = jours["time"].index(cible.isoformat())

    code = jours["weather_code"][i]
    pluie = jours["precipitation_probability_max"][i] or 0
    mauvais_temps = pluie >= 50 or code >= 51
    return {
        "ville": lieu["name"],
        "date": cible.isoformat(),
        "jour": JOURS[cible.weekday()],
        "ciel": CODES_METEO.get(code, f"code météo {code}"),
        "temperature_min": jours["temperature_2m_min"][i],
        "temperature_max": jours["temperature_2m_max"][i],
        "probabilite_pluie_pourcent": pluie,
        "conseil": "prévoir une activité en intérieur" if mauvais_temps else "une activité en extérieur est possible",
    }


SCHEMA_METEO = schema_outil(
    "meteo",
    "Donne la vraie prévision météo (ciel, températures, risque de pluie) pour une ville et un jour.",
    {
        "ville": {"type": "string", "description": "Nom de la ville, ex. 'Namur'"},
        "jour": {"type": "string", "description": "Jour de la semaine ('samedi'), 'demain' ou une date AAAA-MM-JJ"},
    },
)


# --- Outil 2 : activités (petite base locale) --------------------------------

def chercher_activites(ville, meteo):
    """Liste les activités de groupe possibles, filtrées selon la météo."""
    if _normaliser(ville) != "namur":
        return {"erreur": "Cette démo ne connaît que les activités à Namur."}

    with open(DOSSIER_DATA / "activites_namur.json", encoding="utf-8") as fichier:
        activites = json.load(fichier)

    meteo = _normaliser(meteo)
    mauvais_temps = any(mot in meteo for mot in ["pluie", "mauvais", "orage", "averse", "neige", "interieur"])
    if mauvais_temps:
        activites = [a for a in activites if a["type"] == "intérieur"]
    return {"meteo_prise_en_compte": "mauvais temps" if mauvais_temps else "beau temps",
            "activites": activites,
            "remarque": "prix fictifs, pour la démo"}


SCHEMA_CHERCHER_ACTIVITES = schema_outil(
    "chercher_activites",
    "Cherche des activités de groupe dans une ville. Si le temps est mauvais, ne renvoie que des activités en intérieur.",
    {
        "ville": {"type": "string", "description": "Nom de la ville, ex. 'Namur'"},
        "meteo": {"type": "string", "enum": ["beau", "mauvais"],
                  "description": "'beau' ou 'mauvais', selon la prévision météo"},
    },
)


# --- Outil 3 : calcul du budget -----------------------------------------------

def calculer_budget(prix_par_personne, nb_personnes, frais_fixes=0):
    """Calcule le coût total d'une activité (les LLM calculent mal : on leur donne une calculette)."""
    prix_par_personne, nb_personnes, frais_fixes = float(prix_par_personne), int(nb_personnes), float(frais_fixes)
    total = prix_par_personne * nb_personnes + frais_fixes
    return {"total_euros": round(total, 2), "par_personne_euros": round(total / nb_personnes, 2)}


SCHEMA_CALCULER_BUDGET = schema_outil(
    "calculer_budget",
    "Calcule le coût total et le coût par personne d'une activité de groupe.",
    {
        "prix_par_personne": {"type": "number", "description": "Prix de l'activité par personne, en euros"},
        "nb_personnes": {"type": "integer", "description": "Nombre de participants"},
        "frais_fixes": {"type": "number", "description": "Frais fixes éventuels (transport...), en euros"},
    },
    requis=["prix_par_personne", "nb_personnes"],
)


# Tous les outils, sous la forme (fonction, schéma)
TOUS_LES_OUTILS = [
    (meteo, SCHEMA_METEO),
    (chercher_activites, SCHEMA_CHERCHER_ACTIVITES),
    (calculer_budget, SCHEMA_CALCULER_BUDGET),
]
