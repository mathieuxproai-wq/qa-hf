#!/bin/sh
# Pull /sdcard/Download/hyperframe_poc.mp4 -> sandbox via Shizuku base64 chunks (each <120KB arg)
cd /var/minis/workspace
ANDROID=/data/local/tmp
android-shizuku-cli exec "base64 $ANDROID/../..//sdcard/Download/hyperframe_poc.mp4 > $ANDROID/hf.b64 2>/dev/null || base64 /sdcard/Download/hyperframe_poc.mp4 > $ANDROID/hf.b64" >/dev/null 2>&1
SZ=$(android-shizuku-cli exec "stat -c%s $ANDROID/hf.b64" 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['stdout'].strip())" 2>/dev/null)
echo "b64 size=$SZ"
rm -f hf_small.b64
OFF=0; CHUNK=110000; N=0
while [ "$OFF" -lt "$SZ" ]; do
  P=$(android-shizuku-cli exec "dd if=$ANDROID/hf.b64 bs=1 skip=$OFF count=$CHUNK 2>/dev/null" 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['stdout'],end='')" 2>/dev/null)
  printf '%s' "$P" >> hf_small.b64
  OFF=$((OFF+CHUNK)); N=$((N+1))
done
echo "chunks=$N"
base64 -d hf_small.b64 > hf_small.mp4 2>/dev/null
ls -la hf_small.mp4