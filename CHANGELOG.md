# Changelog

## 0.13.0 — Criminalité systémique et renseignement

### Ajouté

- Factions criminelles typées, hiérarchies de rôles, territoires, influence, rivalités, alliances, recrutement et guerres de territoire.
- Marchés de drogues, armes, recel et contrefaçons avec prix, offre, demande, stocks, saisies et transactions citoyennes persistantes.
- Dépendance, risque d’usage, contacts criminels, revenus illégaux, dépenses illégales et conséquences sanitaires/professionnelles individuelles.
- Trafic de gros, blanchiment, corruption et raids policiers ; qualifications et peines judiciaires dédiées.
- Monitoring plein écran et endpoint de détail des factions.
- Six tests backend systémiques supplémentaires.

### Modifié

- Population maximale portée de 1 000 à 5 000 citoyens ; variable d’environnement de démarrage désormais respectée.
- Cadence WebSocket adaptative de 0,5 à 2 secondes selon la population.
- Groupe d’indicateurs Sécurité maintenu à six cartes, recentré sur factions, membres, ventes, dépendances et territoires.
- Sauvegarde stricte v14 ; versions backend et frontend portées à 0.13.0.

### Limites connues

- Le marché clandestin est agrégé par quartier et produit, pas au niveau de chaque rue ou point de deal physique.
- Les enquêtes financières et infiltrations ne sont pas encore des dossiers spécialisés ; les incidents détectés suivent le pipeline judiciaire commun.
- À 5 000 citoyens, un snapshot initial approche 3 Mo et l’initialisation observée prend environ 3 secondes sur la machine de validation.


## 0.12.0 — Banque, précarité et crime organisé

### Ajouté

- Population configurable jusqu’à 1 000 citoyens et capacité urbaine proportionnelle.
- Banque, refuge municipal, comptes, épargne, prêts, intérêts, échéances, défauts et registre de transactions.
- Sans-abrisme déclenché par impayés persistants ou incapacité durable à se nourrir, avec accueil et relogement.
- Mafias territoriales, vols, braquages, extorsions, enlèvements, rançons, notoriété et pression policière.
- Tentatives probabilistes de violation des interdictions de communication et conséquences judiciaires.
- Palette cartographique, volumes, végétation, voirie et implantation résidentielle renouvelés.
- Cinq scénarios backend dédiés et extension des tests de monitoring frontend.

### Modifié

- Un emploi maximum par citoyen et retrait des candidatures concurrentes après embauche.
- Plus de trente intitulés de métier et distinction entre capacité d’embauche et besoin cible.
- Tous les principaux flux monétaires utilisent le module bancaire partagé.
- Sauvegarde stricte v13 ; versions backend et frontend portées à 0.12.0.

### Limites connues

- Une mafia est une organisation agrégée : pas encore de hiérarchie interne, blanchiment, informateurs ou contrôle fin de chaque rue.
- Les prêts utilisent une décision de crédit volontairement lisible, sans garanties, faillite personnelle ni banque concurrente.
- La construction et la migration entre villes ne sont pas simulées ; les capacités des bâtiments évoluent avec la taille choisie.


## 0.11.0 — Quartiers, sécurité et services publics

### Ajouté

- Quatre quartiers générés et persistants, avec treize métriques territoriales issues de la simulation.
- Historique journalier, sécurité ressentie et attractivité évolutives.
- Patrouilles mobiles par zone, affectées à des unités et policiers citoyens réellement en service.
- Dispatch de l’unité disponible la plus proche et temps de réponse agrégé par quartier.
- Influence de l’éclairage, de l’activité, des témoins et de la présence policière sur les opportunités criminelles.
- API, domaine WebSocket, six indicateurs globaux, filtre Quartiers et huit scénarios backend.
- Neuf cartes thématiques interactives et fenêtre quartier complète.
- Deux tests frontend dédiés aux données thématiques.

### Modifié

- Sauvegarde stricte v12 ; les versions v1 à v11 sont refusées.
- Versions backend et frontend portées à 0.11.0.
- Les unités en patrouille restent disponibles pour un dispatch et sont comptées comme telles.

### Limites connues

- Quatre zones fixes, sans redécoupage administratif, construction ou budget municipal propre.
- L’éclairage est une caractéristique persistante mais n’est pas encore améliorable par une décision publique.
- Deux véhicules ne peuvent couvrir simultanément les quatre quartiers.


## 0.10.1 — Communications interpersonnelles

### Ajouté

- Appels téléphoniques, SMS, e-mails et lettres persistants, avec capacités, coûts, délais, lecture et échecs propres à chaque canal.
- Fils de discussion et réponses autonomes limitées à deux niveaux.
- Tons de communication influençant les relations sociales et le stress organisationnel.
- Planification événementielle et générateur pseudo-aléatoire dédié, déterministe et sérialisé.
- API de consultation et d’envoi, domaine WebSocket, métriques et événements filtrables.
- Monitoring global et onglet Communications complet dans la fiche citoyen.
- Sept scénarios backend et deux tests frontend dédiés.

### Modifié

- Sauvegarde stricte v11 avec file de livraison/lecture exacte ; les versions v1 à v10 sont refusées.
- Versions backend et frontend portées à 0.10.1.
- Le groupe d’indicateurs Social présente les communications du jour sans augmenter le nombre de cartes.

### Limites connues

- Pas de pièces jointes, appels de groupe, répondeur, opérateur postal incarné, spam ou authentification des adresses.
- Le contenu textuel autonome repose sur des modèles courts ; il ne s’agit pas d’un moteur conversationnel génératif.


## 0.10.0 — Justice, probation et détention

### Ajouté

- Plaintes persistantes reliées aux incidents, plaignants, mis en cause et motifs de classement.
- Revue du parquet, poursuites, classement sans suite, audiences prioritaires et reports liés à la capacité réelle.
- Tribunal et centre de détention avec juge, greffiers et surveillants incarnés par des citoyens.
- Peines structurées : rappel judiciaire, amende, indemnisation, probation, TIG, interdiction de contact et détention.
- Suivi horaire des peines, violation de probation, progression du TIG et libération bornée.
- Conséquences sur l’emploi, les finances, le stress, les relations et les déplacements.
- Endpoint `/api/justice`, données justice dans les snapshots et deltas WebSocket.
- Fenêtres tribunal et dossier, monitoring institutionnel, chronologie citoyen et filtre Justice.
- Neuf scénarios backend et trois tests frontend dédiés.

### Modifié

- Sauvegarde stricte v10 ; les versions v1 à v9 sont refusées.
- Versions backend et frontend portées à 0.10.0.
- Les bâtiments tribunal et détention deviennent des employeurs publics ordinaires.

### Limites connues

- Pas d’appel, d’avocat, de jury, de fiscalité pénale ou de procédure contradictoire détaillée.
- Le parquet est une étape institutionnelle agrégée ; les audiences durent un créneau simulé.

## 0.9.0 — Logement, loyers et mobilité résidentielle

### Ajouté

- Module `housing.py`, parc et marché résidentiel multi-critères.
- Loyers, impayés, recherche, déménagement groupé, séparation, cohabitation et relogement temporaire.
- Huit résidences supplémentaires, dont cinq réservées vacantes à l'initialisation.
- API, WebSocket, fenêtres logement/foyer, métriques, filtre d'événements et six tests d'acceptation.

### Modifié

- Sauvegarde stricte v9 et versions applicatives 0.9.0.
- Panneau d’indicateurs compacté en sept catégories de six cartes maximum.
- `App.tsx`, les inspecteurs et la modale foyer découpés en composants et hooks spécialisés.
- API, WebSocket, métriques, présentateurs de monitoring et persistance extraits du noyau backend.
- Styles d’indicateurs historiques orphelins supprimés et contrats critiques couverts par des tests unitaires.

### Limites connues

- Pas d'achat, crédit, construction, fiscalité ou bail détaillé ; sécurité locale agrégée.

## 0.8.0 — Santé, blessures et secours

### Ajouté

- Modèle individuel de santé, douleur, blessures, maladies, incapacité, arrêt de travail, hospitalisation, convalescence et guérison.
- Moteur `health.py` isolé avec événements de maladie, épuisement, nutrition, alcool, âge et accidents routiers rares.
- Centre médical de huit lits, médecins et infirmiers citoyens en équipes, file et délais sensibles au sous-effectif.
- Deux ambulances avec équipage citoyen obligatoire, trajet routier, embarquement et transport réel du patient.
- Examen médical préalable à certaines cellules et transfert police-hôpital.
- Certificats médicaux post-consultation renforçant la confiance des enquêtes.
- Endpoint `/api/healthcare`, données santé dans les snapshots/deltas et détails enrichis.
- Onglet Santé, fenêtre hospitalière, fiche ambulance, filtre d’événements et quatre couches cartographiques.
- Six tests d’acceptation santé, dont transport, sous-effectif, preuve, sauvegarde et anti-blocage.

### Modifié

- Format de sauvegarde strict 8, incluant dossiers, files, lits, véhicules, équipages et générateur aléatoire santé.
- Capacité globale d’emploi conservée : huit emplois médicaux remplacent huit emplois ordinaires.
- Les absences médicales empêchent présence, salaire et départ vers le travail pendant l’incapacité.
- Versions backend et frontend portées à 0.8.0.

### Compatibilité

- Les sauvegardes v1 à v7 sont rejetées explicitement.

### Limites connues

- Modèle médical simplifié, sans diagnostic clinique, médicaments, chirurgie ni mortalité.
- Relève nocturne par transport non urgent après 120 minutes si aucun équipage n’est disponible.

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
