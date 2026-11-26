# qa-hf / test-01 — Audit QA Phase 1 / Hyperframe Render

> Campagne **test-01** (2026-11-26).

Audit QA Phase 1 de l'application **`com.hyperframe.render`** (Hyperframe PoC, `app-debug.apk`).
Moteur de rendu vidéo headless : WebView → VirtualDisplay 1280×720 → MediaCodec matériel H.264 → MP4.

- **Appareil :** Redmi 2510DRK44C, Android 17 (MIUI), GPU Adreno 830.
- **Environnement QA :** Alpine Linux (PRoot) + Shizuku (UID 2000).
- **Date audit :** 2026-11-26.
- **Verdict :** SUCCÈS PARTIEL (cœur solide ; automatisation CDP bloquée + mismatch framerate).

## Contenu du dossier

### `rapport/`
- `RAPPORT_AUDIT_PHASE1.md` — rapport complet au format imposé (5 blocs A→E + analyse zero-copy/audio).

### `donnees/` (métriques brutes)
- `ffprobe_hyperframe_poc.txt` — analyse technique du MP4 généré.
- `logcat_hyperframe_poc.txt` — logs `HyperframePoC` (init, pipeline, STATS fps).
- `dumpsys_process.txt` / `dumpsys_process_actif.txt` — OOM adj / procState.
- `dumpsys_display.txt` — état du VirtualDisplay privé.
- `standby_bucket.txt` — App Standby Bucket.
- `deviceidle_whitelist.txt` — exemption batterie Doze.

### `ressources/`
- `scene_test.html` — scène embarquée (`assets/test.html`, canvas 2D 26 particules).
- `hyperframe_poc_sample.mp4` — clip finalisé (1280×720, H.264, ~6 s).
- `frame_10pct.png` / `frame_50pct.png` / `frame_90pct.png` — frames clés (rendu non noir).

### `scripts/` (outils QA réutilisables)
- `cdp_b.py` — client CDP (test pont 9222 + RTT).
- `doze_watch.sh` — surveillance survie PID / fps / mémoire sous Doze.
- `pull_mp4.sh` — récupération du MP4 depuis /sdcard vers le sandbox (chunks base64).

## Résultats clés (rappel)
| Test | Statut | Preuve |
| :--- | :--- | :--- |
| VirtualDisplay privé 1280×720 | OK | FLAG_PRIVATE, state ON |
| Encodeur matériel | OK | c2.qti.avc.encoder, h264 High yuv420p |
| Pont CDP 9222 | WARN | HTTP OK, WS 403 (pas de --remote-allow-origins) |
| Rendu écran éteint 60s | OK | ~54 fps, pas de throttle 1fps |
| Survie Doze 3 min | OK | PID vivant, 56 fps, 0 LMKD |
| Intégrité MP4 | OK | 1280×720, 6.25s, non noir |
| Zero-copy / readback | OK | 0 readback CPU, createInputSurface |
| Vitesse de rendu | 120 fps | 2× temps réel, écran allumé |

> ⚠ **Contre-vérification test-02** : le WS CDP réussit **sans header `Origin`** (101 + `Runtime.evaluate` OK, HUD lu en direct). Le 403 ne bloque que les clients présentant une origine navigateur → le point « Pont CDP 9222 » n'est **pas bloquant** pour l'automatisation native (pas besoin de `--remote-allow-origins=*`). Détails et scripts : [test-02](minis://shared/qa-hf/test-02/README.md). test-02 précise aussi : fps ignoré même à 30, résolution effective du canvas 426×240 (dpr=3), STOP par broadcast inopérant, fuite `.pending` reproduite.

## Commandes utiles
```sh
# Lancer / arrêter le rendu
android-shizuku-cli exec 'am start -n com.hyperframe.render/.MainActivity'
android-shizuku-cli exec 'am startservice -n com.hyperframe.render/.HeadlessRenderService -a com.hyperframe.render.action.STOP'

# Logs
android-shizuku-cli exec 'logcat -d -s HyperframePoC'

# Pont CDP
curl -s http://127.0.0.1:9222/json | jq .
```