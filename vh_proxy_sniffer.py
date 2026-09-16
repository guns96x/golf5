"""
VirtualHere TCP Proxy & USB Protocol Sniffer
Listens on 127.0.0.1:7575 (or 7576) and forwards to 100.105.189.114:7575.
Dumps all bidirectional packets with timestamps, hex, and ASCII.
"""
import socket
import threading
import time
import os
import sys

TARGET_HOST = "100.105.189.114"
TARGET_PORT = 7575
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 7575

LOG_FILE = r"C:\Users\pavlo\golf5\vh_sniff_traffic.log"

log_lock = threading.Lock()

def log_packet(direction, data):
    ts = time.strftime("%H:%M:%S.") + f"{int((time.time() % 1) * 1000):03d}"
    hex_str = ' '.join(f"{b:02X}" for b in data)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
    
    line = f"[{ts}] {direction} ({len(data)} bytes):\n  HEX: {hex_str}\n  ASC: {ascii_str}\n"
    print(line, flush=True)
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def forward(src, dst, direction):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            log_packet(direction, data)
            dst.sendall(data)
    except Exception as e:
        print(f"[{direction}] Connection closed: {e}", flush=True)
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

def handle_client(client_sock, client_addr):
    print(f"[+] Client connected from {client_addr}", flush=True)
    try:
        remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_sock.connect((TARGET_HOST, TARGET_PORT))
        print(f"[+] Connected to phone VirtualHere {TARGET_HOST}:{TARGET_PORT}", flush=True)
    except Exception as e:
        print(f"[-] Failed to connect to phone: {e}", flush=True)
        client_sock.close()
        return

    t1 = threading.Thread(target=forward, args=(client_sock, remote_sock, "PC -> PHONE (OUT/CMD)"))
    t2 = threading.Thread(target=forward, args=(remote_sock, client_sock, "PHONE -> PC (IN/RESP)"))
    t1.daemon = True
    t2.daemon = True
    t1.start()
    t2.start()

def main():
    global LISTEN_PORT
    # Clear previous log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== VirtualHere Traffic Sniffer Started at {time.ctime()} ===\n")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_HOST, LISTEN_PORT))
    except OSError:
        LISTEN_PORT = 7576
        server.bind((LISTEN_HOST, LISTEN_PORT))
        print(f"[*] Port 7575 busy, listening on {LISTEN_HOST}:{LISTEN_PORT}")

    server.listen(5)
    print(f"[+] VirtualHere Sniffer listening on {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}")
    print(f"[+] Logging to {LOG_FILE}")
    print("[*] Waiting for VirtualHere Client connection...")

    try:
        while True:
            client, addr = server.accept()
            th = threading.Thread(target=handle_client, args=(client, addr))
            th.daemon = True
            th.start()
    except KeyboardInterrupt:
        print("\n[*] Stopping sniffer...")
    finally:
        server.close()

if __name__ == "__main__":
    main()
