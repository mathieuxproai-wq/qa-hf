#!/usr/bin/env python3
"""Client CDP minimal — WS sans header Origin (sinon 403), frames masquées côté client.
Usage: python3 cdp_eval.py '<js expression>' [ws_url]
Si ws_url omis: découvert via http://127.0.0.1:9222/json/list (première cible page).
"""
import socket, base64, os, json, struct, sys, urllib.request

def discover():
    with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=3) as r:
        tabs = json.loads(r.read().decode())
    for t in tabs:
        if t.get("type") == "page":
            return t
    raise SystemExit("no page target: %s" % tabs)

def read_frame(sock):
    hdr = b""
    while len(hdr) < 2:
        c = sock.recv(2 - len(hdr))
        if not c:
            raise ConnectionError("closed")
        hdr += c
    fin_op = hdr[0]; ln = hdr[1] & 0x7F
    if ln == 126:
        ext = b""
        while len(ext) < 2:
            ext += sock.recv(2 - len(ext))
        ln = struct.unpack(">H", ext)[0]
    elif ln == 127:
        ext = b""
        while len(ext) < 8:
            ext += sock.recv(8 - len(ext))
        ln = struct.unpack(">Q", ext)[0]
    payload = b""
    while len(payload) < ln:
        payload += sock.recv(min(65536, ln - len(payload)))
    return payload

def main():
    expr = sys.argv[1]
    ws_url = sys.argv[2] if len(sys.argv) > 2 else discover()["webSocketDebuggerUrl"]
    path = ws_url.split("127.0.0.1:9222", 1)[1] if "127.0.0.1:9222" in ws_url else "/devtools/page"
    host = "127.0.0.1:9222"
    s = socket.create_connection(("127.0.0.1", 9222), timeout=5)
    key = base64.b64encode(os.urandom(16)).decode()
    # PAS de header Origin — sinon 403 (piège test-02)
    req = ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, host, key))
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    status = buf.split(b"\r\n", 1)[0].decode()
    if "101" not in status:
        print(json.dumps({"error": "handshake_failed", "status": status})); return 1
    payload = json.dumps({"id": 1, "method": "Runtime.evaluate",
                          "params": {"expression": expr, "returnByValue": True}}).encode()
    mask = os.urandom(4)
    n = len(payload)
    hdr = b"\x81"
    if n < 126: hdr += bytes([0x80 | n])
    elif n < 65536: hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
    else: hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
    s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
    while True:
        frm = read_frame(s)
        try:
            msg = json.loads(frm.decode())
        except Exception:
            continue
        if msg.get("id") == 1:
            print(json.dumps(msg, ensure_ascii=False))
            return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
