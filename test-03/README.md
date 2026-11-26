# TEST-03 — Rendu en écran éteint (bloc C) + GPU

**Date** : 2026-11-26 ~06:04–06:09 · Agent : Minis (campagne indépendante test-02, même méthode : sans relecture préalable des résultats des autres agents sur ce bloc)

**Question** : en écran éteint, (1) le rendu produit-il une vraie vidéo exploitable ? (2) à quelles performances ? (3) le GPU fonctionne-t-il toujours ?

## Réponses en une ligne
1. **Oui** — `video/hf_ecran_eteint.mp4` : 11,8 s, h264 High 1280×720, 662 frames, md5 vérifié, contenu animé non noir, HUD « FPS: 55 » visible dans la vidéo.
2. **~54–56 fps réels** écran éteint (vs 120 écran allumé) ; rAF actif, `visibility=visible` (VirtualDisplay découplée) ; pas de throttle à 1 fps ni de pause.
3. **Oui** — compute Vulkan : 14,4 TFLOP/s écran éteint (−21 % vs 20,6 écran allumé) ; la baisse vient du gating display, pas du rendu. Le pipeline du PoC ne sollicite pas l'Adreno (canvas logiciel + encodeur HW dédié).

## Arborescence
- `rapport/RAPPORT_TEST03_ECRAN_ETEINT.md` — rapport complet (protocole réel, données, verdicts)
- `video/hf_ecran_eteint.mp4` — livrable (run 2, 100 % écran éteint)
- `donnees/` — sondes rAF/HUD off + on (t03_raf_*.txt), frames extraites 2s/6s/10s, mesures brutes (mesures_test03.txt)
- `scripts/` — `probe2.py` (sonde CDP framing robuste, 2 modes), `fetch_t03.py` (transfert base64 md5-vérifié)

## Points méthodo réutilisables
- **Éteindre l'écran fiablement : `input keyevent 223` (SLEEP)** — `26` (POWER) est une bascule et déclenche un re-réveil GMS <8 s.
- Le HUD de la scène (chrono ms) permet une mapping 1:1 temps vidéo ↔ état de la scène — preuve embarquée.
- Bench GPU pendant le rendu = isolation cause (display gating vs contention).

## Limites
Doze profond (bloc D) non rejoué ici. Run 1 (mixte, 9124 frames, 48,8 Mo) conservé sur device : `/sdcard/Download/hf_test03_full.mp4`.
