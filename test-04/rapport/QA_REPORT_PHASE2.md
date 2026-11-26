# QA REPORT — PHASE 2 (com.hyperframe.render)

**Campagne** : test-04 · **Date** : 2026-11-26, 09:56 → 10:04 (UTC+3)
**Device** : Redmi 2510DRK44C (annibale) · Android 17 (SDK 37) · Adreno 830 · MIUI
**APK audité** : `apk_cp3_final_ui.apk` (3 877 750 o, 09:21) installé à 09:22:43 — `versionName=1.0-phase1`
**Environnement d'audit** : Alpine proot (sandbox Minis) + Shizuku (`android-shizuku-cli exec` ≙ `rish`)
**État écran pendant la campagne** : **ÉTEINT (Dozing)** du début à la fin — le rendu, l'API HTTP et le CDP ont été audités dans cet état (prouvé non bloquant en test-03).

Objet de la Phase 2 : serveur de contrôle HTTP local `127.0.0.1:8765` (auth Bearer) + Menu UI « Tableau de bord » dans `MainActivity`.

---

## 1. Description de l'expérience utilisateur & du Menu UI

### Ce qui a été observé directement
- **`MainActivity` ne se ferme plus** : relancée à froid via `am start`, elle reste au premier plan (`mFocusedApp=ActivityRecord{… com.hyperframe.render/.MainActivity}`) et logge `[MAIN] Tableau de bord affiché`. La task est `translucent=true sz=1` — le dashboard est rendu dans une fenêtre translucide au-dessus du wallpaper, comme en Phase 1, mais cette fois avec un contenu plein écran utile.
- **Cycle de vie service ↔ UI cohérent** : l'arrêt HTTP (`/stop`) coupe le service ; un redémarrage par l'UI ou par `am` relance service + rendu + API en ~1 s. Le token affiché dans l'UI (bouton « COPIER TOKEN ») correspond **exactement** à `files/auth_token.txt` (48 hex) et **persiste entre les redémarrages du service** (chargé depuis le fichier, pas régénéré) — bon pour les agents externes.
- **Le rendu par défaut est automatique** : tout démarrage du service (même `am start-foreground-service` sans extras) lance immédiatement un rendu asset 1280×720@60. Il n'existe pas d'état « service idle sans rendu ».
- uiautomator dump a échoué (« could not get idle state ») et le screencap renvoie une image noire : écran éteint + compteur de frames qui se rafraîchit. L'évaluation fine du rendu visuel du dashboard (couleurs, focus states) n'a donc pas pu être faite en live ; elle s'appuie sur la capture fournie par le pilote (30401.jpg) et sur les traces.

### Lecture ergonomique (capture pilote + comportement mesuré)
| Élément UI | Comportement observé | Verdict |
| :--- | :--- | :--- |
| État « ARRÊTÉ » + Frames encodées / Dernier MP4 / URL en cours | Reflète `/status` (`running`, `frames_encoded`, output_file, url) ; les valeurs suivent le pipeline même quand l'UI est en arrière-plan | OK |
| CDP 127.0.0.1:9222 affiché | Proxy vivant pendant le rendu, mort après `/stop` — l'UI ne précise pas qu'il dépend du rendu | WARN (pédagogie) |
| API HTTP 127.0.0.1:8765 affichée | Vraie API, latence ~3,5 ms, auth Bearer effective — mais **absente quand le service est arrêté** | WARN (voir §3.1) |
| Jeton Bearer + COPIER TOKEN | Token stable, copiable ; l'app le logge aussi en clair dans logcat (`[HTTP] Token=…`) | WARN (voir §4.3) |
| URL à rendre préremplie `http://127.0.0.1:3000` | Invite l'utilisateur à CHARGER URL sans serveur derrière → chrome-error silencieux (piège §3.2) | KO ergonomie |
| TEST ASSET (file:///android_asset/test.html) | Fonctionne (hot-load vers asset vérifié) | OK |
| Résolution du VirtualDisplay 1280×720 / 1920×1080 | Les deux valeurs fonctionnent réellement (création VD 1280×720 id 77 puis 1920×1080 id 78 observée dans dumpsys) | OK |
| DÉMARRER / CHARGER URL / ARRÊTER / PERMISSIONS & BATTERIE | DÉMARRER et ARRÊTER équivalents aux endpoints `/start` `/stop` ; CHARGER URL hérite du piège silencieux | OK/WARN |

**Pilotage HTTP vs CLI** : les deux chemins coexistent sans conflit (l'UI et `am`/HTTP aboutissent aux mêmes `ServiceRecord`). Pour un agent externe, le flux réaliste est : `am start-foreground-service` (ou un tap UI) **puis** tout le reste en `curl`. La spec `hf-user/SPEC_SERVICE_HYPERFRAME.md` (« n'importe quel agent fait juste du curl ») **n'est pas encore tenable** : après chaque `/stop`, l'API disparaît et il faut re-démarrer le service par un canal non-HTTP.

---

## 2. Tableau de validation des 5 blocs

| # | Bloc | Verdict | Métriques clés |
| :--- | :--- | :---: | :--- |
| 1 | Installation & démarrage via Menu UI | **OK** | Install 09:22:43 ; MainActivity persiste au 1er plan (mFocusedApp) ; token UI = auth_token.txt (48 hex), persiste entre redémarrages ; `versionName` non incrémenté (cosmétique) |
| 2 | API HTTP 8765 & sécurité | **WARN** | 401 sans Bearer sur `/status` ✓ ; `/health` 200 sans auth (liveness, conforme) ✓ ; latence `/status` **3,49–3,95 ms**, `/health` 4,0 ms ✓ ; cycle complet start→load→status→stop ✓ ; hot-load sandbox→WebView ✓ (frames continuent 708→710, CDP title `SCENE-T04-OK`) ; `/load` URL morte = 200 silencieux ✗ ; **API introuvable après `/stop`** ✗ |
| 3 | Concurrence & anti-corruption MP4 | **OK** | 2× `POST /start` à 3 s : garde-fou 4 = STOP interne **propre** puis redémarrage (log §3.3) ; MP4 (3) = 161 fr / 2,976 s / **54,1 fps** 1280×720 ✓ moov ; MP4 (4) = 511 fr / 9,517 s / **53,7 fps** 1920×1080 ✓ moov ; md5 device=sandbox ✓ ; 1 seul VirtualDisplay à la fois (id 77 → id 78), 0 après stop ✓ |
| 4 | Non-régression écran éteint (keyevent 223) + UI en arrière-plan | **OK** | 45 s+ écran éteint : rendu non gelé (HUD rAF CDP **120 fps**, frames 156→3427→4849) ; débit fin de run **118 fps** (708 fr/6 s) ; MP4 final **4855 fr / 68,125 s = 71,3 fps moyen** (montée 55→118 pendant le run) vs 56,05 fps Phase 1 → **pas de régression, 2× mieux** ; pas de readback CPU (aucune chute de cadence) ; MP4 md5 ✓ |
| 5 | Endurance Doze & mémoire Android 17 | **OK/WARN** | `force-idle` accepté (mState=IDLE) ; rendu survit : 7432 fr à +120 s, PID 6904 inchangé, oom cur=200 (FGS) ; PSS **115,7 → 127,3 Mo** (+11,6 Mo/2 min), RSS 328,6 → 343,0 Mo ; **0** lowmemorykiller / am_kill ; 0 exception loggée ; MP4 (7) = 8744 fr / 135,8 s / 64,4 fps ; ⚠ `mState` retombé à INACTIVE ≤ 2 min après le force (cause non identifiée, le rendu a survécu aux deux états) |

**Données brutes** : `donnees/mesures_test04.txt` · **Vidéos** : `video/cycle2_hotload.mp4`, `video/concurrence_3.mp4`, `video/concurrence_4.mp4`, `video/test4_ecran_eteint.mp4`, `video/test5_doze.mp4` (toutes md5-vérifiées après transfert base64 device→sandbox).

---

## 3. Gros problèmes / Régressions à corriger

### 3.1 L'API de contrôle n'existe que pendant un rendu (bloquant pour la vocation « agents externes »)
`POST /stop` arrête le service **et** le serveur HTTP :
```
11-26 09:58:08.826 I HyperframePoC: [STOP] MediaMuxer et MediaCodec fermés proprement. Fichier finalisé.
11-26 09:58:08.833 I HyperframePoC: [HTTP] Serveur de contrôle arrêté
11-26 09:58:08.833 I HyperframePoC: [HTTP] Boucle d'acceptation terminée
```
→ `curl http://127.0.0.1:8765/health` ensuite : *Connection refused*. Il n'y a aucun moyen HTTP de redémarrer le service (chicken-and-egg) ; il faut `am start-foreground-service` (Shizuku/adb) ou un tap UI. **Recommandation** : serveur HTTP dans un service séparé permanent (ou `START_STICKY`), démarré à l'ouverture de l'app et survivant au STOP du pipeline ; `/health` doit rester répondant en permanence.

### 3.2 LOAD_URL invalide reste silencieux (régression Phase 1 non corrigée)
```
curl -X POST /load {"url":"http://127.0.0.1:39999/inexistant.html"} → 200 {"status":"loading",…}
11-26 09:57:56.051 I HyperframePoC: [WEBVIEW] URL chargée à chaud: http://127.0.0.1:39999/inexistant.html
CDP : document.title = "Page Web non disponible" @ chrome-error://chromewebdata/
```
La spec interne (`hf-user`) exigeait « ne jamais renvoyer 200 sur échec LOAD_URL ». Un agent externe ne peut pas détecter l'échec sans CDP. **Recommandation** : vérifier `onReceivedError`/title après chargement et répondre `502 {"error":{…}}` (ou un champ `"loaded":false` dans `/status`).

### 3.3 Cadence de sortie non déterministe (54 → 118 fps selon les conditions)
Pendant cette campagne écran éteint, le fps **réel encodé** a varié de ~54 fps (pipelines bootés tôt, cf. MP4 (2)/(3)/(4) à 53,7–54,7 fps) à **118 fps** (pipeline booté alors que l'écran était déjà Dozing, MP4 (6) : moyenne 71,3 fps avec montée 55→118 ; MP4 (7) Doze : 64,4 fps). Le HUD rAF via CDP rapporte 120 fps. En Phase 1 la cadence écran éteint était stable à ~56 fps. Ce n'est pas une perte de perf mais une **perte de reproductibilité** : pour du motion design, le tempo de la vidéo dépend de l'état du display physique au moment de la création du VirtualDisplay et de la charge. `fps` demandé reste ignoré (60 ou 30 → même cadence réelle). **Recommandation** : décider d'une politique (cadence verrouillée à la demande `fps`, ou au moins documenter + exposer le fps réel dans `/status`).

### 3.4 Le token Bearer est loggé en clair par l'app
```
11-26 10:03:49.329 I HyperframePoC: [HTTP] Token=73fbd7e17199a23ca7ae2e5670bf9a4e26a3e7cba6469eef
```
Émis à chaque démarrage du serveur HTTP. logcat est lisible par adb/Shizuku et par toute app disposant de READ_LOGS sur certaines configs. L'impact est contenu (bind 127.0.0.1) mais le token perd son sens si un agent l'expose ensuite via tunnel LAN. **Recommandation** : supprimer ce log (ou n'imprimer que les 4 derniers caractères).

---

## 4. Petits problèmes / Améliorations ergonomiques

1. **`versionName=1.0-phase1`** sur un build Phase 2 — incrémenter (`1.1-phase2`) pour lever le doute lors des audits (l'APK a bien le dashboard, mais `dumpsys package` trompe).
2. **Fenêtre d'incohérence `/start` → `/status`** : après un 2ᵉ `POST /start` (réponse `"accepted"` immédiate), `/status` continue de décrire l'**ancien** pipeline (fps:60, ancien output_file) pendant ~3 s avant la bascule. Exposer un état intermédiaire (`"restarting":true`) ou répondre `202` avec le futur output.
3. **Hygiène des secrets côté agents** : le token transmis en argument de commande shell finit dans logcat via les traces de l'outil d'audit lui-même (`ShellExecDiag`/`ToolChain` — 11 occurrences constatées, imputables à l'agent, pas à l'app). Bonne pratique : `curl -H @token_file` ou `-K` config file.
4. **Les 7 `.pending-*hyperframe_poc.mp4` orphelins** de la Phase 1 (246 Mo, 90 Mo, …) traînent toujours dans Téléchargements et ne sont jamais purgés au démarrage — ajouter un nettoyage au boot du service (fichiers `.pending` de plus de N heures).
5. **Titre du dashboard chevauché par la barre d'état** (constat pilote sur 30401.jpg) : appliquer les WindowInsets (`fitsSystemWindows` / padding top) pour l'edge-to-edge.
6. **Champ « URL à rendre » prérempli `http://127.0.0.1:3000`** sans aucun serveur derrière : l'utilisateur qui appuie CHARGER URL tombe sur chrome-error sans retour dans l'UI. Mettre un état d'erreur lisible (lié à 3.2) et/ou préremplir avec `file:///android_asset/test.html`.
7. **CDP affiché comme toujours disponible** : préciser dans l'UI que le pont 9222 vit seulement pendant un rendu.
8. **Pas de régénération manuelle du token** ni d'affichage de sa date de création — un bouton « RÉGÉNÉRER » + horodatage aiderait en cas de compromission (voir 3.4).
9. **`/status` après `/stop`** : ne répond pas (connexion refusée). Même service mort, une réponse JSON d'erreur serait plus diagnostiquable — mais la vraie correction est 3.1.
10. **Compteur « Frames encodées »** : vérifié fidèle au backend (30 288 frames vues pendant le rendu pilote de 8 min ≈ 63 fps moyen ; `frames_encoded` = compteur EOS identique au log `[STATS]`). Continuer d'afficher aussi le **fps réel instantané** — aujourd'hui seul `fps` (demandé, ignoré) est montré.

---

### Verdict global Phase 2
**SUCCÈS PARTIEL (orienté bon)** — Les fonctions livrées marchent : sécurité Bearer effective (401 sans token), cycle de vie HTTP complet, hot-load sans interruption, garde-fou anti-corruption sur START dupliqué (finalisation propre systématique), survie écran éteint/Doze **sans régression de cadence** (jusqu'à 2× la Phase 1), mémoire stable sans LMK. Les trois chantiers pour la Phase 3 : (1) serveur HTTP permanent indépendant du pipeline, (2) vérification réelle du LOAD_URL, (3) cadence de sortie maîtrisée/documentée + suppression du log du token.
