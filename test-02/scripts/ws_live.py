#!/usr/bin/env python3
import socket, base64, os, json, time, urllib.request

HOST, PORT = '127.0.0.1', 9222
tgt = json.load(urllib.request.urlopen(f'http://{HOST}:{PORT}/json/list', timeout=5))[0]['id']
print('target:', tgt)

key = base64.b64encode(os.urandom(16)).decode()
req = (f'GET /devtools/page/{tgt} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nUpgrade: websocket\r\n'
       f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
s = socket.create_connection((HOST, PORT), timeout=5)
s.sendall(req.encode())
resp = b''
while b'\r\n\r\n' not in resp:
    c = s.recv(4096)
    if not c: break
    resp += c
print('handshake:', resp.split(b'\r\n\r\n')[0].decode().split('\r\n')[0])

def send_text(sock, text):
    p = text.encode(); mask = os.urandom(4)
    m = bytes(b ^ mask[i % 4] for i, b in enumerate(p)); n = len(p)
    hdr = bytes([0x81, 0x80 | n]) if n < 126 else bytes([0x81, 0x80|126]) + n.to_bytes(2,'big')
    sock.sendall(hdr + mask + m)

def recv_text(sock, timeout=5):
    sock.settimeout(timeout); b1 = sock.recv(1); b2 = sock.recv(1)
    ln = b2[0] & 0x7F
    if ln == 126: ln = int.from_bytes(sock.recv(2),'big')
    elif ln == 127: ln = int.from_bytes(sock.recv(8),'big')
    mask = sock.recv(4) if (b2[0] & 0x80) else None
    d = b''
    while len(d) < ln: d += sock.recv(ln - len(d))
    if mask: d = bytes(b ^ mask[i % 4] for i, b in enumerate(d))
    return d.decode('utf-8','replace')

expr = 'JSON.stringify({frames:document.getElementById("frames").textContent, fps:document.getElementById("fps").textContent, chrono:document.getElementById("chrono").textContent, visibility:document.visibilityState, hidden:document.hidden, w:innerWidth, h:innerHeight, hasRAF:(typeof requestAnimationFrame)})'
for i in range(3):
    send_text(s, json.dumps({'id': 10+i, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'returnByValue': True}}))
    print(f'eval#{i}:', recv_text(s)[:300])
    time.sleep(1)
s.close()
