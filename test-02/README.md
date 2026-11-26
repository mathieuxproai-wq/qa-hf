# qa-hf / test-02 — QA indépendant (contre-audit) / Hyperframe Render

> Campagne **test-02** (2026-11-26, 05:44–05:52 GMT+3). Auteur : Minis (session indépendante).
> Mené **sans consultation préalable** de test-01 ni du protocole source — comparaison faite **après** coup.

Package : `com.hyperframe.render` v1.0-phase1 (app-debug, versionCode 1). Device : Redmi 2510DRK44C, Android 17 (SDK 37), Adreno 830.

## Portée (différente de test-01)
- **Analyse statique complète** (manifest AXML parsé maison + chaînes dex classes2/3) → protocole reconstitué de façon indépendante.
- Tests dynamiques des **cas d'erreur et du protocole d'actions** (jamais couverts par test-01) : START dupliqué, STOP/LOAD_URL à froid, STOP par broadcast, LOAD_URL invalide, kill brutal, cycle de vie du proxy CDP, notification FGS.
- **Contre-vérification du point CDP** (divergence majeure avec test-01, voir ci-dessous).
- ffprobe indépendant + extraction de frames.
- Blocs C (écran éteint 60 s) et D (Doze 3 min) **non rejoués** : l'extinction d'écran verrouillerait le device (PIN) — à rejouer avec l'utilisateur présent. Les résultats de test-01 sur C/D restent la référence.

## Verdict : SUCCÈS PARTIEL — avec une correction importante sur le CDP

### Divergence clé avec test-01 : le pont CDP n'est PAS bloquant
| Connexion | test-01 | test-02 (vérifié) |
| :--- | :--- | :--- |
| HTTP `/json/version`, `/json/list` | OK | OK (Chrome/158, CDP 1.3) |
| WS avec header `Origin` | 403 Forbidden | **403 confirmé** |
| WS **sans** header `Origin` | — (non testé) | **101 + `Runtime.evaluate` fonctionnel** |

Le 403 ne s'applique qu'aux clients présentant une origine navigateur (protection anti-piratage de page). Un client natif (socket brut, `ws` Node sans `Origin`, etc.) se connecte et pilote le WebView : HUD lu en direct (frames/fps/chrono/visibilityState), JS eval. **L'automatisation Phase 2 est donc possible sans modifier l'app** (pas besoin de `--remote-allow-origins=*`). Scripts : `scripts/ws_test.py`, `scripts/ws_live.py`.

### Résultats test-02 (tous vérifiés via logs `HyperframePoC` + observations système)
| # | Test | Statut | Preuve |
| :--- | :--- | :--- | :--- |
| 1 | Démarrage à froid MainActivity→Service | OK | `[MAIN] …startForegroundService, url=file:///android_asset/test.html`, pipeline actif < 0,3 s |
| 2 | fps configuré vs réel | **KO** | 60→**112-118 fps réels** ; 30→**120 fps réels** (`[STATS]` +120/s constant). Frame keeper (16 ms/33 ms) inopérant, rAF suit le vsync device |
| 3 | Résolution effective du contenu | **WARN** | canvas backing **426×240 (dpr=3)** en 1280×720 ; **213×120** en 640×360 → contenu upscalé, la "résolution" n'est que le conteneur |
| 4 | START dupliqué (pipeline actif) | OK | `[PIPE] START ignoré : pipeline déjà actif` |
| 5 | STOP via `startService` | OK | takedown ~90 ms : EOS → muxer finalisé → MP4 → relays CDP fermés → VD détruite |
| 6 | STOP via `am broadcast` (même action complète) | **KO (attendu)** | broadcast livré (`result=0`), **aucun effet** — pas de receiver ; chemin service obligatoire |
| 7 | LOAD_URL à chaud | OK | vérifié via CDP `/json/list` : titre change immédiatement |
| 8 | LOAD_URL URL invalide | **WARN** | "URL chargée à chaud" loggé, **aucune remontée d'erreur** (pas d'`onReceivedError`) → page blanche enregistrée |
| 9 | STOP/LOAD_URL à froid (idle) | OK | graceful : "Aucun pipeline actif… arrêt du service" / "LOAD_URL ignoré" — pas de crash |
| 10 | Kill brutal (`force-stop`) en rendu | **KO** | nouvel orphelin `.pending-*` (17,2 Mo) **non nettoyé** au START suivant ; 7 orphelins cumulés ≈ 361 Mo, dotfiles invisibles pour l'app |
| 11 | Notification FGS | OK | "Hyperframe PoC" présente (bouton STOP non actionné — interaction UI requise) |
| 12 | Cycle de vie proxy CDP | OK | actif pendant pipeline, **fermé après STOP** (connexion refusée) |
| 13 | WebView accélération | WARN | `isHardwareAccelerated=false` à l'exécution malgré `hardwareAccelerated=true` au manifest ; message HTML "WebView hardware" trompeur |
| 14 | Standby bucket / whitelist | OK | bucket=5 (brut), `user,com.hyperframe.render,10539` (croisé avec test-01) |

### Produit final (ffprobe, rendu court par défaut 1280×720@60)
`h264 High 1280×720 yuv420p` — 1126 frames / 9,528 s → **avg_frame_rate 118,2 fps** (60 demandés), r_frame_rate nominal 120/1, 4,15 Mbps. Frame extraite : scène conforme, HUD net (texte DOM à 3×), non noir.

## Ajouts au registre des problèmes
1. (MAJEUR) **fps complètement ignoré** : ce n'est pas un simple mismatch de conteneur — la config 30/60 ne throttle rien. Fix : cadencer la capture (ex. `Choreographer.postFrameCallback` avec saut de frames, ou `VirtualDisplay.setRenderMode`/surface rate) et écrire des timestamps cohérents.
2. (MAJEUR) **Fuite `.pending` après kill** : le cleanup ne vise que `_display_name = hyperframe_poc.mp4` ; les `.pending-<id>-…` (dotfiles) ne sont jamais supprimés. Fix : requête sur le préfixe `is_pending=1` + `relative_path=Download`.
3. (SECURITÉ, à arbitrer) `HeadlessRenderService` et `MainActivity` **exported sans permission** → toute app du device peut lancer/arrêter des rendus (coût CPU/IO/batterie, écriture Downloads). Ajouter `android:permission` ou `exported=false` si usage interne uniquement.
4. (MINEUR) Pas de gestion d'erreur de chargement (URL invalide silencieuse).
5. (MINEUR) Pas d'extra `duration` ni limite de taille : fichiers potentiellement énormes (orphelin de 246 Mo observé dans test-01, cohérent avec ce défaut).
6. (INFO) Texte marketing dans `test.html` ("Rendu GPU zero-copy · WebView hardware") ≠ réalité runtime.

## Croisement avec test-01
- **Confirmations indépendantes** : VD privée 1280×720, encodeur `c2.qti.avc.encoder`, logs clairs, isHardwareAccelerated=false, orphelins `.pending`, suppression de l'ancien fichier au START, bucket/whitelist.
- **Corrections** : CDP non bloquant (voir tableau ci-dessus) ; action STOP = `startService` obligatoire (broadcast inopérant même avec le nom complet d'action).
- **Nouveautés test-02** : fps ignoré même à 30 ; résolution effective 426×240/213×120 ; cas d'erreur et kill testés ; cycle de vie CDP ; surface exported.
- test-01 reste la référence pour les blocs C (écran éteint) et D (Doze/LMKD), non rejoués ici (verrouillage device).
