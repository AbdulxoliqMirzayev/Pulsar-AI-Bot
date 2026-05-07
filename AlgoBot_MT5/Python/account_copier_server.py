from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from dataclasses import dataclass, field


@dataclass
class Client:
    conn: socket.socket
    addr: tuple[str, int]
    role: str = "unknown"
    connected_at: float = field(default_factory=time.time)


class CopierServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5555) -> None:
        self.host = host
        self.port = port
        self.clients: list[Client] = []
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(50)

    def broadcast_signal(self, signal_json: str) -> None:
        payload = (signal_json.strip() + "\n").encode("utf-8")
        dead: list[Client] = []
        with self.lock:
            for client in self.clients:
                if client.role != "slave":
                    continue
                try:
                    client.conn.sendall(payload)
                except OSError:
                    dead.append(client)
            for client in dead:
                self._remove(client)

    def _remove(self, client: Client) -> None:
        try:
            client.conn.close()
        except OSError:
            pass
        if client in self.clients:
            self.clients.remove(client)

    def handle_client(self, client: Client) -> None:
        print(f"Connected: {client.addr}")
        buffer = ""
        try:
            while True:
                data = client.conn.recv(8192)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        print(f"Bad JSON from {client.addr}: {line[:120]}")
                        continue
                    if "role" in message:
                        client.role = message["role"]
                        print(f"{client.addr} role={client.role}")
                        continue
                    if message.get("action") in {"OPEN", "CLOSE", "MODIFY", "HEARTBEAT"}:
                        if message.get("action") == "OPEN":
                            message["server_received_at"] = time.time()
                        self.broadcast_signal(json.dumps(message))
        except OSError as exc:
            print(f"Client error {client.addr}: {exc}")
        finally:
            with self.lock:
                self._remove(client)
            print(f"Disconnected: {client.addr}")

    def accept_connections(self) -> None:
        print(f"Copier server running on {self.host}:{self.port}")
        while True:
            conn, addr = self.server.accept()
            client = Client(conn=conn, addr=addr)
            with self.lock:
                self.clients.append(client)
            threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5555)
    args = parser.parse_args()
    CopierServer(args.host, args.port).accept_connections()


if __name__ == "__main__":
    main()
