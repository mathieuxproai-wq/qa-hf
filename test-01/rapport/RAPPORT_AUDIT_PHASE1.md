# RAPPORT D'AUDIT QA — Hyperframe Render (Phase 1)

> Appareil : Redmi 2510DRK44C, Android 17 (MIUI), GPU Adreno 830.
> Environnement QA : Alpine Linux (PRoot) + Shizuku (UID 2000).
> Package testé : `com.hyperframe.render` (app-debug.apk).
> Date : 2026-11-26.

## 1. Description de l'Application & Comportement à l'Usage
- **Ce que fait réellement l'application :** moteur de rendu vidéo **headless**. `MainActivity` (translucide, vide) démarre `HeadlessRenderService` (service foreground + notification + `PARTIAL_WAKE_LOCK` 240 min), crée un **`VirtualDisplay` privé 1280×720@60fps** (`FLAG_PRIVATE`), y affiche un **WebView** (Chrome 158) chargeant `assets/test.html`, et encode en continu via **MediaCodec matériel `c2.qti.avc.encoder`** → `hyperframe_poc.mp4` (MediaStore Downloads). Cycle : lancement → init encodeur → VirtualDisplay → Presentation WebView → muxer → `[STATS] Frames encodées`/s → arrêt propre sur intent. « L'écran se ferme instantanément » = comportement attendu (pas de crash, `isCrashing=false`).
- **Expérience CLI :** pilotage via `am startservice` (actions `com.hyperframe.render.action.LOAD_URL` / `.STOP`), logs `HyperframePoC` clairs/horodatés. **Friction** : pont CDP HTTP OK mais injection WebSocket **bloquée 403**.
- **Verdict Global : SUCCÈS PARTIEL** (rendu/encodeur/endurance parfaits ; automatisation CDP bloquée + mismatch framerate).

## 2. Tableau Récapitulatif des Tests

| Test | Statut | Métrique / Preuve clé |
| :--- | :--- | :--- |
| Installation & `VirtualDisplay` privé | OK | `dumpsys display` : `HyperframePoC-VirtualDisplay 1280x720 state ON FLAG_PRIVATE mHasContent=true` |
| Encodeur Matériel (`MediaCodec`) | OK | logcat `Encodeur matériel: c2.qti.avc.encoder` ; ffprobe `h264 High yuv420p 1280x720` |
| Pont CDP (`127.0.0.1:9222`) | WARN | HTTP `/json` OK (Chrome/158, CDP 1.3) ; WS `Handshake 403 Forbidden` (`--remote-allow-origins` manquant) |
| Rendu Écran Éteint (60s) | OK | Dozing : frames continuent ~54 fps (vs 120 allumé), **pas de throttle 1fps** |
| Survie Doze / Process Killers (3 min) | OK | `force-idle` 184s : PID 22903 vivant, 56 fps, PSS ~112 Mo stable, **0 LMKD/am_kill** |
| Intégrité `hyperframe_poc.mp4` | OK | ffprobe 1280×720 h264, 6.25s, 337 frames, 2.4 Mbps ; luminance ~30 % (non noir) |

## 3. Gros Problèmes à Corriger (Critiques / Bloquants)
1. **Injection CDP impossible (bloquant automatisation Phase 2).**
   ```
   Handshake status 403 Forbidden — Rejected an incoming WebSocket connection ...
   Use the command line flag --remote-allow-origins=*
   ```
   Fix : `WebView.setWebContentsDebuggingEnabled(true)` + flag `--remote-allow-origins=*`.
2. **Mismatch framerate réel/nominal.** ffprobe `r_frame_rate=120/1` vs `avg_frame_rate≈53.9`. Conteneur annonce 120 fps, débit réel ~54 fps. Fiabiliser les timestamps MediaMuxer.

## 4. Petits Problèmes & Points d'Amélioration (Mineurs)
- Action CLI d'arrêt non documentée : `-a STOP` échoue ; réelle = `com.hyperframe.render.action.STOP`.
- Fichiers `.pending` orphelins dans Downloads (muxer non finalisé si process tué brutalement). Nettoyage à prévoir.
- WebView non accéléré matériellement (`isHardwareAccelerated=false`, canvas 2D) : plafonne le GPU (Adreno 830 tient ~112 fps en WebGL).
- GMS rallume l'écran ~4 s après extinction (artefact environnement).
- Bon point : `[MUXER] Ancien fichier supprimé` au démarrage → l'app nettoie l'ancien fichier.

## 5. Audit des Flags & Restrictions Système Android 17
- **OOM Adj & Priorité :** actif `oom adj cur=50 set=50` (principal), `51` (WebView sandboxed), `curProcState=4` (FOREGROUND_SERVICE) → bien protégé.
- **Standby Bucket & Doze :** `get-standby-bucket` = `5` (brut, MIUI) ; **dans `deviceidle whitelist`** (`user,com.hyperframe.render,10539`) = exempt batterie. Sous `force-idle` : survit 3 min sans dégradation.
- **Flags WebView/Chromium :** renderer sandboxed (uid isolé), **pas de throttle rAF 1fps** écran éteint (VirtualDisplay découple du vsync physique), accélération matérielle WebView **désactivée**, `FLAG_NEVER_BLANK` sur le display privé.

## 6. Architecture Zero-Copy / Readback (analyse complémentaire)
- **Readback CPU supprimé par conception.** Aucune API de readback dans le bytecode : `glReadPixels`, `PixelCopy`, `ImageReader`, `getPixels`, `copyPixelsToBuffer`, `readIntoBuffer` → **0 occurrence**.
- **Chaîne zero-copy présente :** `MediaCodec.createInputSurface()` + `createVirtualDisplay()` + logs `"Pipeline zero-copy actif"`.
- Flux : `WebView (GPU) → SurfaceFlinger → Surface d'entrée MediaCodec (buffer GPU) → encodeur H.264 → MP4`. Les frames ne quittent jamais la RAM GPU → CPU ~3 %, 120 fps.
- **Audio :** non supporté (vidéo seule, 1 track). Ajout = 2ᵉ `addTrack` AAC + encodeur audio + sync A/V ; **n'affecte pas** le zero-copy vidéo (l'audio ne passe pas par le GPU).

## 7. Vitesse de Rendu (mesurée)
- Génération/encodage écran allumé : **120 fps** (2× temps réel), stable (120 frames/s pile).
- Écran éteint : ~54 fps. Résolution 1280×720, encodeur `c2.qti.avc.encoder` ~2.4 Mbps.