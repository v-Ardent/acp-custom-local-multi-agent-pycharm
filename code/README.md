# Labo — Architecture agentique & orchestrateurs d'agents IA

Code du labo (3e bachelier, Hénallux). Tout est écrit **sans framework agentique** (pas de LangChain, CrewAI...) pour voir la mécanique : un agent, c'est un LLM + des outils + une boucle.

Le code utilise le SDK `openai`, qui sert seulement de « prise universelle ». Groq, Ollama et la plupart des fournisseurs parlent le même format : pour changer de fournisseur, on modifie le fichier `.env`, pas le code.

---

## 1. Installation (15 min, à faire avant le premier labo)

Il faut **Python 3.10 ou plus récent** (`python3 --version`).

### a) Créer un environnement virtuel et installer les dépendances

Toutes les commandes se lancent **depuis le dossier `code/`**.

```bash
cd code
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Quand l'environnement est actif, `(.venv)` apparaît au début de la ligne de commande. Il faut le réactiver (`source .venv/bin/activate`) à chaque nouveau terminal.

### b) Créer un compte Groq et une clé API (gratuit)

1. Allez sur <https://console.groq.com> et créez un compte (email, Google ou GitHub). Pas de carte bancaire.
2. Menu **API Keys** → **Create API Key** → copiez la clé. Elle ne sera plus affichée ensuite.

> Groq est une société américaine : vos requêtes partent aux États-Unis. N'y envoyez donc pas de données personnelles réelles. On en reparle dans la partie RGPD du projet.

### c) Créer le fichier `.env`

```bash
cp .env.example .env               # Windows : copy .env.example .env
```

Ouvrez `.env` et collez votre clé :

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=votre-cle-ici
LLM_MODEL=qwen/qwen3.8-27b
```

Le fichier `.env` contient votre clé : **ne le partagez pas et ne le mettez pas sur Git** (il est déjà dans `.gitignore`).

### d) Vérifier que tout marche

```bash
python demo_bloc1/1_appel_simple.py
```

Vous devez voir une réponse du modèle, puis un tableau avec les tokens consommés.

---

## 2. Structure du dossier

```
code/
├── README.md                 ce fichier
├── requirements.txt          dépendances (openai, python-dotenv, rich, requests, streamlit)
├── .env.example              modèle de configuration (Groq / Ollama)
├── common/                   code partagé par tous les labos
│   ├── llm.py                chat(), suivi des tokens, resume_couts(), gestion des erreurs
│   ├── traces.py             affichage coloré [PENSÉE] [ACTION] [OBSERVATION] [RÉPONSE]
│   └── agent.py              classe Agent réutilisable (nom, instructions, outils, run())
├── demo_bloc1/               démo de l'enseignant : « organiser une sortie de classe à Namur »
├── lab1_premier_agent/       bloc 2 : premier agent (secrétariat d'une école fictive)
│   ├── data/                 cours.json, etudiants.json, reglement.md
│   ├── outils_secretariat.py les 4 outils (fournis)
│   ├── enonce/               fichiers à compléter (TODO)
│   ├── solution/             corrigé
│   └── QUESTIONS.md          questions de réflexion
├── lab2_orchestration/       bloc 3 : router et supervisor (enonce/ + solution/)
├── lab3_couts_securite/      bloc 5 : mesure des coûts + prompt injection
└── template_projet/          kit de démarrage du projet (interface Streamlit + traces en direct)
```

Chaque appel au modèle est enregistré dans `traces.jsonl` (agent, tokens, durée). Ce fichier sert au calcul des coûts (lab 3).

---

## 3. Lancer chaque partie

Toujours depuis le dossier `code/`, avec l'environnement virtuel activé.

### Démo du bloc 1 : du prompt à l'orchestrateur

| Script | Ce qu'il montre |
|---|---|
| `python demo_bloc1/1_appel_simple.py` | un LLM seul : il ne connaît pas la météo de samedi (il invente ou botte en touche) |
| `python demo_bloc1/2_avec_outil.py` | le même LLM avec un outil météo **réel** (Open-Meteo) : un aller-retour d'outil |
| `python demo_bloc1/3_agent_boucle.py` | un agent ReAct : météo → activités → budget, en boucle (max 8 itérations) |
| `python demo_bloc1/4_multi_agents.py` | un superviseur + 3 agents (météo, activités, rédacteur) + validation humaine avant l'envoi |

### Lab 1 : premier agent (bloc 2, 2 h)

Les fichiers à compléter sont dans `lab1_premier_agent/enonce/`, dans l'ordre :

```bash
python lab1_premier_agent/enonce/etape1_appel.py
python lab1_premier_agent/enonce/etape2_outil.py
python lab1_premier_agent/enonce/etape3_boucle_react.py
python lab1_premier_agent/enonce/etape4_memoire.py
python lab1_premier_agent/enonce/bonus_reflection.py
```

Tant qu'un TODO n'est pas complété, le script s'arrête avec un message jaune **« À compléter : TODO n ... »**. Le corrigé est dans `lab1_premier_agent/solution/`.

### Lab 2 : orchestration (bloc 3, 30 min)

```bash
python lab2_orchestration/enonce/orchestrateur_router.py       # après avoir complété agents_secretariat.py
python lab2_orchestration/enonce/orchestrateur_supervisor.py
```

### Lab 3 : coûts et sécurité (bloc 5, 30 min)

```bash
python lab3_couts_securite/mesure_couts.py                     # analyse traces.jsonl
python lab3_couts_securite/mesure_couts.py --dernieres 3       # seulement les 3 dernières demandes
python lab3_couts_securite/prompt_injection/attaque.py         # agent vulnérable
python lab3_couts_securite/prompt_injection/defense.py         # même agent, 3 protections
```

### Template du projet

```bash
streamlit run template_projet/app.py
```

Voir `template_projet/README.md` pour y brancher vos propres agents.

---

## 4. Changer de fournisseur de LLM

Le fichier `.env.example` contient 2 blocs. Décommentez-en **un seul** dans votre `.env` :

- **Groq** (par défaut) : gratuit, sans carte bancaire, appel d'outils disponible. Modèle `qwen/qwen3.8-27b`. Limites : 8 000 tokens par minute et 1 000 requêtes par jour, par clé.
- **Ollama** (plan B) : en local, gratuit et hors ligne, mais il faut une machine correcte. Installez Ollama, puis `ollama pull qwen2.5:3b` (ou `qwen2.5:7b`, nettement plus fiable pour les outils si votre machine le permet).

---

## 5. Dépannage

**« Problème avec le LLM : Aucune clé API trouvée »**
Le fichier `.env` n'existe pas, n'est pas dans le dossier `code/`, ou la clé n'a pas été collée. Vérifiez avec `cat .env`.

**« Clé API refusée (erreur 401) »**
La clé est mal copiée (espace en trop, guillemets, clé révoquée) ou ne correspond pas au fournisseur de `LLM_BASE_URL` (clé Groq envoyée à une autre adresse...). Recréez une clé si besoin.

**« Erreur 429 (trop de requêtes) : nouvelle tentative dans ... s »**
Le plan gratuit de Groq limite les tokens par minute (8 000). Les scripts à plusieurs agents dépassent souvent cette limite : le code réessaie automatiquement (2, 5, 10 puis 20 s), une pause de 10 à 20 s est donc normale. Si l'erreur persiste : attendez une minute et évitez de lancer plusieurs scripts en même temps avec la même clé.

**« Modèle ou adresse introuvable (erreur 404) »**
Le nom du modèle dans `LLM_MODEL` est faux (faute de frappe, modèle retiré). Avec Ollama : le modèle n'a pas été téléchargé (`ollama pull ...`).

**« Impossible de joindre ... »**
Pas de connexion internet, proxy de l'école, ou (avec Ollama) le serveur n'est pas lancé : `ollama serve`.

**Le modèle n'appelle pas les outils / répond « je vais chercher... » puis s'arrête**
- Vérifiez que le modèle supporte l'appel d'outils (`qwen/qwen3.8-27b` le supporte ; si vous changez de modèle, vérifiez-le dans la liste des modèles du fournisseur).
- Les petits modèles (Ollama 3B) se trompent souvent : essayez un modèle plus gros.
- Améliorez la **description** de l'outil (le modèle ne voit qu'elle) et le prompt système (« utilise l'outil X pour... »).

**`ModuleNotFoundError: No module named 'openai'` (ou `rich`, `dotenv`...)**
L'environnement virtuel n'est pas activé (`source .venv/bin/activate`) ou `pip install -r requirements.txt` n'a pas été lancé.

**`ModuleNotFoundError: No module named 'common'`**
Lancez les scripts avec le chemin complet depuis `code/` (ex. `python lab1_premier_agent/solution/etape1_appel.py`), sans déplacer le dossier `common/`.

**Les couleurs ne s'affichent pas (Windows)**
Utilisez Windows Terminal ou le terminal de VS Code plutôt que l'ancienne invite de commandes.
