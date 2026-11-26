# QA indépendant — com.hyperframe.render (v1.0-phase1)
**Auteur : Minis (session indépendante, sans consultation préalable de qa-hf ni du rapport AGENT_QA_AUDIT_PHASE1.md)**
Date : 2026-11-26 05:44–05:52 (GMT+3). Device : Redmi 2510DRK44C (annibale), Android 17 (SDK 37), Adreno 830.

## Méthode
1. Analyse statique : extraction `AndroidManifest.xml` (parseur AXML maison) + `assets/test.html` + chaînes des dex de l'app (classes2/3.dex) — **sans** se fier aux résultats antérieurs.
2. Tests dynamiques : démarrage à froid, protocole d'actions, cas d'erreur, kill brutal, sondes CDP, ffprobe du produit.

## Protocole reconstitué (statique)
- Actions : `com.hyperframe.render.action.{START, STOP, LOAD_URL}` — traitées dans `HeadlessRenderService.onStartCommand` (aucun receiver dans le manifest ; 8 receivers dynamiques observés sur le process).
- Extras : `url` (déf. `file:///android_asset/test.html`), `width` (1280), `height` (720), `fps` (60), bornes MAX/clamp.
- Sortie : MediaStore.Downloads → `hyperframe_poc.mp4` (ancien fichier supprimé au START ; `.pending-*` renommé à la finalisation).
- CDP : proxy TCP `127.0.0.1:9222` → socket unix `webview_devtools_remote_<pid>`.
- FGS `specialUse` ("Offscreen GPU Web Rendering"), WakeLock PARTIAL max 240 min, pas d'extra "duration" (rendu jusqu'à STOP).

## Résultats dynamiques (tous vérifiés par logs tag `HyperframePoC` + observations système)
| # | Test | Résultat |
|---|------|----------|
| 1 | Démarrage à froid via MainActivity | ✓ Service démarré via `startForegroundService`, exemption batterie déjà accordée, pipeline actif en ~0,3 s |
| 2 | MainActivity | `noHistory`+`excludeFromRecents` → disparaît des recents (comportement "se ferme" normal) |
| 3 | WebView | **`isHardwareAccelerated=false`** à l'exécution (manifest dit `hardwareAccelerated=true`) |
| 4 | fps configuré vs réel | **60 configurés → ~112-118 fps réels** ; 30 configurés → 120 fps réels. Non-respect complet (rAF au vsync device + frame keeper inopérant). VD déclarée 60 Hz par SurfaceFlinger mais vsync effectif ~120 Hz |
| 5 | Résolution effective | Canvas backing store = **426×240 (dpr=3)** en 1280×720 ; **213×120** en 640×360. Contenu upscalé → qualité ≠ résolution annoncée |
| 6 | START dupliqué (pipeline actif) | ✓ Ignoré proprement : "[PIPE] START ignoré : pipeline déjà actif" |
| 7 | STOP via `startService` | ✓ Takedown propre ~90 ms : EOS → muxer finalisé → MP4 dans Downloads → relays CDP fermés → VirtualDisplay détruite |
| 8 | STOP via `am broadcast` | ✗ **Aucun effet** (broadcast livré, result=0, encodeur continue) → chemin service obligatoire |
| 9 | LOAD_URL à chaud | ✓ Vérifié via CDP `/json/list` (titre passe à HOTLOAD-QA-OK immédiatement) |
| 10 | LOAD_URL URL invalide | ⚠ Loggé "URL chargée à chaud" mais **aucune remontée d'erreur** (pas d'onReceivedError) → page blanche enregistrée silencieusement |
| 11 | STOP/LOAD_URL à froid (idle) | ✓ Graceful : "Aucun pipeline actif… arrêt du service" / "LOAD_URL ignoré (aucune Presentation active)" — pas de crash |
| 12 | Kill brutal (`force-stop`) en cours de rendu | ✗ **Nouvel orphelin `.pending-*` (17,2 Mo)** non nettoyé au START suivant → accumulation (7 orphelins, ~361 Mo au total, dotfiles invisibles pour l'app) |
| 13 | Notification FGS | ✓ "Hyperframe PoC" présente pendant le rendu (bouton STOP non testé — nécessite interaction UI) |
| 14 | Proxy CDP cycle de vie | ✓ Actif pendant pipeline, fermé après STOP (connexion refusée) |

## CDP — point clé (différenciant)
- HTTP `/json/version` + `/json/list` : ✓ (Chrome/158, CDP 1.3, cible page 1280×720 `visible`).
- **WebSocket avec header `Origin` → 403 Forbidden** (WebView sans `--remote-allow-origins`).
- **WebSocket SANS header `Origin` → 101 + `Runtime.evaluate` fonctionnel** (HUD lu en direct : frames/fps/chrono/visibilityState).
- ⇒ **Le pilotage externe du WebView est POSSIBLE** pour un client natif (lecture HUD, JS eval, potentiellement screencast/CDP complet). Le 403 ne bloque que les clients présentant une origine navigateur.

## Produit final (ffprobe du rendu court par défaut)
h264 High 1280×720 yuv420p, 1126 frames, durée 9,528 s, **avg_frame_rate 118,2 fps** (vs 60 demandés), r_frame_rate nominal 120/1, 4,15 Mbps. Frame extraite : scène conforme (particules/anneaux/onde), HUD net, badge LIVE.

## Verdicts QA
1. **Bloquant pour la spéc** : fps non respecté (2× environ, indépendant de la config) → durée/bitrate imprévisibles.
2. **Bug de robustesse** : fuite `.pending` après kill (jamais nettoyés, invisibles MediaStore).
3. **Incohérence qualité** : résolution réelle du contenu = taille/dpr (426×240), pas 1280×720 ; message HTML "WebView hardware" trompeur (runtime = software).
4. **Sécurité/surface d'attaque** : `HeadlessRenderService` et `MainActivity` exported sans permission → n'importe quelle app peut lancer un rendu (coût CPU/IO/batterie) ou arrêter le service. À évaluer selon l'usage cible.
5. **Ergonomie protocole** : STOP par broadcast non supporté (piège documenté ici) ; pas d'extra duration ni de limite de taille (fichiers potentiellement énormes — un orphelin de 246 Mo observé).
6. **Non-bloquant /_surprise_** : l'automatisation externe marche sans Origin (contrairement à une conclusion "impossible" antérieure que je n'avais pas relue au moment du test).

## Limites de la session
- Bouton STOP de la notification non actionné (interaction UI requise).
- Tests écran éteint/Doze non rejoués (coût temporel ; l'app était exemptée battery, whitelist confirmée indépendamment : UID 10539).
- Transferts gros fichiers limités à ~2-3 Mo/chunk via base64 (contrainte MAX_ARG_STRLEN + JSON offload).
