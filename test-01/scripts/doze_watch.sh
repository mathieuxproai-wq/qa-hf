#!/bin/sh
S(){ android-shizuku-cli exec "$1" 2>&1 | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['stdout'])" 2>/dev/null; }
pid(){ S 'ps -A | grep com.hyperframe.render' | grep -oE '^[^ ]+ +[0-9]+' | awk '{print $2}' | head -1; }
fr(){ S 'logcat -d -s HyperframePoC' | grep STATS | tail -1 | grep -oE '[0-9]+$'; }
P0=$(pid); F0=$(fr); T0=$(date +%s)
echo "START pid=$P0 frames=$F0 $(date +%T)"
i=0
while [ $i -lt 6 ]; do
  sleep 30
  i=$((i+1))
  P=$(pid); F=$(fr); T=$(date +%s)
  rss=$(S 'dumpsys meminfo com.hyperframe.render' | grep -iE 'TOTAL PSS|TOTAL RSS' | head -1)
  echo "t=$((T-T0))s pid=$P frames=$F  [$rss]"
done
P1=$(pid); F1=$(fr); T1=$(date +%s)
echo "END pid=$P1 frames=$F1 delta_frames=$((F1-F0)) over $((T1-T0))s = $(( (F1-F0)/(T1-T0) ))fps"
[ -z "$P1" ] && echo "PROCESS_DIED" || echo "PROCESS_ALIVE pid=$P1"