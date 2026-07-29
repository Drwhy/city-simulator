# Validation — v0.13.0

## Résultats

- Backend : 89 tests réussis sous Python 3.12, dont 6 scénarios systémiques v0.13.0.
- Frontend : 16 tests Vitest dans 7 fichiers.
- TypeScript strict et build Vite de production réussis.
- Persistance v14 : export/import strictement identique après 900 minutes de simulation criminelle.
- Déterminisme : deux mondes de même graine produisent un monitoring criminel identique.
- Capacité : initialisation validée à 5 000 citoyens, 16 factions et au moins 32 marchés.
- Bornes validées : 5 000 transactions, 2 000 opérations, 120 jours d’historique.
- Compatibilité : tous les scénarios historiques économie, banque, logement, santé, communications, quartiers, police et justice restent verts.

## Commandes de validation

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app tests
.venv/bin/pip check

cd ../frontend
npm ci
npm test -- --run
npm run build
npm audit --audit-level=high

cd ..
git diff --check
```

## Lancement

```bash
# Population par défaut : 100
CITYSIM_CITIZEN_COUNT=1000 docker compose up --build

# Charge maximale validée
CITYSIM_CITIZEN_COUNT=5000 docker compose up --build
```

Frontend : `http://localhost:5173` — API : `http://localhost:8000` — WebSocket : `ws://localhost:5173/ws/city`.

## Limites de validation

- Aucun collecteur de couverture Python/Vitest n’est installé ; aucun pourcentage non mesuré n’est annoncé. La couverture fonctionnelle est maintenue par 105 tests au total.
- Le navigateur intégré reste indisponible à cause de `helper_unknown_error`; la compilation valide les contrats et styles, mais une inspection visuelle interactive locale reste recommandée.
- À 5 000 citoyens, l’initialisation mesurée est d’environ 3 secondes, consomme environ 325 Mo et le snapshot initial JSON approche 3 Mo ; la cadence des deltas monte automatiquement à 2 secondes.
