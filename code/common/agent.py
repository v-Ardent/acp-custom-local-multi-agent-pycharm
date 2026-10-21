"""
Une classe Agent réutilisable : un nom, des instructions, des outils, et une
boucle ReAct (pensée -> action -> observation) qui tourne jusqu'à la réponse.

Exemple :
    agent = Agent(
        nom="Agent horaires",
        instructions="Tu réponds aux questions sur l'horaire des cours.",
        outils=[(horaire_du_jour, SCHEMA_HORAIRE_DU_JOUR)],
    )
    print(agent.run("Quels cours ai-je lundi ?"))

Un agent peut lui-même devenir un outil pour un autre agent (un superviseur) :
    outil = agent.comme_outil("demander_agent_horaires", "Répond aux questions d'horaire")
"""

import json

from common import traces
from common.llm import chat, lire_arguments, message_assistant, message_outil, schema_outil


class Agent:
    def __init__(self, nom, instructions, outils=None, max_iterations=6):
        """
        nom            : nom affiché dans les traces (ex. "Agent météo")
        instructions   : le prompt système (rôle, règles, style de réponse)
        outils         : liste de couples (fonction_python, schema_de_l_outil)
        max_iterations : garde-fou contre les boucles infinies
        """
        self.nom = nom
        self.instructions = instructions
        self.max_iterations = max_iterations
        outils = outils or []
        # nom de l'outil -> fonction Python à exécuter
        self.fonctions = {schema["function"]["name"]: fonction for fonction, schema in outils}
        # descriptions envoyées au modèle
        self.schemas = [schema for _, schema in outils]

    def run(self, demande):
        """Traite une demande et renvoie la réponse finale (texte)."""
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": demande},
        ]
        traces.tracer(self.nom, "DEMANDE", demande)

        for _ in range(self.max_iterations):
            message = chat(messages, tools=self.schemas or None, agent=self.nom)

            # Pas d'outil demandé : c'est la réponse finale
            if not message.tool_calls:
                texte = message.content or ""
                traces.reponse(self.nom, texte)
                return texte

            # Le modèle a parfois écrit son raisonnement avant d'appeler un outil
            if message.content:
                traces.pensee(self.nom, message.content)

            messages.append(message_assistant(message))
            for appel in message.tool_calls:
                resultat = self.executer_outil(appel)
                messages.append(message_outil(appel, resultat))

        traces.tracer(self.nom, "INFO", f"Limite de {self.max_iterations} itérations atteinte : arrêt.")
        return "Je n'ai pas pu terminer : limite d'itérations atteinte."

    def executer_outil(self, appel):
        """Exécute l'outil demandé par le modèle et renvoie le résultat sous forme de texte."""
        nom_outil = appel.function.name
        arguments = lire_arguments(appel)
        traces.action(self.nom, nom_outil, arguments)

        if nom_outil not in self.fonctions:
            resultat = f"Erreur : l'outil '{nom_outil}' n'existe pas. Outils disponibles : {list(self.fonctions)}"
        else:
            try:
                resultat = self.fonctions[nom_outil](**arguments)
            except Exception as erreur:  # on renvoie l'erreur au modèle au lieu de planter
                resultat = f"Erreur pendant l'exécution de {nom_outil} : {erreur}"

        if not isinstance(resultat, str):
            resultat = json.dumps(resultat, ensure_ascii=False)
        traces.observation(self.nom, resultat)
        return resultat

    def comme_outil(self, nom_outil, description):
        """
        Transforme cet agent en outil utilisable par un autre agent (pattern Supervisor).
        Renvoie un couple (fonction, schema), comme les autres outils.
        """
        def deleguer(demande):
            return self.run(demande)

        schema = schema_outil(nom_outil, description, {
            "demande": {"type": "string",
                        "description": "La demande complète et précise à transmettre à cet agent."},
        })
        return deleguer, schema
