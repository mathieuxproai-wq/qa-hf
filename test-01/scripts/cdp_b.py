import websocket, json, sys, time
ws_url = sys.argv[1]
try:
    ws = websocket.create_connection(ws_url, timeout=8, suppress_origin=True, header=["Origin: "])
except Exception as e:
    print("WS_CONNECT_FAIL:", str(e)[:200]); sys.exit(2)
_id=0
def cmd(method,params=None):
    global _id; _id+=1
    t=time.time()
    ws.send(json.dumps({"id":_id,"method":method,"params":params or {}}))
    while True:
        m=json.loads(ws.recv())
        if m.get("id")==_id:
            return m,(time.time()-t)*1000
# RTT title
r,ms=cmd("Runtime.evaluate",{"expression":"document.title","returnByValue":True})
print("TITLE:",r.get("result",{}).get("result",{}).get("value"),"RTT=%.2fms"%ms)
# inject DOM change
r,ms2=cmd("Runtime.evaluate",{"expression":"document.getElementById('hud').style.background='rgba(255,0,0,.3)'; 'injected'","returnByValue":True})
print("INJECT:",r.get("result",{}).get("result",{}).get("value"),"RTT=%.2fms"%ms2)
# frame counter
r,ms3=cmd("Runtime.evaluate",{"expression":"document.getElementById('frames').textContent","returnByValue":True})
print("FRAMES:",r.get("result",{}).get("result",{}).get("value"),"RTT=%.2fms"%ms3)
ws.close()