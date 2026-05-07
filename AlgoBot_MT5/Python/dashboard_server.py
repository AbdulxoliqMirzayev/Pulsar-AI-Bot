from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from aiohttp import web


class DashboardServer:
    def __init__(self) -> None:
        self.clients: set[web.WebSocketResponse] = set()
        self.state: dict[str, Any] = {
            "balance": 0,
            "daily_pl": 0,
            "risk_used": 0,
            "open_trades": 0,
            "equity": [],
            "strategies": {},
            "trades": [],
        }

    async def ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        await ws.send_json(self.state)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    await self.update(json.loads(msg.data))
                except json.JSONDecodeError:
                    pass
        self.clients.discard(ws)
        return ws

    async def push_handler(self, request: web.Request) -> web.Response:
        payload = await request.json()
        await self.update(payload)
        return web.json_response({"ok": True})

    async def index_handler(self, request: web.Request) -> web.Response:
        html_path = Path(__file__).resolve().parents[2] / "dashboard.html"
        if html_path.exists():
            return web.Response(text=html_path.read_text(encoding="utf-8"), content_type="text/html")
        return web.Response(text="AlgoBot dashboard server running.")

    async def update(self, payload: dict[str, Any]) -> None:
        self.state.update(payload)
        dead = []
        for ws in self.clients:
            try:
                await ws.send_json(self.state)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def tcp_ingest(self, host: str, port: int) -> None:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            data = await reader.read(65536)
            try:
                payload = json.loads(data.decode("utf-8"))
                await self.update(payload)
                writer.write(b"OK")
            except Exception as exc:
                writer.write(f"ERR {exc}".encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle, host, port)
        async with server:
            await server.serve_forever()

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self.index_handler)
        app.router.add_get("/ws", self.ws_handler)
        app.router.add_post("/push", self.push_handler)
        return app


async def main_async(host: str, port: int, tcp_port: int) -> None:
    server = DashboardServer()
    runner = web.AppRunner(server.app())
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Dashboard HTTP/WS running on http://{host}:{port}")
    await server.tcp_ingest(host, tcp_port)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--tcp-port", type=int, default=8766)
    args = parser.parse_args()
    asyncio.run(main_async(args.host, args.port, args.tcp_port))


if __name__ == "__main__":
    main()
