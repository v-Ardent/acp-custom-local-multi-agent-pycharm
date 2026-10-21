"""
Interface Streamlit du prototype : demande -> orchestrateur -> agents, avec traces en direct.

Lancer (depuis le dossier code/) :  streamlit run template_projet/app.py
Vous n'avez normalement PAS besoin de modifier ce fichier : branchez vos agents dans mes_agents.py.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from common import llm, traces
from mes_agents import ACTIONS_EN_ATTENTE, creer_superviseur, executer_action

PRIX_ENTREE, PRIX_SORTIE = 0.80, 4.00  # $ par million de tokens (indicatif, qwen3.8-27b chez Groq) : à adapter
COULEURS = ["blue", "green", "orange", "violet", "red", "gray"]  # une couleur par agent
ETIQUETTES = {"DEMANDE": "demande", "PENSÉE": "pensée", "ACTION": "action", "OBSERVATION": "observation",
              "RÉPONSE": "réponse", "LLM": "appel LLM", "HUMAIN": "humain", "INFO": "info"}

st.set_page_config(page_title="Prototype multi-agent", layout="wide")
etat = st.session_state
for cle, valeur in {"traces": [], "tokens_in": 0, "tokens_out": 0, "couleurs": {},
                    "resultat": None, "action": None, "message_action": None}.items():
    etat.setdefault(cle, valeur)


# --- Panneau latéral : compteurs + traces en direct ----------------------------------

def afficher_compteurs():
    cout = (etat.tokens_in * PRIX_ENTREE + etat.tokens_out * PRIX_SORTIE) / 1_000_000
    with zone_compteurs.container():
        col1, col2 = st.columns(2)
        col1.metric("Tokens", f"{etat.tokens_in + etat.tokens_out:,}".replace(",", " "))
        col2.metric("Coût estimé", f"{cout:.4f} $")


def afficher_trace(evt):
    couleur = etat.couleurs.setdefault(evt["agent"], COULEURS[len(etat.couleurs) % len(COULEURS)])
    texte = evt["texte"].replace("\n", " ")
    texte = texte[:200] + " [...]" if len(texte) > 200 else texte
    zone_traces.markdown(f"`{evt['heure']}` :{couleur}[**{evt['agent']}**] "
                         f"· *{ETIQUETTES.get(evt['type'], evt['type'])}* — {texte}")


def ecouteur(evt):
    """Appelée par common/traces.py à CHAQUE événement : c'est ce qui rend le panneau 'en direct'."""
    etat.traces.append(evt)
    if evt["type"] == "LLM":
        etat.tokens_in += evt.get("prompt_tokens", 0)
        etat.tokens_out += evt.get("completion_tokens", 0)
        afficher_compteurs()
    afficher_trace(evt)


with st.sidebar:
    st.header("Traces en direct")
    zone_compteurs = st.empty()
    zone_traces = st.container(height=650)
afficher_compteurs()
for evenement in etat.traces:          # on réaffiche l'historique des traces à chaque rechargement
    afficher_trace(evenement)
traces.definir_ecouteur(ecouteur)


# --- Zone principale ------------------------------------------------------------------

st.title("Prototype multi-agent")
st.caption(f"Modèle : {llm.MODELE} — fournisseur : {llm.BASE_URL}")
probleme = llm.verifier_configuration()
if probleme:
    st.error(probleme)

demande = st.text_area("Votre demande", "Écris un court message de bienvenue pour des étudiants "
                                        "qui visitent Namur, puis propose de l'envoyer à la classe.")
if st.button("Lancer les agents", type="primary", disabled=bool(probleme)) and demande.strip():
    llm.nouvelle_demande()
    ACTIONS_EN_ATTENTE.clear()
    etat.resultat, etat.action, etat.message_action = None, None, None
    with st.spinner("Les agents travaillent... (suivez-les dans le panneau de gauche)"):
        try:
            etat.resultat = creer_superviseur().run(demande)
        except llm.ErreurLLM as erreur:
            st.error(str(erreur))
    if ACTIONS_EN_ATTENTE:
        etat.action = ACTIONS_EN_ATTENTE[-1]

if etat.resultat:
    st.subheader("Réponse")
    st.markdown(etat.resultat)

# --- Human-in-the-loop : rien ne s'exécute sans validation ------------------------------
if etat.action:
    st.warning(f"**Action proposée par les agents :** {etat.action}")
    col_ok, col_non = st.columns(2)
    if col_ok.button("Valider", type="primary", use_container_width=True):
        traces.tracer("Humain", "HUMAIN", f"Validé : {etat.action}")
        etat.message_action, etat.action = executer_action(etat.action), None
        st.rerun()
    if col_non.button("Refuser", use_container_width=True):
        traces.tracer("Humain", "HUMAIN", f"Refusé : {etat.action}")
        etat.message_action, etat.action = "Action refusée : rien n'a été exécuté.", None
        st.rerun()
if etat.message_action:
    st.info(etat.message_action)
