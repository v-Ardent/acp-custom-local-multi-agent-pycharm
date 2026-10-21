"""
LAB 3 — Mesurer ce que coûte (vraiment) un système d'agents.

Chaque appel au LLM fait via common/llm.py est enregistré dans code/traces.jsonl
(agent, tokens envoyés, tokens reçus, durée, identifiant de la demande).
Ce script relit ce fichier et affiche :
    1. les tokens consommés par agent (qui coûte le plus ?)
    2. le coût de chaque demande utilisateur
    3. une extrapolation : N utilisateurs x M demandes par jour x 30 jours, pour plusieurs modèles

Lancer (depuis le dossier code/) :
    python lab3_couts_securite/mesure_couts.py                  (toutes les traces)
    python lab3_couts_securite/mesure_couts.py --dernieres 3    (les 3 dernières demandes)

Astuce : supprimez traces.jsonl pour repartir de zéro avant de mesurer votre prototype.
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# ============================================================================
#  PARAMÈTRES À MODIFIER
# ============================================================================

# Prix en dollars par MILLION de tokens : (entrée, sortie).
# PRIX INDICATIFS, À VÉRIFIER SUR LE SITE DU FOURNISSEUR : ils changent souvent.
PRIX = {
    "qwen3.8-27b":     (0.80, 4.00),   # Groq, le modèle du labo (1re ligne = prix de référence du tableau)
    "gpt-oss-20b":     (0.075, 0.30),  # Groq
    "mistral-small":   (0.10, 0.30),
    "mistral-medium":  (0.40, 2.00),
    "mistral-large":   (2.00, 6.00),
    "gpt-4o-mini":     (0.15, 0.60),
    "claude-sonnet":   (3.00, 15.00),
    "local-ollama":    (0.00, 0.00),   # gratuit en tokens... mais pas en matériel ni en électricité
}

N_UTILISATEURS = 200        # combien de personnes utilisent le système
REQUETES_PAR_JOUR = 5       # combien de demandes chacune fait par jour
JOURS_PAR_MOIS = 30

# ============================================================================

FICHIER_TRACES = Path(__file__).resolve().parent.parent / "traces.jsonl"
console = Console()


def charger_traces(fichier):
    """Lit traces.jsonl : une ligne JSON par appel au LLM."""
    if not fichier.exists():
        console.print(f"[red]Fichier introuvable : {fichier}[/]\n"
                      "Lancez d'abord un script du labo (ex. demo_bloc1/4_multi_agents.py).")
        sys.exit(1)
    with open(fichier, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def cout(tokens_entree, tokens_sortie, modele):
    prix_entree, prix_sortie = PRIX[modele]
    return (tokens_entree * prix_entree + tokens_sortie * prix_sortie) / 1_000_000


def grouper(appels, cle):
    """Additionne les tokens par agent, par demande... selon `cle`."""
    groupes = {}
    for appel in appels:
        g = groupes.setdefault(appel[cle], {"appels": 0, "in": 0, "out": 0, "duree": 0.0,
                                            "debut": appel["horodatage"]})
        g["appels"] += 1
        g["in"] += appel["prompt_tokens"]
        g["out"] += appel["completion_tokens"]
        g["duree"] += appel["duree_s"]
    return groupes


def main():
    parser = argparse.ArgumentParser(description="Mesure des coûts à partir de traces.jsonl")
    parser.add_argument("--dernieres", type=int, default=None, help="ne garder que les N dernières demandes")
    parser.add_argument("--fichier", type=Path, default=FICHIER_TRACES)
    args = parser.parse_args()

    appels = charger_traces(args.fichier)
    if args.dernieres:
        ordre = list(dict.fromkeys(a["demande"] for a in appels))  # demandes dans l'ordre d'apparition
        gardees = set(ordre[-args.dernieres:])
        appels = [a for a in appels if a["demande"] in gardees]
    if not appels:
        console.print("[red]Aucun appel à analyser.[/]")
        return

    modele_ref = list(PRIX)[0]  # le premier modèle de la table sert de référence

    # --- 1. Par agent ------------------------------------------------------------
    total_tokens = sum(a["prompt_tokens"] + a["completion_tokens"] for a in appels)
    t = Table(title=f"1. Tokens par agent ({len(appels)} appels au LLM)", caption=f"* au prix de {modele_ref}")
    for col in ["Agent", "Appels", "Entrée", "Sortie", "% tokens", "Coût $*"]:
        t.add_column(col, justify="left" if col == "Agent" else "right")
    for agent, g in sorted(grouper(appels, "agent").items(), key=lambda x: -(x[1]["in"] + x[1]["out"])):
        part = 100 * (g["in"] + g["out"]) / max(total_tokens, 1)
        t.add_row(agent, str(g["appels"]), str(g["in"]), str(g["out"]), f"{part:.0f} %",
                  f"{cout(g['in'], g['out'], modele_ref):.5f}")
    console.print(t)

    # --- 2. Par demande utilisateur ------------------------------------------------
    demandes = grouper(appels, "demande")
    t = Table(title="2. Coût par demande utilisateur", caption=f"* au prix de {modele_ref}")
    for col in ["Demande", "Début", "Appels", "Entrée", "Sortie", "Durée s", "Coût $*"]:
        t.add_column(col, justify="left" if col in ("Demande", "Début") else "right")
    for id_demande, g in demandes.items():
        t.add_row(id_demande, g["debut"][5:16].replace("T", " "), str(g["appels"]), str(g["in"]), str(g["out"]),
                  f"{g['duree']:.1f}", f"{cout(g['in'], g['out'], modele_ref):.5f}")
    console.print(t)

    moy_in = sum(g["in"] for g in demandes.values()) / len(demandes)
    moy_out = sum(g["out"] for g in demandes.values()) / len(demandes)
    console.print(f"Moyenne par demande : [bold]{moy_in:.0f}[/] tokens en entrée, "
                  f"[bold]{moy_out:.0f}[/] en sortie ({len(demandes)} demandes analysées).\n")

    # --- 3. Extrapolation ---------------------------------------------------------------
    demandes_par_mois = N_UTILISATEURS * REQUETES_PAR_JOUR * JOURS_PAR_MOIS
    t = Table(title=f"3. Extrapolation : {N_UTILISATEURS} utilisateurs x {REQUETES_PAR_JOUR} demandes/jour "
                    f"x {JOURS_PAR_MOIS} jours = {demandes_par_mois} demandes/mois")
    for col in ["Modèle", "$/M entrée-sortie", "$/demande", "$/jour", "$/mois"]:
        t.add_column(col, justify="left" if col == "Modèle" else "right")
    for modele, (p_in, p_out) in PRIX.items():
        par_demande = cout(moy_in, moy_out, modele)
        prix = " / ".join(f"{x:.2f}" if round(x, 2) == x else f"{x:.3f}" for x in (p_in, p_out))
        t.add_row(modele, prix, f"{par_demande:.5f}",
                  f"{par_demande * N_UTILISATEURS * REQUETES_PAR_JOUR:.2f}",
                  f"{par_demande * demandes_par_mois:.2f}")
    console.print(t)
    console.print("[dim]Prix indicatifs, à vérifier sur le site du fournisseur. "
                  "Les tokens mesurés dépendent du modèle utilisé pendant le test "
                  "(chaque modèle découpe le texte différemment).[/]")


if __name__ == "__main__":
    main()
