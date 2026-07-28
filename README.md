# City Simulator — v0.8.0 Santé, blessures et secours

Prototype web d'une ville persistante simulant 100 habitants, leurs déplacements, relations, conflits, emplois, santé, blessures, maladies, secours médicalisés, finances, incidents, interventions policières et premières procédures judiciaires.

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

Le format de sauvegarde passe à la version 8 et conserve dossiers médicaux, files, hospitalisations, ambulances, équipages, historiques, générateur santé, ainsi que tout l’état v0.7. La v0.8.0 accepte uniquement les sauvegardes créées par la v0.8.0 ; les formats 1 à 7 reçoivent une erreur explicite. Pour migrer une ancienne ville, il faut repartir d'une nouvelle génération.

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
│   │   └── simulation/
│   │       ├── economy.py
│   │       ├── snapshot.py
│   │       ├── health.py
│   │       ├── generator.py
│   │       ├── models.py
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
│       ├── map/
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
GET  /api/healthcare
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

- Le moteur backend reste la source de vérité ; le frontend ne recalcule aucune décision économique.
- Les montants sont des unités monétaires simulées et ne représentent ni fiscalité, ni inflation, ni crédit bancaire réel.
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
