# Validation de l'archive — v0.7.0

## Backend

- 38 tests automatisés réussis sous Python 3.12, sans avertissement.
- Génération déterministe vérifiée.
- Simulation continue de 30 jours avec 100 habitants vérifiée.
- Absence de trajet bloqué depuis plus de 12 heures et historiques financiers bornés à 30 entrées vérifiés.
- Sauvegarde v7 et reprise bit-à-bit déterministes vérifiées, y compris générateur aléatoire, candidatures, carrières et comptabilités.
- Rejet explicite des sauvegardes v1 à v6 vérifié.
- Recherche d'emploi, création de postes, candidatures, embauche et refus testés.
- Licenciements déficitaires, fermeture privée et maintien des employeurs publics testés.
- Aucun double versement de salaire sur une même journée vérifié.
- Budgets, découvert, dette et stress financier des foyers testés.
- Courses, stocks, réserves, recettes et affectation des flux entreprise/foyer testés.
- Équipages policiers composés de citoyens en service testés.
- API ville, économie, entreprise, bâtiment, citoyen, véhicule, incident, enquête et justice testée.
- WebSocket testé : instantané complet initial, delta dynamique ensuite, géométrie routière statique absente du delta et fermeture normale.
- Un test interdit explicitement l'appel aux sérialiseurs statiques lors de la construction d'un delta.
- L'environnement Python verrouillé correspond exactement à `requirements.lock` et `pip check` ne remonte aucune incohérence.

## Frontend

- `npm ci` exécuté à partir du verrouillage reproductible `package-lock.json`.
- 3 tests Vitest réussis pour la fusion snapshot/delta et la conservation des données statiques.
- `npm run build` réussi : contrôle TypeScript strict et build de production Vite.
- 466 modules transformés ; CSS 23,66 kB, application 72,91 kB, React 141,63 kB et Pixi 476,13 kB avant compression gzip.
- `npm audit` réussi avec zéro vulnérabilité connue.
- Fusion des messages WebSocket différentiels avec conservation de la carte et du réseau statiques côté client.
- Tableau de bord économique, fiche finances/emploi citoyen, fenêtre entreprise et filtre d'événements économiques compilés.
- Sélection d'entité protégée contre les réponses réseau obsolètes.
- Un seul polling de la fiche citoyen.
- Polling des fiches et du graphe social désactivé en pause ; rafraîchissement unique après un pas manuel.
- Fenêtres complètes pour habitants, bâtiments, véhicules et incidents.
- Carte à hauteur stable et panneaux indépendamment défilables.

## Commandes exécutées

```bash
cd backend
.venv/bin/pytest -q
python -m compileall -q app tests
.venv/bin/pip check

cd ../frontend
npm ci
npm test
npm run build
npm audit
```

Résultat backend : `38 passed`, aucun avertissement. Starlette utilise désormais `httpx2`.

Résultat frontend : `3 passed`, build réussi, zéro vulnérabilité npm et aucun chunk supérieur à 500 kB.

## Limites de l'environnement de validation

- Le navigateur intégré n'a pas pu démarrer à cause d'une erreur du bac à sable Windows (`helper_unknown_error`) après deux tentatives. Le contrôle visuel interactif n'a donc pas été effectué dans cette session.
- Les services locaux ont néanmoins répondu sur `/`, `/api/economy` et les tests d'API/WebSocket automatisés sont passés.
