#!/usr/bin/env python3
# Test handshake WebSocket CDP: avec/sans Origin, puis Runtime.evaluate si OK
import socket, base64, os, json, sys

HOST, PORT = '127.0.0.1', 9222
target = sys.argv[1] if len(sys.argv) > 1 else ''

def handshake(path, with_origin):
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f'GET {path} HTTP/1.1\r\n'
        f'Host: 127.0.0.1:{PORT}\r\n'
        'Upgrade: websocket\r\n'
        'Connection: Upgrade\r\n'
        f'Sec-WebSocket-Key: {key}\r\n'
        'Sec-WebSocket-Version: 13\r\n'
    )
    if with_origin:
        req += f'Origin: http://127.0.0.1:{PORT}\r\n'
    req += '\r\n'
    s = socket.create_connection((HOST, PORT), timeout=5)
    s.sendall(req.encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        chunk = s.recv(4096)
        if not chunk:
            break
        resp += chunk
    head = resp.split(b'\r\n\r\n')[0].decode('utf-8', 'replace')
    return s, head

for label, origin in [('avec Origin', True), ('sans Origin', False)]:
    path = f'/devtools/page/{target}' if target else '/devtools/browser'
    try:
        s, head = handshake(path, origin)
        status = head.split('\r\n')[0]
        print(f'[{label}] {path} -> {status}')
        if ' 101 ' in status:
            # envoyer Runtime.evaluate: lire le HUD
            def send_text(sock, text):
                payload = text.encode()
                mask = os.urandom(4)
                masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                n = len(payload)
                hdr = bytes([0x81])
                if n < 126:
                    hdr += bytes([0x80 | n])
                elif n < 65536:
                    hdr += bytes([0x80 | 126]) + n.to_bytes(2, 'big')
                else:
                    hdr += bytes([0x80 | 127]) + n.to_bytes(8, 'big')
                sock.sendall(hdr + mask + masked)
            def recv_text(sock, timeout=5):
                sock.settimeout(timeout)
                buf = b''
                while True:
                    b1 = sock.recv(1)
                    if not b1: return None
                    b2 = sock.recv(1)
                    ln = b2[0] & 0x7F
                    if ln == 126:
                        ln = int.from_bytes(sock.recv(2), 'big')
                    elif ln == 127:
                        ln = int.from_bytes(sock.recv(8), 'big')
                    mask = sock.recv(4) if (b2[0] & 0x80) else None
                    data = b''
                    while len(data) < ln:
                        data += sock.recv(ln - len(data))
                    if mask:
                        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
                    if (b1[0] & 0x0F) == 1:
                        return data.decode('utf-8', 'replace')
            msg = json.dumps({'id': 1, 'method': 'Runtime.evaluate',
                              'params': {'expression': 'JSON.stringify({t: document.title, f: document.getElementById("frames").textContent, fps: document.getElementById("fps").textContent})', 'returnByValue': True}})
            send_text(s, msg)
            r = recv_text(s)
            print('  REPONSE:', r[:400])
        s.close()
    except Exception as e:
        print(f'[{label}] {path} -> ERREUR: {e}')
