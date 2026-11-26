# qa-hf — Dossiers de référence QA / Hyperframe Render

Chaque sous-dossier = une campagne de test numérotée.

| Dossier | Description | Verdict |
| :--- | :--- | :--- |
| [test-01](minis://shared/qa-hf/test-01/README.md) | Audit QA Phase 1 (5 blocs A→E + zero-copy/audio) — 2026-11-26 | SUCCÈS PARTIEL |
| [test-02](minis://shared/qa-hf/test-02/README.md) | QA indépendant (contre-audit) : analyse statique protocole, cas d'erreur, kill, CDP WS sans Origin → automatisation possible — 2026-11-26 | SUCCÈS PARTIEL |
| [test-03](minis://shared/qa-hf/test-03/README.md) | Bloc C rejoué indépendamment : rendu écran éteint → vidéo réelle 56,05 fps + GPU vérifié (−21 %, gating display) — 2026-11-26 | SUCCÈS |

Voir `test-01/README.md`, `test-02/README.md` et `test-03/README.md` pour le détail et les métriques.
⚠ Correction croisée : le point « Pont CDP 403 » de test-01 est affiné par test-02 —
le handshake WS réussit sans header `Origin` (101 + `Runtime.evaluate` fonctionnel).