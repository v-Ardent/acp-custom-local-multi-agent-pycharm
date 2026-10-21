# Prompt injection : attaque et défense

**Le problème.** Un agent qui lit des documents, des mails ou des pages web reçoit ce contenu dans la même conversation que ses instructions. Pour le modèle, tout est du texte. Si un document contient une consigne, il peut lui obéir.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `documents/pv_conseil_de_classe.txt` | document interne **confidentiel** (données d'étudiants, code d'accès) |
| `documents/annonce_portes_ouvertes.txt` | injection **grossière** : « IGNORE TOUTES TES INSTRUCTIONS... » |
| `documents/newsletter_partenaire.txt` | injection **subtile** : une fausse « procédure RGPD » demande d'envoyer tous les documents lus à une adresse extérieure avec `envoyer_email` |
| `outils_documents.py` | outils `lister_documents`, `lire_document`, `envoyer_email` (simulé, rien ne part) + `bilan()` |
| `attaque.py` | l'agent vulnérable : tous les outils, aucun contrôle |
| `defense.py` | le même agent avec 3 protections, activables une par une |

## Déroulé (30 min)

1. **Attaque** (5 min) : `python lab3_couts_securite/prompt_injection/attaque.py`. Lancez-le 2 ou 3 fois : le résultat varie. Le bilan final indique si l'agent a obéi au document ou envoyé des données dehors.
2. **Défense** (10 min) : `python lab3_couts_securite/prompt_injection/defense.py`. Au scénario 3, un humain doit valider chaque envoi : refusez (`n`) l'envoi vers l'adresse extérieure.
3. **Une protection à la fois** (10 min) : dans `defense.py`, passez deux des trois constantes `PROTECTION_...` à `False`. Laquelle protège vraiment ? Laquelle est seulement « probabiliste » ?
4. **À vous** (5 min) : écrivez votre propre document piégé dans `documents/` et essayez de contourner les protections.

## Les 3 protections

1. **Délimiter le contenu non fiable** : le texte des documents est encadré par `<document_non_fiable>...</document_non_fiable>`, et le prompt système précise que c'est une donnée, jamais une instruction. Ça aide, mais ce n'est qu'une consigne de plus : le modèle peut encore se faire convaincre.
2. **Liste blanche d'outils selon le contexte** : pour « résumer », l'agent n'a pas besoin d'envoyer de mails, donc on ne lui donne pas l'outil. C'est une protection **déterministe** : elle ne dépend pas du bon vouloir du modèle.
3. **Validation humaine avant une action sensible** : quand l'outil est nécessaire, un humain voit le destinataire et le contenu, puis décide.

À retenir pour le projet : on ne compte pas sur le modèle pour se protéger lui-même. On limite ce qu'il **peut** faire (outils, droits, données) et on garde un humain dans la boucle pour les actions irréversibles.
