# Template de projet : prototype multi-agent avec traces en direct

Point de départ pour le prototype présenté en démo à la défense :

- une zone de saisie de la demande ;
- un **orchestrateur** (pattern Supervisor) et 2 agents d'exemple, à remplacer par les vôtres ;
- un **panneau de traces en direct** (à gauche) : quel agent travaille, quelle action, quel outil, combien de tokens ;
- un compteur de tokens et de coût estimé, cumulé sur la session ;
- un point **human-in-the-loop** : les actions sensibles attendent un clic sur *Valider* ou *Refuser*.

## Lancer

Depuis le dossier `code/`, avec l'environnement virtuel activé et le `.env` configuré :

```bash
streamlit run template_projet/app.py
```

Le navigateur s'ouvre sur <http://localhost:8501>. Les traces s'affichent aussi dans le terminal.

## Les fichiers

| Fichier | À modifier ? | Rôle |
|---|---|---|
| `mes_agents.py` | **oui** | vos outils, vos agents, votre orchestrateur |
| `app.py` | rarement | l'interface Streamlit (traces, compteurs, validation humaine) |
| `../common/` | non | `llm.py` (appels + tokens), `agent.py` (classe Agent), `traces.py` (affichage) |

Pour votre propre dépôt Git, copiez `template_projet/`, `common/`, `requirements.txt` et `.env.example` en gardant la même organisation (`common/` à côté du dossier de l'application).

## Où brancher vos agents (dans `mes_agents.py`)

**1. Un outil = une fonction Python + un schéma** (la notice lue par le modèle) :

```python
def chercher_meteo(ville):
    ...                                   # appel d'API, lecture de fichier, calcul...
    return {"ville": ville, "temperature": 18}

SCHEMA_METEO = schema_outil("chercher_meteo", "Donne la météo actuelle d'une ville.",
                            {"ville": {"type": "string", "description": "Nom de la ville"}})
```

**2. Un agent = un nom, des instructions, des outils :**

```python
agent_meteo = Agent(nom="Agent météo",
                    instructions="Tu es météorologue. Utilise chercher_meteo, n'invente rien.",
                    outils=[(chercher_meteo, SCHEMA_METEO)])
```

**3. L'orchestrateur** (`creer_superviseur()`) reçoit vos agents comme outils :

```python
agent_meteo.comme_outil("demander_agent_meteo", "Donne la météo d'une ville.")
```

La description passée à `comme_outil` est ce que lit le superviseur pour choisir à qui déléguer : soignez-la.

**4. Human-in-the-loop** : un agent qui veut agir (envoyer, publier, réserver...) appelle `proposer_action(description)`. Rien n'est exécuté : l'interface affiche l'action avec *Valider* / *Refuser*. Remplacez le contenu de `executer_action()` par la vraie action.

## Adapter

- **Prix** : `PRIX_ENTREE` et `PRIX_SORTIE` en haut de `app.py`, en $ par million de tokens, selon votre modèle.
- **Autre pattern d'orchestration** (router, séquentiel...) : remplacez `creer_superviseur()` par une fonction qui renvoie un objet avec une méthode `run(demande)`.
- **Coûts détaillés** : toutes les demandes sont enregistrées dans `traces.jsonl`. Lancez `python lab3_couts_securite/mesure_couts.py` pour l'étude économique.
