# Validation de l'archive — v0.6.0

## Backend

- 29 tests automatisés réussis.
- Génération déterministe vérifiée.
- Simulation continue de 7 jours vérifiée.
- Simulation de calibration sur 30 jours exécutée.
- Sauvegarde et reprise déterministes vérifiées.
- Rejet explicite des sauvegardes v1 à v5 vérifié.
- Travail, présence et salaire effectif testés.
- Courses, stocks, réserves et recettes testés.
- Équipages policiers composés de citoyens en service testés.
- Conséquence policière et historique personnel testés.
- API bâtiment, citoyen, véhicule, incident, enquête et justice testée.
- Fermeture normale du WebSocket testée.

## Frontend

- Contrôle TypeScript strict exécuté avec des déclarations locales temporaires pour les dépendances externes.
- Sélection d'entité protégée contre les réponses réseau obsolètes.
- Un seul polling de la fiche citoyen.
- Polling des fiches et du graphe social désactivé en pause ; rafraîchissement unique après un pas manuel.
- Fenêtres complètes pour habitants, bâtiments, véhicules et incidents.
- Carte à hauteur stable et panneaux indépendamment défilables.

## Limite de l'environnement de génération

Le registre npm n'était pas joignable de façon exploitable dans l'environnement de génération. `npm install` n'a donc pas pu terminer et le build Vite complet n'a pas été exécuté ici. Le code applicatif TypeScript/TSX a néanmoins passé le contrôle strict avec des déclarations temporaires ; le build réel est effectué par `docker compose up --build` sur la machine cible.
