# test-04 — QA Phase 2 (API HTTP 8765 + Menu UI dashboard)

**Date** : 2026-11-26 09:56→10:04 · **Verdict** : SUCCÈS PARTIEL (orienté bon)
**Objet** : audit de `apk_cp3_final_ui.apk` (Phase 2 : serveur de contrôle HTTP `127.0.0.1:8765` Bearer + Menu UI « Tableau de bord » dans MainActivity), sur consigne `QA_REPORT_PHASE2.md` (fourni par le pilote).

## Résultats (5 blocs)
| Bloc | Verdict | Essentiel |
| :--- | :---: | :--- |
| 1 Install & Menu UI | OK | MainActivity persiste au 1er plan ; token UI = auth_token.txt, persiste entre redémarrages |
| 2 API HTTP & sécurité | WARN | 401 ✓ health ✓ latence 3,5-4 ms ✓ cycle+hot-load ✓ ; MAIS /load invalide silencieux + API morte après /stop |
| 3 Concurrence & anti-corruption | OK | Garde-fou 4 : STOP interne propre + redémarrage ; 2 MP4 valides (54,1 / 53,7 fps) ; 1 display à la fois |
| 4 Écran éteint 45 s | OK | 118 fps fin de run, MP4 71,3 fps moyen — 2× la Phase 1, pas de readback CPU |
| 5 Doze & mémoire | OK/WARN | Survit 2 min+ (8744 fr / 64,4 fps), PSS +11,6 Mo, 0 LMK ; force-idle retombé spontanément |

## 3 chantiers Phase 3 (détail dans le rapport §3)
1. Serveur HTTP permanent (indépendant du pipeline — actuellement il meurt à chaque `/stop`).
2. `/load` doit détecter l'échec (chrome-error silencieux aujourd'hui).
3. Cadence de sortie non déterministe (54→118 fps) à verrouiller/documenter + ne plus logger le token.

## Contenu
- `rapport/QA_REPORT_PHASE2.md` — rapport au format imposé (UX, tableau, gros/petits problèmes)
- `donnees/mesures_test04.txt` — métriques brutes (frames, ffprobe, meminfo, latences)
- `donnees/t04_ui_dashboard.png` — screencap (noir : écran éteint, preuve d'état)
- `scripts/scene/scene.html` — scène de test (title auto = `SCENE-T04-OK | <fps> | <WxH>`)
- `scripts/cdp_eval.py` — client CDP WS minimal **sans header Origin** (sinon 403), frames masquées
- `video/` — 5 MP4 md5-vérifiés (cycle2_hotload, concurrence_3/4, test4_ecran_eteint, test5_doze)

## Notes méthode
- API HTTP joignable **directement depuis le sandbox** (namespace réseau partagé) : `curl -H "Authorization: Bearer <token>" http://127.0.0.1:8765/...`.
- Après `/stop`, relancer le service : `am start-foreground-service -n com.hyperframe.render/.HeadlessRenderService` (sans extras = rendu asset par défaut ; avec `-a ...action.START --es url ... --ei width --ei height --ei fps` pour paramétrer).
- Transfert MP4 : `split -b 2000000 <file> /data/local/tmp/pfx_` (toybox : FILE puis PREFIX) → `base64` par chunk via CLI → concat → md5 device vs sandbox.
- Nom des MP4 finaux : `hyperframe_poc (N).mp4` (espace + parenthèses → quoter).
- Écran éteint : rendu/API/CDP/logcat/screencap OK ; uiautomator dump IMPOSSIBLE (idle state).
