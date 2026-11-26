# RAPPORT TEST-03 — Rendu en écran éteint : vidéo, performances, GPU

**Date** : 2026-11-26, 06:04–06:09 (+03:00) · **Campagne QA indépendante** (méthode test-02 : protocole suivi sans relecture préalable des conclusions des autres agents sur ce bloc).
**Périmètre** : bloc C du protocole (écran éteint) + vérification GPU. Les blocs A/B/E (déjà couverts par test-02) ne sont pas rejoués sauf nécessité.

## 1. Contexte d'exécution

| Paramètre | Valeur |
|---|---|
| Device | Redmi 2510DRK44C, Android 17 (SDK 37), Adreno 830 |
| App | com.hyperframe.render v1.0-phase1 (debuggable) |
| Batterie | 40 % → 39 % (décharge, non branché) |
| Température | 38,3 °C → 39,5 °C |
| Orphelins `.pending` au début | 7 (inchangés — aucun nouveau après ce test : les 2 STOP ont été propres) |

**Particularité du protocole réel** : l'écran s'est éteint par **timeout naturel** juste avant le premier rendu → le run 1 a démarré **déjà écran éteint**. Cela a fourni un segment « off » de ~100 s sans manipulation. Un run 2 dédié 100 % écran éteint a ensuite été réalisé proprement.

## 2. Outils d'extinction/réveil — résultat méthodologique important

| Méthode | Effet |
|---|---|
| `input keyevent 26` (POWER) | **Bascule** on↔off + **re-réveil observé en <8 s** (artefact GMS connu de test-01, probablement lié à l'extinction par bouton) |
| `input keyevent 223` (KEYCODE_SLEEP) | Extinction **fiable et stable** : Dozing maintenu pendant tout le run 2 (~15 s), **aucun re-réveil** |
| `input keyevent 224` (WAKEUP) | Réveil fiable (lockscreen affichée — ne perturbe pas le pipeline VirtualDisplay) |

→ Pour les futurs tests : **utiliser 223 pour éteindre, jamais 26** (ou assumer la bascule). Note : l'écran éteint verrouille le device (PIN) — le test laisse le téléphone en veille verrouillée, comportement attendu.

## 3. Run 1 — rendu mixte (écran éteint → allumé), 9124 frames

Démarrage à froid ~06:05:07 (écran **déjà Dozing**) → rendu à ~55 fps d'emblée.
Réveil `224` à 06:06:42 → 120 fps immédiat. Re-extinction `26` à 06:07:13 → annulée (<8 s). STOP `start-foreground-service -a com.hyperframe.render.action.STOP` → **EOS frames totales=9124**, finalisation propre en <50 ms.

**Encodage mesuré par [STATS] (Δframes/Δt)** :
- Écran éteint (06:06:22→06:06:33) : +120 frames / 2,14–2,23 s = **53,8–56,1 fps**
- Écran allumé (06:06:45→06:06:50) : +120 / 1,0 s = **120,4 fps** (creux isolé à 102,7 fps pendant le bench GPU concurrent — normal)
- Fichier : 48,8 Mo, préservé sur device : `/sdcard/Download/hf_test03_full.mp4` (non transféré, trop lourd ; timeline = ~55 fps jusqu'à frame ≈ 5,5k puis 120 fps)

**Sondes CDP écran éteint** (WS sans header Origin — 101 OK, reconfirmé) :
```
HUD: frames 4173→4341 en 3,0 s (56,0 fps), fps affiché 54→56
rAF direct (compteur 3 s) : 53,3 fps
visibility="visible", hidden=false  → pas de pause rAF
```
**Sondes CDP écran allumé** : HUD fps 120, frames +360/3,0 s = 120,0 fps, rAF mesuré **240/s** (2× le compteur HUD — hypothèse non tranchée : double source vsync display/VD ; à réexaminer en Phase 2).

## 4. Run 2 — rendu 100 % écran éteint (livrable)

`223` → Dozing vérifié → `force-stop` → cold start → 12 s → STOP.
- STATS dès les premières lignes : 360 @06:08:05,9 ; 480 @06:08:08,1 (**54,6 fps**) ; 600 @06:08:10,2 (**56,1 fps**) — cadence « écran éteint » du premier au dernier échantillon, `mWakefulness=Dozing` vérifié avant ET après.
- EOS **662 frames**, finalisation propre, 3 662 034 octets.

**ffprobe** (transfert base64 3 chunks, **md5 vérifié** `5088c3c2…a421` = md5 device) :
```
h264 High 1280x720 yuv420p · r_frame_rate=120/1 (nominal) · avg_frame_rate=56,05 (réel)
nb_frames=662 · duration=11,81 s · 2,48 Mbps
```
**Livrable** : `video/hf_ecran_eteint.mp4` (+ frames 2s/6s/10s dans `donnees/`).
**Frame t=6 s** : contenu vivant (particules/anneaux nets), HUD « Frames: 339 · **FPS: 55** · LIVE · Chrono: 5968 ms » → mapping chrono↔temps vidéo 1:1, le HUD documente lui-même l'état écran éteint dans la vidéo. Aucune frame noire, aucun gel.

## 5. GPU en écran éteint

Bench Vulkan compute (Turnip 27.0.0-devel, Adreno 830, FMA 1M threads) :

| État | ms/dispatch | GFLOP/s |
|---|---|---|
| Écran allumé, sans rendu | 5,9 | 18 239 |
| **Écran éteint, rendu actif** | **7,4** | **14 417 (−21 %)** |
| Écran allumé, rendu actif | 5,2 | 20 622 |

**Conclusions GPU** :
1. Le GPU **fonctionne correctement écran éteint** : compute complet, driver OK, résultat cohérent.
2. La baisse (−21 à −30 %) est liée à l'**état display** (gating / downclock du GPU quand l'écran dort), **pas** à la charge du rendu (le bench écran allumé + rendu actif est même le plus rapide : 20,6 TFLOP/s).
3. Rappel structurel : le pipeline du PoC n'utilise **pas** l'Adreno pour le canvas (WebView `isHardwareAccelerated=false`, rendu logiciel) ; l'encodeur est un bloc matériel dédié (c2.qti.avc.encoder). Le GPU n'est donc pas dans le chemin critique — sa santé reste vérifiable/comfirmée indépendamment comme ci-dessus.

## 6. Verdict bloc C (écran éteint)

| Test | Résultat |
|---|---|
| Le rendu survit et produit une vraie vidéo | ✅ (662 frames nettes, non noires, animées) |
| fps réel écran éteint | **~54–56 fps** (vs 120 écran allumé — réduction ≈ ×2,2, PAS 1 fps ni pause) |
| `visibility`/rAF | reste "visible" / actif (VirtualDisplay découplée de l'écran physique) |
| GPU | ✅ fonctionnel, −21 % (gating display) |
| Takedown propre écran éteint | ✅ EOS + finalisation <50 ms, zéro nouvel orphelin |
| Vidéo livrable | ✅ `hf_ecran_eteint.mp4` 11,8 s, 56,05 fps réel, md5 vérifié |

Concordance avec le chiffre rapporté par test-01 (~54 fps) : **confirmée indépendamment**.

## 7. Limites
- Doze profond non testé (bloc D — `dumpsys device-idle force-idle` rejouable plus tard).
- Le run 1 n'a pas pu être repassé en écran éteint en fin (artefact re-réveil GMS avec keyevent 26) — sans impact grâce au run 2 dédié.
- Batterie sur décharge (39 %) : perf sous faible charge non explorée.
