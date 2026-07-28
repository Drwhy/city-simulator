# Changelog

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
