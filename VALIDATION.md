# Validation de l'archive — v0.8.0

## Backend

- 44 tests automatisés réussis sous Python 3.12.
- Compilation de `app` et `tests` réussie ; `pip check` ne remonte aucune incohérence.
- Simulation continue de 30 jours avec 100 habitants vérifiée, en conservant les critères économiques v0.7.
- Blessure lors d'une bagarre/agression, douleur, incapacité et arrêt de travail vérifiés.
- Ambulance bloquée sans équipage puis départ avec deux soignants citoyens en service vérifié.
- Déplacement routier, embarquement et arrivée physique du patient au centre médical vérifiés.
- Délai plus long avec un seul soignant qu'avec quatre soignants vérifié.
- Consultation réelle, certificat médical et hausse de confiance de l'enquête vérifiés.
- Aucun dossier âgé de plus de 12 heures ne reste en attente, en transport ou en consultation après un scénario de 48 heures.
- Sauvegarde stricte v8 et reprise des dossiers, états citoyens, files, lits, ambulances, équipages, historiques et deux générateurs aléatoires vérifiées.
- Endpoint `/api/healthcare`, fiche hôpital, métriques de snapshot et domaine santé des deltas WebSocket vérifiés.
- Les 38 tests hérités de la v0.7 restent réussis, y compris salaires, économie, 7/30 jours, police, justice, API et WebSocket.

## Frontend

- 3 tests Vitest réussis pour la fusion snapshot/delta et la conservation des données statiques.
- `npm run build` réussi : contrôle TypeScript et build Vite de production.
- 466 modules transformés ; CSS 23,90 kB, application 79,99 kB, React 141,63 kB et Pixi 476,13 kB avant gzip.
- Aucun chunk ne dépasse 500 kB.
- `npm audit --audit-level=high` : zéro vulnérabilité.
- Tableau de bord santé, onglet Santé, fiche ambulance, fenêtre hospitalière, filtre Santé et quatre couches cartographiques compilés.

## Contrôles HTTP

- `GET /api/health` : 200.
- `GET /api/city` : snapshot de 100 habitants avec domaine `health`.
- `GET /api/healthcare` : Centre médical Saint-Roch, huit lits et deux ambulances disponibles au démarrage.
- Frontend Vite : 200 sur `http://127.0.0.1:5173`.

## Commandes exécutées

```bash
cd backend
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q app tests
.venv/bin/pip check

cd ../frontend
npm test
npm run build
npm audit --audit-level=high

cd ..
git diff --check
```

Résultat backend : `44 passed`.

Résultat frontend : `3 passed`, build réussi, zéro vulnérabilité npm et aucun chunk supérieur à 500 kB.

## Limite de l'environnement de validation

- Le navigateur intégré n'a pas pu établir sa connexion à cause de l'erreur du bac à sable Windows `helper_unknown_error`, malgré deux tentatives. Le contrôle visuel interactif n'a donc pas été effectué dans cette session.
- Les contrôles TypeScript, Vite, API, WebSocket et HTTP locaux sont tous réussis ; cette limite concerne uniquement l'inspection visuelle manuelle du rendu.