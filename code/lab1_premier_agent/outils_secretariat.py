"""
Les outils de l'agent du secrétariat (Haute École de la Citadelle, école fictive).

Ce fichier est FOURNI : vous n'avez pas à le modifier (mais lisez-le !).

    horaire_du_jour(jour)          -> les cours d'un jour ("lundi", "demain"...)
    infos_cours(nom)               -> prof, local, jour et heure d'un cours
    chercher_reglement(mot_cle)    -> les articles du règlement qui contiennent ce mot
    absences_etudiant(matricule)   -> les absences d'un étudiant (ex. "E24003")

Pour chaque outil : la fonction Python + son SCHEMA (la notice lue par le modèle).
En bas du fichier : TOUS_LES_SCHEMAS et executer_outil(nom, arguments).
"""

import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common.llm import schema_outil

DATA = Path(__file__).resolve().parent / "data"
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOTS_VIDES = {"l", "d", "le", "la", "les", "de", "des", "du", "un", "une", "et", "ou",
              "en", "au", "aux", "sur", "pour", "par", "que", "qui", "est", "a"}


def _lire_json(nom_fichier):
    with open(DATA / nom_fichier, encoding="utf-8") as fichier:
        return json.load(fichier)


def _normaliser(texte):
    """'Réseaux ' -> 'reseaux' : minuscules, sans accents, sans espaces autour."""
    texte = unicodedata.normalize("NFD", str(texte).strip().lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


# --- Outil 1 -------------------------------------------------------------------

def horaire_du_jour(jour):
    """Renvoie la liste des cours d'un jour de la semaine, triés par heure."""
    jour = _normaliser(jour)
    if jour in ("aujourd'hui", "aujourdhui"):
        jour = JOURS[date.today().weekday()]
    elif jour == "demain":
        jour = JOURS[(date.today() + timedelta(days=1)).weekday()]
    if jour not in JOURS:
        return {"erreur": f"Jour inconnu : '{jour}'. Jours possibles : {JOURS}"}

    cours = [c for c in _lire_json("cours.json") if c["jour"] == jour]
    cours.sort(key=lambda c: c["heure_debut"])
    return {"jour": jour, "cours": cours} if cours else {"jour": jour, "cours": [], "remarque": "aucun cours ce jour-là"}


SCHEMA_HORAIRE_DU_JOUR = schema_outil(
    "horaire_du_jour",
    "Donne l'horaire des cours (nom, prof, local, heures) pour un jour de la semaine.",
    {"jour": {"type": "string", "description": "Jour de la semaine en français (ex. 'lundi'), ou 'aujourd'hui' / 'demain'"}},
)


# --- Outil 2 -------------------------------------------------------------------

def infos_cours(nom):
    """Cherche un cours par son nom (ou une partie du nom)."""
    tous = _lire_json("cours.json")
    trouves = [c for c in tous if _normaliser(nom) in _normaliser(c["nom"])]
    if not trouves:
        return {"erreur": f"Aucun cours ne correspond à '{nom}'.",
                "cours_existants": [c["nom"] for c in tous]}
    return trouves


SCHEMA_INFOS_COURS = schema_outil(
    "infos_cours",
    "Donne les informations d'un cours : professeur, local, jour et heures.",
    {"nom": {"type": "string", "description": "Nom du cours ou une partie du nom (ex. 'bases de données')"}},
)


# --- Outil 3 -------------------------------------------------------------------

def chercher_reglement(mot_cle):
    """Renvoie les articles du règlement qui contiennent le(s) mot(s)-clé(s)."""
    texte = (DATA / "reglement.md").read_text(encoding="utf-8")
    articles = ["## " + bloc.strip() for bloc in texte.split("## ")[1:]]  # un bloc par article

    # Mots recherchés, sans les petits mots ; "absences" trouve aussi "absence"
    mots = [m.rstrip("s") for m in re.findall(r"\w+", _normaliser(mot_cle)) if m not in MOTS_VIDES]

    def score(article):
        """Nombre de mots recherchés présents au début d'un mot de l'article."""
        mots_article = re.findall(r"\w+", _normaliser(article))
        return sum(any(m.startswith(mot) for m in mots_article) for mot in mots)

    trouves = [article for article in sorted(articles, key=score, reverse=True) if score(article) > 0]

    if not trouves:
        titres = [article.splitlines()[0].strip("# ") for article in articles]
        return {"erreur": f"Aucun article ne contient '{mot_cle}'.", "articles_existants": titres}
    return "\n\n".join(trouves[:3])  # au plus 3 articles, pour limiter les tokens


SCHEMA_CHERCHER_REGLEMENT = schema_outil(
    "chercher_reglement",
    "Cherche dans le règlement des études les articles qui parlent d'un sujet "
    "(absences, retards, examens, plagiat, IA...).",
    {"mot_cle": {"type": "string", "description": "Un mot-clé simple, ex. 'absences' ou 'plagiat'"}},
)


# --- Outil 4 -------------------------------------------------------------------

def absences_etudiant(matricule):
    """Renvoie les absences d'un étudiant et un petit résumé par cours."""
    for etudiant in _lire_json("etudiants.json"):
        if etudiant["matricule"].lower() == str(matricule).strip().lower():
            non_justifiees = {}
            for absence in etudiant["absences"]:
                if not absence["justifiee"]:
                    non_justifiees[absence["cours"]] = non_justifiees.get(absence["cours"], 0) + 1
            return {
                "etudiant": f"{etudiant['prenom']} {etudiant['nom']}",
                "matricule": etudiant["matricule"],
                "nombre_absences": len(etudiant["absences"]),
                "non_justifiees_par_cours": non_justifiees,
                "detail": etudiant["absences"],
            }
    return {"erreur": f"Matricule '{matricule}' inconnu. Format attendu : E24001."}


SCHEMA_ABSENCES_ETUDIANT = schema_outil(
    "absences_etudiant",
    "Donne la liste des absences d'un étudiant (justifiées ou non) à partir de son matricule.",
    {"matricule": {"type": "string", "description": "Matricule de l'étudiant, ex. 'E24003'"}},
)


# --- Pour la boucle de l'agent -----------------------------------------------

# Nom de l'outil -> fonction Python
FONCTIONS = {
    "horaire_du_jour": horaire_du_jour,
    "infos_cours": infos_cours,
    "chercher_reglement": chercher_reglement,
    "absences_etudiant": absences_etudiant,
}

TOUS_LES_SCHEMAS = [SCHEMA_HORAIRE_DU_JOUR, SCHEMA_INFOS_COURS,
                    SCHEMA_CHERCHER_REGLEMENT, SCHEMA_ABSENCES_ETUDIANT]


def executer_outil(nom, arguments):
    """Exécute l'outil `nom` avec les `arguments` (dict) et renvoie le résultat en texte."""
    if nom not in FONCTIONS:
        return f"Erreur : l'outil '{nom}' n'existe pas. Outils disponibles : {list(FONCTIONS)}"
    try:
        resultat = FONCTIONS[nom](**arguments)
    except Exception as erreur:  # mauvais arguments, etc. : on prévient le modèle
        return f"Erreur pendant l'exécution de {nom} : {erreur}"
    return resultat if isinstance(resultat, str) else json.dumps(resultat, ensure_ascii=False)
