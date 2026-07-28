# MANIFESTE CODEX — City Simulator

## 1. Mission

Faire évoluer **City Simulator** à partir de la version **v0.6.0**.

Le projet est un simulateur de ville 2D orienté monitoring. La priorité n’est pas l’animation, mais la cohérence de la simulation, la lisibilité des comportements et la capacité à inspecter chaque habitant, bâtiment, véhicule, incident et institution.

Le système doit produire des histoires émergentes compréhensibles : emploi, revenus, consommation, relations sociales, conflits, interventions policières, justice, santé, logement et mobilité.

---

## 2. État actuel du projet

### Frontend

- React
- TypeScript
- PixiJS
- Carte 2D
- Communication REST et WebSocket
- Fenêtres complètes pour les habitants, bâtiments, véhicules, incidents et le graphe social
- Rafraîchissement suspendu lorsque la simulation est en pause
- Sélection stable sans clignotement ni déplacement de la carte

### Backend

- Python
- FastAPI
- Moteur de simulation indépendant de l’API
- Simulation déterministe fondée sur une graine
- Sauvegardes JSON de version v0.6.0 uniquement
- WebSocket pour les snapshots et deltas
- Tests automatisés

### Fonctionnalités existantes

- 100 habitants persistants
- foyers et logements
- besoins individuels
- marche, voitures et bus
- emplois et présence au travail
- salaires selon le temps réellement travaillé
- commerces avec stock, employés et recettes
- consommation de nourriture et de biens courants
- personnalités et tempéraments
- relations sociales, amitiés, rivalités et conflits
- mémoire durable des différends
- incidents structurés
- interventions de police
- policiers incarnés par de vrais citoyens
- rappels à la loi, cellule temporaire, dégrisement et garde à vue
- enquêtes simplifiées, preuves, suspects et arrestations
- dossiers judiciaires, audiences et décisions simplifiées
- graphe social global

---

## 3. Principes non négociables

### 3.1 Séparation simulation / interface

Le frontend ne doit jamais devenir la source de vérité. Le backend détient l’état réel de la ville. Le frontend affiche des snapshots ou des deltas et envoie des commandes.

Le moteur de simulation ne doit pas dépendre de FastAPI, React ou PixiJS.

### 3.2 Déterminisme

À graine, commandes et état initial identiques, la simulation doit produire le même résultat.

Toute nouvelle mécanique aléatoire doit utiliser le générateur pseudo-aléatoire du monde ou du moteur, jamais un appel aléatoire global incontrôlé.

### 3.3 Simulation événementielle

Ne pas recalculer inutilement tous les habitants à chaque tick. Préférer les événements programmés, décisions déclenchées par besoin, traitements espacés, agrégation et mises à jour différentielles.

### 3.4 UI / UX de monitoring

Toute nouvelle entité importante doit disposer d’une vraie fenêtre ou modale cohérente avec les fenêtres existantes.

Ne jamais :

- faire bouger la carte quand une fiche s’ouvre ;
- reconstruire toute la scène PixiJS à chaque snapshot ;
- fermer le graphe social lorsqu’un habitant est consulté ;
- afficher un état « Chargement » à chaque rafraîchissement ;
- lancer un polling périodique lorsque la simulation est en pause ;
- multiplier les appels REST pour une même fiche.

Les panneaux doivent conserver leur contenu pendant l’actualisation.

### 3.5 Sauvegardes

La rétrocompatibilité avec les versions antérieures à v0.6.0 n’est pas requise.

À partir de maintenant :

- conserver un numéro de version de sauvegarde ;
- documenter toute rupture de format ;
- privilégier la rapidité d’itération ;
- refuser proprement un format incompatible avec un message explicite.

### 3.6 Performance

Objectif minimal :

- 100 habitants sans ralentissement perceptible ;
- simulation de 30 jours sans fuite mémoire ;
- possibilité de monter progressivement à 1 000 habitants ;
- aucune boucle quadratique non justifiée sur toutes les relations ;
- aucun snapshot complet envoyé plusieurs fois par seconde si un delta suffit.

### 3.7 Tests

Chaque lot doit ajouter :

- tests unitaires des nouvelles règles ;
- test de simulation longue durée ;
- test sauvegarde / reprise ;
- test des endpoints ajoutés ;
- test des messages WebSocket ajoutés ;
- test des cas limites ;
- vérification qu’aucun habitant ne reste bloqué dans un état transitoire.

---

# 4. Prochaines versions

## LOT 1 — v0.7.0 — Économie locale et marché du travail

### Objectif

Transformer le travail actuel en véritable système économique local.

Les habitants doivent pouvoir perdre leur emploi, en chercher un autre, être recrutés, changer de poste, subir une baisse de revenus et adapter leur consommation.

Les entreprises doivent avoir des besoins de personnel, des charges, des recettes, une rentabilité et un risque de fermeture.

### Fonctionnalités backend

#### Entreprises

Ajouter à chaque entreprise :

- trésorerie ;
- chiffre d’affaires ;
- charges salariales ;
- charges fixes ;
- rentabilité ;
- capacité maximale ;
- effectif requis ;
- postes ouverts ;
- niveau de service ;
- historique financier ;
- statut : saine, fragile, déficitaire ou fermée.

#### Marché du travail

Ajouter :

- chômage ;
- recherche d’emploi ;
- candidatures ;
- recrutement ;
- licenciement ;
- démission ;
- changement d’emploi ;
- comparaison salaire / distance / horaires / satisfaction ;
- délai minimal avant un nouveau changement ;
- expérience simplifiée par métier ;
- adéquation entre profil et poste.

#### Revenus et dépenses

Ajouter :

- revenu du foyer ;
- dépenses récurrentes simples ;
- budget alimentaire ;
- budget de biens courants ;
- arbitrage de consommation en cas de manque d’argent ;
- dette légère ou découvert limité ;
- stress financier ;
- risque de conflit domestique lié aux difficultés financières.

#### Emploi public

La mairie, le commissariat et les futurs services de santé doivent fonctionner comme des employeurs ordinaires.

Le budget public peut rester simplifié mais doit suivre la masse salariale, le nombre d’agents, la capacité de service et les dépenses quotidiennes.

### Fonctionnalités frontend

#### Fenêtre entreprise

Afficher :

- employés ;
- postes ouverts ;
- masse salariale ;
- recettes ;
- charges ;
- résultat ;
- niveau de service ;
- historique récent ;
- causes des recrutements et licenciements.

#### Fenêtre habitant

Ajouter un onglet « Travail et finances » avec emploi actuel, ancien emploi, salaire, temps travaillé, candidatures, licenciements, démissions, revenus du foyer, dépenses et stress financier.

#### Tableau de bord

Ajouter :

- taux de chômage ;
- postes vacants ;
- entreprises déficitaires ;
- salaire médian ;
- revenu médian des foyers ;
- recrutements ;
- licenciements.

### Critères d’acceptation

- Un habitant sans emploi cherche réellement un poste.
- Une entreprise déficitaire peut réduire ses effectifs.
- Une entreprise sous-staffée peut ouvrir des postes.
- Les habitants ne changent pas d’emploi de manière chaotique.
- Le chômage influence l’argent, le stress et la consommation.
- Les policiers restent des employés de la ville.
- Une simulation de 30 jours produit des changements d’emploi cohérents.
- Aucun employé ne reçoit deux salaires pour la même période.

---

## LOT 2 — v0.8.0 — Santé, blessures et secours

### Objectif

Créer un système de santé simplifié mais connecté aux conflits, au travail, aux besoins et aux institutions.

### Fonctionnalités backend

#### Santé individuelle

Ajouter :

- santé générale ;
- douleur ;
- blessure ;
- maladie légère ;
- maladie grave rare ;
- incapacité temporaire ;
- récupération ;
- fatigue aggravée ;
- absence au travail ;
- risque de décès désactivé par défaut ou extrêmement rare.

#### Origines

Les problèmes de santé peuvent provenir de bagarres, agressions, accidents de circulation, épuisement, maladie, mauvaise alimentation, alcoolisation ou vieillissement simplifié.

#### Services de santé

Ajouter :

- centre médical ou hôpital ;
- médecins et infirmiers incarnés par des citoyens ;
- horaires ;
- capacité ;
- files d’attente ;
- consultation ;
- hospitalisation simplifiée ;
- ambulance ;
- dispatch selon gravité.

#### Interaction police / justice

Ajouter :

- constat médical ;
- incapacité temporaire ;
- preuve médicale dans une enquête ;
- transfert commissariat → hôpital ;
- impossibilité de placer certaines personnes en cellule sans examen médical.

### Fonctionnalités frontend

- Onglet « Santé » dans la fenêtre habitant.
- Fenêtre hôpital avec personnel, capacité, patients, attente, ambulances et niveau de service.
- Couches de carte santé, urgences, ambulances et établissements médicaux.

### Critères d’acceptation

- Une bagarre peut produire une blessure.
- Une blessure peut entraîner une absence au travail.
- Une ambulance ne part que si un équipage citoyen est disponible.
- Un patient est réellement transporté.
- Un hôpital sous-staffé augmente les délais.
- Une preuve médicale peut renforcer une enquête.
- Aucun patient ne reste indéfiniment dans un état transitoire.

---

## LOT 3 — v0.9.0 — Logement, loyers et mobilité résidentielle

### Objectif

Faire du logement un système vivant relié aux foyers, aux revenus, au travail et aux relations.

### Fonctionnalités backend

#### Logements

Ajouter capacité, loyer, état, confort, disponibilité, distance aux services, distance au travail, occupants et propriétaire abstrait ou municipal.

#### Foyers

Ajouter :

- budget commun ;
- dépenses de logement ;
- recherche de logement ;
- déménagement ;
- séparation de foyer ;
- formation de nouveau foyer ;
- cohabitation ;
- sur-occupation ;
- impayés ;
- expulsion simplifiée ;
- hébergement temporaire chez un proche.

#### Décision de déménagement

Le choix doit considérer loyer, revenu, taille du foyer, travail, relations, sécurité du quartier, temps de trajet et confort.

### Fonctionnalités frontend

- Fenêtre logement avec occupants, capacité, loyer, confort, état, historique et impayés.
- Fenêtre foyer avec membres, revenus, dépenses, réserves, cohésion, logement et historique des déménagements.
- Indicateurs : loyers médians, vacance, sur-occupation, foyers en difficulté, déménagements et temps domicile-travail.

### Critères d’acceptation

- Un foyer trop pauvre peut chercher un logement moins cher.
- Un foyer qui s’agrandit peut chercher plus grand.
- Un déménagement modifie réellement les trajets.
- Les membres d’un même foyer déménagent ensemble sauf séparation explicite.
- Aucun habitant ne perd son domicile sans état alternatif explicite.
- Les déménagements restent rares et justifiés.

---

## LOT 4 — v0.10.0 — Justice, probation et détention

### Objectif

Remplacer la justice simplifiée par une chaîne institutionnelle cohérente, sans chercher un réalisme juridique exhaustif.

### Fonctionnalités backend

#### Procédure

Ajouter :

- dépôt de plainte ;
- dossier d’enquête ;
- parquet simplifié ;
- classement sans suite ;
- poursuites ;
- audience ;
- verdict ;
- peine.

#### Peines

Ajouter :

- rappel judiciaire ;
- amende ;
- indemnisation ;
- probation ;
- travaux d’intérêt général ;
- interdiction de contact ;
- détention courte ;
- détention plus longue.

#### Institutions

Ajouter :

- tribunal ;
- juges, greffiers et agents incarnés par des citoyens ;
- capacité quotidienne ;
- dossiers en attente ;
- retards ;
- priorités ;
- centre de détention simplifié ;
- surveillants citoyens.

#### Conséquences sociales

Ajouter perte d’emploi, stress, dette, rupture de relation, rancune, baisse de confiance, difficulté à retrouver un emploi, récidive et respect ou violation de probation.

### Fonctionnalités frontend

- Fenêtre dossier judiciaire.
- Fenêtre tribunal.
- Chronologie judiciaire complète dans la fenêtre habitant.

### Critères d’acceptation

- Tous les incidents ne mènent pas automatiquement à une condamnation.
- Une enquête insuffisante peut être classée.
- Une audience nécessite une capacité institutionnelle.
- Une peine modifie réellement la vie de l’habitant.
- Une interdiction de contact influence les déplacements et interactions.
- Une détention empêche l’activité normale et conserve le suivi du foyer et de l’emploi.

---

## LOT 5 — v0.11.0 — Quartiers, sécurité et services publics

### Objectif

Créer des différences spatiales durables entre les quartiers.

### Fonctionnalités backend

Ajouter à chaque quartier :

- population ;
- revenus ;
- chômage ;
- loyers ;
- activité commerciale ;
- criminalité ;
- sentiment de sécurité ;
- couverture policière ;
- accès aux soins ;
- accès aux commerces ;
- temps de transport ;
- attractivité.

Ajouter également :

- patrouilles par zone ;
- temps de réponse selon distance et disponibilité ;
- services publics sous pression ;
- influence des incidents répétés sur la perception locale ;
- influence de l’éclairage, de l’activité et de la présence de témoins sur les opportunités criminelles.

### Fonctionnalités frontend

- Cartes thématiques revenus, chômage, criminalité, sécurité ressentie, temps de réponse, accessibilité, loyers, santé et fréquentation commerciale.
- Fenêtre quartier avec tendances, incidents, population, entreprises, services, attractivité et historique.

### Critères d’acceptation

- Deux quartiers peuvent évoluer différemment.
- La distance aux services a un effet réel.
- Les incidents répétés diminuent la sécurité ressentie.
- Une forte présence policière ne supprime pas automatiquement toute criminalité.
- Les cartes thématiques reposent sur les données de simulation, pas sur des valeurs décoratives.

---

# 5. Tâches transversales obligatoires

## Backend

- incrémenter la version de sauvegarde ;
- ajouter les modèles nécessaires ;
- maintenir les systèmes découplés ;
- exposer les nouvelles données via API ;
- ajouter les nouveaux deltas WebSocket ;
- éviter les snapshots complets inutiles ;
- mettre à jour le générateur de ville ;
- ajouter les tests.

## Frontend

- ajouter les types TypeScript ;
- ajouter une fenêtre complète par nouvelle entité importante ;
- conserver les modales ouvertes pendant les actualisations ;
- suspendre le polling en pause ;
- mettre à jour les données après un pas manuel ;
- conserver le contexte du graphe social ;
- éviter tout déplacement de la carte ;
- rendre les nouveaux événements cliquables ;
- ajouter des filtres de journal.

## Documentation

Pour chaque version :

- mettre à jour le README ;
- ajouter une section de migration ;
- documenter les ruptures de sauvegarde ;
- fournir la liste des fonctionnalités ;
- fournir les commandes Docker ;
- fournir les limites connues ;
- fournir les résultats de tests.

---

# 6. Règles d’implémentation pour Codex

## Méthode de travail

Pour chaque lot :

1. Inspecter le code existant avant modification.
2. Identifier les modèles, systèmes et endpoints concernés.
3. Éviter les réécritures globales non nécessaires.
4. Implémenter d’abord les règles backend.
5. Ajouter les tests backend.
6. Ajouter les API et messages WebSocket.
7. Ajouter le frontend.
8. Vérifier la pause et le pas manuel.
9. Exécuter les tests longue durée.
10. Mettre à jour la documentation.

## Sortie attendue

À la fin de chaque lot, fournir :

- résumé des changements ;
- liste des fichiers modifiés ;
- commandes de lancement ;
- résultats des tests ;
- limites connues ;
- archive complète ;
- patch depuis la version précédente ;
- somme SHA-256.

## Qualité du code

- typage Python explicite ;
- dataclasses ou modèles cohérents avec l’existant ;
- TypeScript strict ;
- pas de `any` non justifié ;
- fonctions courtes ;
- noms explicites ;
- commentaires uniquement lorsque la règle métier n’est pas évidente ;
- pas de dépendance supplémentaire sans justification.

---

# 7. Ordre conseillé

1. **v0.7.0 — Économie locale et marché du travail**
2. **v0.8.0 — Santé, blessures et secours**
3. **v0.9.0 — Logement, loyers et mobilité résidentielle**
4. **v0.10.0 — Justice, probation et détention**
5. **v0.11.0 — Quartiers, sécurité et services publics**

Ne pas commencer le lot suivant tant que les critères d’acceptation du lot courant ne sont pas satisfaits.

---

# 8. Définition de « terminé »

Un lot est terminé lorsque :

- les fonctionnalités sont visibles dans l’interface ;
- les données sont inspectables ;
- les systèmes interagissent réellement entre eux ;
- les événements sont journalisés ;
- la simulation tient au moins 30 jours ;
- la sauvegarde et la reprise sont stables ;
- les tests passent ;
- le frontend ne poll pas inutilement en pause ;
- aucun habitant, véhicule, patient, détenu ou intervention ne reste bloqué dans un état transitoire ;
- la documentation est à jour.
