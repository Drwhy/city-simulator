# City Simulator — v0.13.0 Criminalité systémique et renseignement

Simulateur urbain persistant de 20 à 5 000 habitants : économie, emplois uniques, logement, banque, communications, quartiers, services publics, factions criminelles, police et justice.

## Nouveautés v0.13.0

- Jusqu’à 5 000 citoyens configurables (`CITYSIM_CITIZEN_COUNT` ou sélecteur UI), avec 16 factions au plafond et cadence WebSocket adaptée au volume.
- Sept familles de factions : gangs de rue ou organisés, mafias, triades, cartels, gangs de motards et réseaux cybercriminels. Chaque groupe possède chef, rôles, territoires, rivaux, alliés, cohésion, violence, sophistication, influence et pression de recrutement.
- Six marchés illicites : cannabis, cocaïne, drogues de synthèse, armes, biens volés et contrefaçons. Offre, demande, prix, stocks, pression policière et saisies évoluent quotidiennement.
- Transactions réelles dealer–citoyen : argent retiré des comptes/espèces, commission du vendeur, trésorerie de faction, contacts criminels, exposition, dépendance, santé et performance professionnelle.
- Recrutement des habitants vulnérables, conflits territoriaux, trafic de gros, blanchiment, corruption, raids et réponse judiciaire différenciée.
- Monitoring criminel plein écran avec factions, marchés, transactions, opérations et influence territoriale. Les données non détectées sont explicitement présentées comme omniscience de simulation, distincte du savoir policier.
- Endpoint détaillé `GET /api/crime/factions/{id}`, domaine `crime` enrichi dans le snapshot et le WebSocket, fiche citoyen enrichie.
- Historiques bornés : 5 000 transactions, 2 000 opérations et 120 jours de tendances criminelles.
- Sauvegarde stricte v14 comprenant factions, rôles, relations, marchés, transactions, dépendances, compteurs et générateur pseudo-aléatoire criminel.

## Migration depuis v0.12.0

Le schéma passe de 13 à 14. Les sauvegardes antérieures sont refusées : elles ne contiennent pas les factions typées, marchés, transactions, rôles, relations territoriales ni états individuels d’exposition.

## Nouveautés v0.12.0

- Population configurable de 20 à 1 000 citoyens ; capacité résidentielle et effectifs montent avec la ville sans multiplier les bâtiments à l’infini.
- Un seul emploi courant par citoyen ; toute autre candidature pendante est retirée à l’embauche. Plus de 30 intitulés couvrent industrie, bureaux, commerce, services, banque et accueil social.
- Banque incarnée : comptes courants, espèces, épargne, historique borné, score de crédit, prêts, intérêts, échéances, défauts et réserves bancaires. Salaires, achats, loyers, transports, communications et sanctions passent par un registre commun.
- Précarité matérielle : insécurité alimentaire, impayés, statut sans-abri, refuge municipal, repli au parc si le refuge est plein et retour conditionnel vers un logement.
- Organisations mafieuses persistantes avec membres, chef, territoire, trésorerie, notoriété et pression policière ; vols, braquages, extorsions, enlèvements et rançons produisent incidents, enquêtes et peines proportionnées.
- Les citoyens visés par une interdiction peuvent tenter de la contourner selon leur personnalité. Une réussite marque la peine violée et crée un nouvel incident judiciaire.
- Implantation résidentielle moins régulière et carte rafraîchie : volumes, ombres, végétation, marquages de voirie et couleurs dédiées à la banque et au refuge.
- Indicateurs toujours limités à six cartes par vue, avec une catégorie Banque et des métriques de sans-abrisme/crime organisé.
- Sauvegarde stricte v13 incluant comptes, transactions, précarité, mafias, opérations, enlèvements, rançons et générateurs pseudo-aléatoires dédiés.

## Migration depuis v0.11.0

Le schéma passe de 12 à 13. Les anciennes sauvegardes sont refusées explicitement car elles ne contiennent pas les comptes bancaires, états de précarité ni organisations criminelles.

## Nouveautés v0.11.0

- Quatre quartiers persistants avec population, revenus, chômage, loyers, activité commerciale, criminalité, sécurité ressentie, couverture policière, accès aux soins et commerces, transport, pression des services et attractivité.
- Historique journalier borné à 90 jours et évolution différenciée de la sécurité et de l’attractivité.
- Patrouilles territoriales réellement conduites par des policiers citoyens ; l’unité disponible la plus proche est choisie lors d’un signalement.
- Les incidents répétés dégradent la sécurité locale. Éclairage, fréquentation, témoins et patrouilles modulent les opportunités criminelles sans jamais les supprimer.
- Les distances au commissariat, au centre médical et aux commerces influencent réellement réponse et accessibilité.
- Neuf cartes thématiques : revenus, chômage, criminalité, sécurité ressentie, réponse policière, accessibilité, loyers, santé et fréquentation commerciale.
- Fenêtre quartier avec tendances, incidents, population, entreprises, services, patrouilles et attractivité.
- Endpoints `GET /api/neighborhoods` et `GET /api/neighborhoods/{id}`, domaine WebSocket `neighborhoods` et filtre Quartiers.
- Sauvegarde stricte v12 incluant quartiers, historiques, affectations et générateur aléatoire territorial.

## Migration depuis v0.10.1

Le format de sauvegarde passe de 11 à 12. Les sauvegardes v11 et antérieures sont refusées explicitement, car elles ne contiennent ni découpage spatial, ni historiques locaux, ni file d’affectation des patrouilles.

## Nouveautés v0.10.1

- Quatre canaux persistants : appel téléphonique, SMS, e-mail et lettre, avec coûts, délais de livraison et délais de lecture distincts.
- Appels synchrones dépendant de la disponibilité réelle du destinataire et appels manqués explicitement enregistrés.
- Conversations, réponses automatiques bornées, tons amical, pratique, excuses, invitation ou conflictuel, avec conséquences sur les relations.
- Communications autonomes planifiées à quelques créneaux quotidiens par une file événementielle, sans balayage permanent de toute la population.
- Générateur aléatoire dédié et sauvegardé pour préserver le déterminisme sans perturber l’économie, la santé ou la justice.
- Commandes `GET /api/communications`, `GET /api/citizens/{id}/communications` et `POST /api/communications`, domaine WebSocket `communications`.
- Fenêtre de monitoring globale, onglet de composition/historique dans chaque fiche citoyen, indicateurs compacts et filtre du journal.
- Sauvegarde stricte v11 et historique global plafonné à 2 000 communications.

## Migration depuis v0.10.0

Le schéma de sauvegarde passe de 10 à 11 pour conserver les coordonnées, communications, fils, statuts, compteurs, file de livraison/lecture et état du générateur aléatoire dédié. Les sauvegardes v10 et antérieures sont refusées explicitement. La version applicative est v0.10.1 ; v0.11.0 reste réservée au prochain lot du manifeste.

## Nouveautés v0.10.0

- Dépôt de plainte persistant, enquête, revue du parquet, classement sans suite, poursuites, audience, verdict et peines structurées.
- Tribunal municipal avec juge et greffiers citoyens, capacité quotidienne, priorités et reports lorsque le service est sous-staffé.
- Centre de détention avec surveillants citoyens et suivi de capacité.
- Rappel judiciaire, amende, indemnisation, probation, travail d’intérêt général, interdiction de contact et détention courte ou longue.
- Conséquences réelles : paiement et indemnisation, stress, perte d’emploi en détention longue, déplacement alternatif, interactions bloquées et violation de probation.
- Fenêtre tribunal, fenêtre dossier avec chronologie complète, monitoring des institutions, fiche citoyen enrichie et filtre Justice.
- Endpoint `/api/justice`, domaine `justice` dans les snapshots/deltas et sauvegarde stricte v10.

## Migration depuis v0.9.0

Le format de sauvegarde passe de 9 à 10. Les sauvegardes v9 et antérieures sont refusées explicitement ; aucune migration approximative n’est appliquée. Sauvegardez ou archivez une ville v9 avant de démarrer cette version si vous souhaitez la conserver.

## Nouveautés v0.9.0

- Chaque résidence possède capacité, loyer, état, confort, propriétaire, disponibilité, proximité des services et sécurité locale.
- Cinq logements restent vacants à l'initialisation ; le choix compare revenu, taille, travail, relations, sécurité, trajet et confort.
- Budget commun, paiement du loyer, impayés, recherche, déménagement groupé, séparation explicite, nouveau foyer, cohabitation et relogement municipal temporaire.
- Tableau de bord résidentiel, fenêtre logement, fenêtre foyer, filtre Logement, endpoints `/api/housing` et `/api/households/{id}`, domaine WebSocket `housing`.
- Un délai de sept jours prévient les boucles et une alternative explicite précède toute éviction simplifiée.

## Interface et architecture maintenables

- Le panneau d’indicateurs est limité à six cartes visibles et neuf catégories navigables : synthèse, logement, économie, banque, santé, mobilité, social, quartiers et sécurité.
- Le frontend sépare désormais flux WebSocket, état des couches, catalogue de métriques, panneau de contrôle et inspecteurs spécialisés.
- Le backend sépare routes HTTP, transport WebSocket, calcul des métriques, présentateurs de monitoring et persistance atomique.
- Les fonctions pures de métriques, fusion de flux, URL WebSocket et état des couches disposent de tests dédiés.

## Nouveautés v0.8.0

### Santé individuelle

- État général, douleur, blessure légère ou grave, maladie bénigne ou sévère, incapacité temporaire, arrêt de travail, convalescence et guérison.
- Origines intégrées : bagarre ou agression, accident de circulation rare, fatigue, mauvaise nutrition, alcool, maladie et risque lié à l’âge.
- La mort reste volontairement désactivée dans cette version.

### Centre médical et secours

- Le Centre médical Saint-Roch possède huit lits, une capacité, une file de consultation et des délais dépendant du personnel réellement présent.
- Huit citoyens exercent comme médecins ou infirmiers en équipes 06:00–14:00 et 14:00–22:00.
- Deux ambulances nécessitent chacune deux soignants en service. Le véhicule se rend réellement auprès du patient, l’embarque et le transporte au centre médical.
- Une relève bornée par transport non urgent après 120 minutes et des durées maximales de consultation/hospitalisation empêchent les patients bloqués.

### Police, justice et preuve médicale

- Une personne gravement blessée ou malade ne peut pas être placée en cellule avant examen médical.
- La mesure policière devient un examen préalable et le patient est transféré vers le dispositif de soins.
- Un certificat médical n’est créé qu’après une consultation réelle ; sa fiabilité augmente la confiance de l’enquête.

### Monitoring

- Tableau de bord : urgences, file d’attente, lits occupés, soignants en service, ambulances disponibles et attente moyenne.
- Onglet Santé de la fiche citoyen avec douleur, gravité, incapacité, arrêt et historique cliquable.
- Fenêtre hospitalière avec personnel, capacité, patients, file, ambulances et niveau de service.
- Couches carte indépendantes : état de santé, urgences, ambulances et structures médicales.
- Filtre Santé du journal avec navigation vers citoyen, incident ou centre médical.
- Endpoint `GET /api/healthcare` et domaine `health` dans les instantanés et deltas WebSocket.

## Nouveautés v0.7.0

### Économie locale

- Chaque employeur possède une trésorerie, des recettes, une masse salariale, des coûts fixes, un résultat journalier, une capacité d'emploi et un niveau de service.
- Les entreprises privées peuvent devenir fragiles, déficitaires puis fermer ; les employeurs publics restent ouverts et reçoivent un financement public explicite.
- Les recettes commerciales proviennent des achats réels. Les autres activités privées génèrent une activité abstraite proportionnelle aux minutes de travail productives.
- Les bilans financiers et les mouvements de personnel sont conservés dans des historiques bornés.

### Marché du travail

- Chômage, recherche active, postes ouverts, candidatures, recrutement, refus, démission, changement d'emploi et licenciement.
- Les candidats comparent salaire, distance, horaire, satisfaction et adéquation au poste.
- Expérience, performance et personnalité influencent le score ; tous les tirages utilisent exclusivement le générateur pseudo-aléatoire déterministe du monde.
- Un délai minimal évite les changements d'emploi en boucle et les embauches quotidiennes sont plafonnées.

### Finances des foyers

- Revenus du travail, charges récurrentes, dépenses alimentaires et dépenses en biens sont attribués à chaque foyer.
- Budgets journaliers, découvert plafonné, dette et stress financier contraignent la consommation.
- Le stress financier augmente le risque de tensions domestiques sans rendre le conflit automatique.

### Monitoring et transport des données

- Tableau de bord : chômage, postes ouverts, entreprises déficitaires, salaire médian, revenu médian des foyers, embauches et licenciements du jour.
- Fiche citoyen : finances, stress, candidatures et historique professionnel.
- Fenêtre entreprise : trésorerie, coûts, résultat, service, capacité, postes ouverts et historiques.
- Journal filtrable « Économie » avec ouverture des citoyens et entreprises concernés.
- Le WebSocket envoie un instantané complet à la connexion puis des deltas dynamiques, sans retransmettre la carte statique à chaque cycle.

### Correctifs issus de l'audit technique

- La projection dynamique est isolée dans `snapshot.py` : les deltas ne calculent plus les cellules routières, arrêts ou lignes statiques.
- La fusion snapshot/delta est isolée et couverte par trois tests frontend.
- Vite et Vitest sont sur des versions corrigées ; `npm audit` ne signale aucune vulnérabilité.
- React, Pixi et le code applicatif sont répartis en chunks inférieurs à 500 kB.
- Les environnements Python et npm disposent désormais de locks reproductibles.

## Socle v0.6.0

### Actualisation et UI / UX

- Une fiche habitant n'est plus interrogée par deux composants en parallèle.
- Aucun appel périodique à `/api/citizens/{id}` lorsque la simulation est en pause.
- En pause, une fiche n'est réactualisée qu'à sa sélection ou après un pas manuel.
- Les bâtiments, véhicules et incidents utilisent une fenêtre complète cohérente avec la fiche habitant.
- Les panneaux de la carte restent à hauteur fixe et défilent indépendamment.
- Les bâtiments sont cliquables sur la carte.

### Travail

- Horaires, jours travaillés et équipes distinctes selon le métier.
- Trajet réel vers le lieu de travail.
- Présence effective et minutes travaillées.
- Salaire calculé selon le temps réellement effectué.
- Performance, satisfaction, shifts terminés et absences.
- Services dégradés lorsque le personnel nécessaire n'est pas présent.
- Fiche d'un lieu de travail avec employés, horaires, présence et performance.

### Police incarnée par les habitants

- Les policiers sont des habitants ordinaires avec domicile, foyer, relations, besoins, horaires et salaire.
- Deux équipes assurent une couverture de 06:00 à 22:00.
- Une patrouille nécessite deux agents réellement présents et en service.
- Les agents se déplacent dans leur véhicule d'intervention et restent consultables pendant la mission.
- Leur travail influence leurs besoins, leurs revenus et leur historique personnel.

### Conséquences des interventions

Selon les faits, l'état de la personne et son comportement, les agents peuvent appliquer :

- un rappel à la loi ;
- une mise en cellule temporaire ;
- un passage en cellule de dégrisement ;
- une garde à vue.

La mesure, sa durée, son motif, les agents et l'incident associé sont enregistrés dans la fiche de l'habitant.

### Courses et consommation

- Le Marché Central fournit de la nourriture et des biens de consommation courante.
- Chaque habitant possède des réserves domestiques simples.
- Les repas à domicile consomment les provisions.
- Les biens courants s'usent lentement.
- Les habitants se rendent réellement au marché lorsque leurs réserves deviennent faibles.
- Les achats dépendent de l'argent, du stock et de la présence d'employés.
- Le commerce possède stocks, recettes et niveau de service consultables.

## Rupture de compatibilité des sauvegardes

Le format passe à la version 9 et conserve tout l'état résidentiel et v0.8. La v0.9.0 accepte uniquement les sauvegardes v9 ; les formats 1 à 8 sont rejetés explicitement. Pour migrer une ancienne ville, il faut repartir d'une nouvelle génération.

Pour repartir proprement :

```bash
docker compose down -v
docker compose up --build
```

Le bouton **Réinitialiser** génère également une nouvelle ville.

## Lancement avec Docker

Prérequis : Docker et Docker Compose.

```bash
docker compose up --build
```

Ouvrir ensuite :

- interface : `http://localhost:5173`
- documentation API : `http://localhost:8000/docs`
- santé du backend : `http://localhost:8000/api/health`

## Lancement manuel

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\\Scripts\\activate
pip install -r requirements.lock
pip install -e . --no-deps
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

## Architecture

```text
city-simulator-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes.py
│   │   │   └── websocket.py
│   │   └── simulation/
│   │       ├── banking.py
│   │       ├── communication.py
│   │       ├── crime.py
│   │       ├── criminal_factions.py
│   │       ├── criminal_markets.py
│   │       ├── crime_monitoring.py
│   │       ├── economy.py
│   │       ├── snapshot.py
│   │       ├── health.py
│   │       ├── housing.py
│   │       ├── justice.py
│   │       ├── generator.py
│   │       ├── models.py
│   │       ├── metrics.py
│   │       ├── monitoring.py
│   │       ├── neighborhood.py
│   │       ├── persistence.py
│   │       ├── service.py
│   │       ├── social.py
│   │       ├── transport.py
│   │       ├── work.py
│   │       └── world.py
│   ├── tests/
│   └── requirements.lock
├── frontend/
│   └── src/
│       ├── components/
│       │   └── inspectors/
│       ├── hooks/
│       ├── map/
│       ├── monitoring/
│       ├── api.ts
│       ├── App.tsx
│       ├── stream.ts
│       └── styles.css
├── docker-compose.yml
├── CHANGELOG.md
└── VALIDATION.md
```

## API principale

```text
GET  /api/city
GET  /api/citizens/{id}
GET  /api/buildings/{id}
GET  /api/enterprises/{id}
GET  /api/economy
GET  /api/banking
GET  /api/crime
GET  /api/crime/factions/{id}
GET  /api/healthcare
GET  /api/housing
GET  /api/justice
GET  /api/households/{id}
GET  /api/vehicles/{id}
GET  /api/incidents/{id}
GET  /api/social/graph
GET  /api/investigations/{id}
GET  /api/cases/{id}
WS   /ws/city  (instantané complet initial, puis messages `city_delta`)

POST /api/simulation/pause
POST /api/simulation/resume
POST /api/simulation/speed
POST /api/simulation/step
POST /api/city/save
POST /api/city/load
POST /api/city/reset
```

## Modèle et limites assumées

- La justice reste institutionnelle mais simplifiée : pas d’appel, avocat, régime procédural détaillé ni droit pénal exhaustif.
- La capacité quotidienne du tribunal est agrégée et le parquet est représenté comme une étape, pas comme un agent autonome.
- Le parc ne modélise ni achat immobilier, prêt, fiscalité foncière, bail détaillé, travaux pilotés ni construction.
- Le loyer utilise un mois de 30 jours et le revenu mensuel est estimé depuis salaire et planning.
- La sécurité locale dérive des incidents récents ; la cohabitation ne fusionne pas les budgets.

- Le moteur backend reste la source de vérité ; le frontend ne recalcule aucune décision économique.
- Les montants restent des unités monétaires simulées : la banque modélise comptes, prêts et défauts, mais pas fiscalité, inflation, assurance-dépôts, marchés financiers ni insolvabilité institutionnelle.
- Hors commerces, la demande adressée aux entreprises est agrégée à partir du temps productif : il n'existe pas encore de chaîne d'approvisionnement interentreprises.
- Les entreprises publiques sont financées par la ville et ne ferment pas ; la dépense publique cumulée est visible dans les métriques.
- Les historiques financiers et professionnels sont limités à 30 entrées pour éviter une croissance mémoire illimitée.
- Le marché du travail est volontairement local : une candidature compare salaire, distance, horaires, satisfaction, expérience et adéquation, sans formation ni immigration.
- Le modèle médical est volontairement agrégé : pas de diagnostic clinique, médicament, spécialité, chirurgie, assurance ou protocole réel.
- La nuit, une urgence attend un équipage du matin ; au-delà de 120 minutes, un transport non urgent de secours évite le blocage.
- Les décès sont désactivés et les maladies graves restent rares.

## Tests

```bash
cd backend
pytest -q

cd ../frontend
npm ci
npm test
npm run build
```

La validation complète, y compris la simulation de 30 jours et le contrat WebSocket différentiel, est détaillée dans `VALIDATION.md`.
