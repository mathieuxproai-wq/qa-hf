# AGENT_QA_AUDIT_PHASE1.md — Protocole d'Audit & Batterie de Tests (Android 17 / Alpine + Shizuku)

## 1. CONTEXTE & RÈGLE D'OR POUR L'AGENT DE TEST
Tu es un agent d'assurance qualité (QA) opérant depuis un environnement **Alpine Linux (`proot`)** sur l'appareil Android 17 cible, avec accès aux privilèges shell (`UID 2000`) via **Shizuku (`rish`)**.

**⚠️ INTERDICTION FORMELLE (NE PAS INSTALLER CHROMIUM) :**
Ne tente **pas** d'installer `chromium` ni `puppeteer` complet dans Alpine `proot`. L'application testée (`com.hyperframe.render`) embarque déjà son propre moteur Chromium matériel (WebView Android sur `VirtualDisplay`) et expose son protocole DevTools (CDP) sur **`http://127.0.0.1:9222`**.
Dans Alpine, installe uniquement des outils légers (`apk add curl nodejs npm jq ffmpeg` ou `mediainfo`) et utilise `puppeteer-core` (ou `ws`) en mode `browserURL: "http://127.0.0.1:9222"`.

---

## 2. BATTERIE DE TESTS À EXÉCUTER (VIA SHIZUKU `rish` & ALPINE)

Exécute ces 5 blocs de tests dans l'ordre, en relevant les métriques exactes et les logs système.

### Bloc A : Installation, Démarrage & Audit des Flags / Permissions Android 17
1. **Installation & Lancement :**
   * Installe l'APK via Shizuku : `rish -c "pm install -r /chemin/vers/app-debug.apk"`
   * Vide les logs : `rish -c "logcat -c"`
   * Lance l'Activity initiale (pour accorder permissions/exemption batterie si nécessaire) ou démarre le service :
     `rish -c "am start -n com.hyperframe.render/.MainActivity"`
2. **Audit des Flags & Quotas Système (`dumpsys`) :**
   * Inspecte l'état du processus, son score OOM (`oom_adj`), son *App Standby Bucket* et ses restrictions d'arrière-plan :
     `rish -c "dumpsys activity processes com.hyperframe.render"`
     `rish -c "am get-standby-bucket com.hyperframe.render"`
     `rish -c "dumpsys deviceidle whitelist | grep hyperframe"`
   * Vérifie l'état du `VirtualDisplay` privé et des surfaces actives :
     `rish -c "dumpsys display | grep -A 25 -i Hyperframe"`
     `rish -c "dumpsys media.codec"` (vérifier qu'un encodeur matériel `c2.qti.avc.encoder` ou `c2.mtk...` est bien actif et non logiciel).

### Bloc B : Validation du Pont CDP & Pilotage Sans Chromium Local
1. **Vérification du port `9222` depuis Alpine :**
   * Exécute `curl -s http://127.0.0 | jq .`
   * Vérifie que le socket répond sans blocage réseau local Android 17 (`ACCESS_LOCAL_NETWORK`).
2. **Test d'injection et de contrôle frame-par-frame (Node.js + `ws` ou `puppeteer-core`) :**
   * Connecte-toi à `webSocketDebuggerUrl`, évalue `document.title`, injecte une modification DOM ou un changement d'URL (`LOAD_URL`), et mesure la latence d'aller-retour (RTT) d'une commande `Runtime.evaluate`.

### Bloc C : Test de Rendu Écran Éteint & Throttling `requestAnimationFrame`
1. **Extinction prolongée de l'écran physique :**
   * Simule l'appui sur le bouton Power pour éteindre l'écran : `rish -c "input keyevent 26"`
   * Vérifie que l'écran est bien `OFF` (`rish -c "dumpsys power | grep mWakefulness"`).
   * Laisse tourner le rendu pendant **60 secondes** écran totalement éteint et verrouillé.
2. **Vérification du maintien des FPS écran éteint :**
   * Pendant que l'écran est éteint, interroge via CDP (`Runtime.evaluate`) le compteur de frames de `test.html` à `t = 10s` et `t = 40s` pour vérifier si `requestAnimationFrame` tourne toujours à 60 FPS ou s'il est bridé (throttled) à 1 FPS par Chromium.

### Bloc D : Test d'Endurance face aux Process Killers Android (LMKD / Doze / Phantom Processes)
1. **Mise en sommeil forcé (Deep Doze) :**
   * Écran éteint, force le mode Doze profond via Shizuku :
     `rish -c "dumpsys deviceidle force-idle"`
   * Attends **3 minutes** tout en surveillant la survie du PID de `com.hyperframe.render` et le compteur `[STATS]` dans `logcat -s HyperframePoC`.
   * Sors du mode Doze : `rish -c "dumpsys deviceidle unforce"`.
2. **Test de pression mémoire (LMKD / App Memory Limits Android 17) :**
   * Surveille la consommation RSS/PSS du processus (`rish -c "dumpsys meminfo com.hyperframe.render"`) et vérifie dans `logcat -d | grep -iE "lowmemorykiller|am_kill|hyperframe"` si Android 17 déclenche des alertes mémoire ou tue le processus WebView enfant (`sandboxed_process`).

### Bloc E : Arrêt Propre & Audit de la Vidéo Générée (`hyperframe_poc.mp4`)
1. **Arrêt du service :**
   * `rish -c "am startservice -n com.hyperframe.render/.HeadlessRenderService -a STOP"`
2. **Analyse technique du fichier MP4 généré :**
   * Inspecte le fichier avec `ffprobe` (ou `mediainfo`) : durée réelle, résolution, codec, framerate moyen, frames perdues, et vérifie visuellement/programmatiquement (via extraction de 3 frames clés avec `ffmpeg`) que l'image n'est pas noire et que le chronomètre affiché dans la vidéo correspond à la durée réelle.

---

## 3. FORMAT OBLIGATOIRE DU RAPPORT DE RENDU

Rédige ton rapport final en respectant **strictement** cette structure Markdown :

```markdown
# RAPPORT D'AUDIT QA — Hyperframe Render (Phase 1)

## 1. Description de l'Application & Comportement à l'Usage
- **Ce que fait réellement l'application :** (Décrire le cycle de vie observé : lancement, notifications, comportement du service en arrière-plan, interactions avec Alpine/Termux).
- **Expérience d'utilisation & Ergonomie CLI :** (Facilité de pilotage via `am` et CDP, clarté des logs `HyperframePoC`, comportement de la batterie/chauffe observé).
- **Verdict Global :** [SUCCÈS PARTIEL / SUCCÈS TOTAL / ÉCHEC BLOQUANT]

## 2. Tableau Récapitulatif des Tests

| Test | Statut (OK / KO / WARN) | Métrique / Preuve clé (`logcat` / `dumpsys` / `ffprobe`) |
| :--- | :--- | :--- |
| Installation & `VirtualDisplay` privé | ... | ... |
| Encodeur Matériel (`MediaCodec`) | ... | ... |
| Pont CDP (`127.0.0.1:9222`) | ... | ... |
| Rendu Écran Éteint (60s) | ... | ... |
| Survie Doze / Process Killers (3 min) | ... | ... |
| Intégrité `hyperframe_poc.mp4` | ... | ... |

## 3. Gros Problèmes à Corriger (Critiques / Bloquants)
*(Lister ici tout crash, écran noir, throttling à 1 FPS écran éteint, processus tué par LMKD/Doze, fichier MP4 corrompu ou blocage réseau Android 17, avec l'extrait exact de `logcat` ou `dumpsys`.)*

## 4. Petits Problèmes & Points d'Amélioration (Mineurs)
*(Lister ici les frictions : gestion des permissions au premier lancement, fuite mémoire légère, latence CDP, format des intents CLI, nettoyage des fichiers temporaires, etc.)*

## 5. Audit des Flags & Restrictions Système Android 17
- **OOM Adj & Priorité Processus :** (Valeur relevée)
- **Standby Bucket & Doze :** (Comportement sous `force-idle`)
- **Flags WebView / Chromium détectés :** (Throttling, sandboxed renderer, accélération matérielle)
```