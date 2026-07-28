# City Simulator — v0.6.0 Travail, consommation et police citoyenne

Prototype web d'une ville persistante simulant 100 habitants, leurs déplacements, relations, conflits, emplois, consommation, incidents, interventions policières et premières procédures judiciaires.

## Nouveautés v0.6.0

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

La structure de simulation a beaucoup évolué. La v0.6.0 accepte uniquement les sauvegardes créées par la v0.6.0. Une ancienne sauvegarde reçoit volontairement une erreur explicite au lieu d'une migration approximative.

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
pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```text
city-simulator-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── simulation/
│   │       ├── generator.py
│   │       ├── models.py
│   │       ├── service.py
│   │       ├── social.py
│   │       ├── transport.py
│   │       ├── work.py
│   │       └── world.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       ├── map/
│       ├── api.ts
│       ├── App.tsx
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
GET  /api/vehicles/{id}
GET  /api/incidents/{id}
GET  /api/social/graph
GET  /api/investigations/{id}
GET  /api/cases/{id}
WS   /ws/city

POST /api/simulation/pause
POST /api/simulation/resume
POST /api/simulation/speed
POST /api/simulation/step
POST /api/city/save
POST /api/city/load
POST /api/city/reset
```

## Tests

```bash
cd backend
pytest -q
```

La validation de cette archive est détaillée dans `VALIDATION.md`.
