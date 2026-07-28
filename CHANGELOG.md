# Changelog

## 0.7.0 — Économie locale et marché du travail

### Ajouté

- Comptabilité journalière des employeurs : trésorerie, recettes, masse salariale, coûts fixes, résultat et historique.
- Capacité, effectif cible, postes ouverts, niveau de service et états sain, fragile, déficitaire ou fermé.
- Activité privée liée au travail productif et financement budgétaire explicite des services publics.
- Chômage, recherche d'emploi, candidatures, scoring déterministe, recrutement, refus, démission, changement et licenciement.
- Délai entre changements d'emploi, expérience par métier et plafonds d'embauche pour éviter les boucles instables.
- Revenus et dépenses par foyer, budgets alimentaires et de biens, découvert, dette et stress financier.
- Influence bornée du stress financier sur les conflits domestiques.
- Endpoints `/api/economy` et `/api/enterprises/{id}`.
- Métriques économiques dans l'instantané de ville et tableau de bord frontend.
- Fenêtres de monitoring des entreprises et de la situation professionnelle et financière des citoyens.
- Filtre d'événements économiques avec navigation vers les entités concernées.
- Tests de simulation sur 30 jours, économie, embauche, licenciement, fermeture, finances domestiques, sauvegarde, API et WebSocket.
- Module `snapshot.py` séparant la projection dynamique du cœur de simulation.
- Trois tests frontend pour la fusion des messages WebSocket.
- Locks reproductibles Python et npm.

### Modifié

- Le WebSocket envoie un instantané complet à la connexion puis des deltas dynamiques qui réutilisent la géométrie statique côté client.
- Les achats et salaires alimentent désormais la comptabilité de l'entreprise et du foyer sans double versement quotidien.
- Le score de conflit domestique tient compte du stress financier.
- Le moteur de sauvegarde passe au format strict 7 et persiste tout l'état économique ainsi que l'état du générateur aléatoire.
- Les versions backend et frontend passent à 0.7.0.
- Les deltas WebSocket ne calculent plus les cellules routières, arrêts ou lignes statiques.
- Vite passe à 6.4.3 et Vitest à 3.2.6 ; l'audit npm ne remonte plus de vulnérabilité.
- Le build sépare React, Pixi et l'application en chunks inférieurs à 500 kB.
- Les tests Starlette utilisent `httpx2` et ne produisent plus d'avertissement de dépréciation.

### Compatibilité

- Les sauvegardes v1 à v6 sont rejetées explicitement. Aucune migration approximative n'est tentée.

### Limites connues

- Les recettes hors commerce utilisent une demande abstraite proportionnelle au travail productif.
- Les employeurs publics ne ferment pas et leur financement n'est pas soumis à un budget municipal plafonné.
- Il n'existe pas encore de fiscalité, d'inflation, de chaîne d'approvisionnement ou de formation professionnelle.

## 0.6.0 — Travail, commerces et police citoyenne

### Ajouté

- Horaires et jours de travail propres à chaque emploi.
- Équipes matin et soir pour la police et l'usine.
- Suivi du temps travaillé, de la performance, de la satisfaction et des absences.
- Salaire proportionnel à la présence effective.
- Personnel minimum et état opérationnel des lieux de service.
- Réserves domestiques de nourriture et de biens courants.
- Courses réelles au Marché Central.
- Stocks et recettes du commerce.
- Policiers représentés par de vrais habitants.
- Équipages de patrouille composés de deux agents en service.
- Rappel à la loi, cellule temporaire, dégrisement et garde à vue.
- Historique des mesures policières dans la fiche habitant.
- Inspection complète des bâtiments et de leurs employés.
- Fenêtre générique complète pour bâtiments, véhicules et incidents.
- Indicateurs de travail, de commerce et de police dans le tableau de bord.

### Modifié

- La fiche habitant est l'unique source des appels à `/api/citizens/{id}`.
- Les rafraîchissements périodiques sont suspendus lorsque la simulation est en pause.
- Un pas manuel en pause provoque une actualisation unique.
- Les panneaux latéraux ont une hauteur stable et un défilement indépendant.
- Le moteur de sauvegarde passe au format 6.

### Supprimé

- Migration des sauvegardes v0.1 à v0.5.
- Salaire fixe versé sans tenir compte de la présence.
- Patrouilles capables d'intervenir sans agents humains.
