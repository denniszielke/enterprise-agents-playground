import logging
import sys
import os
import asyncio
import uvicorn
from uvicorn import Server, Config

class SSEServer(Server):
    async def run(self, sockets=None):
        self.config.setup_event_loop()
        return await self.serve(sockets=sockets)

configList = [
    {"port": 8000, "script": "server-mcp-sse-customers:sse_app"}
]

async def run():
    apps = []
    for cfg in configList:
        config = Config(cfg["script"], host="0.0.0.0",
                        port=cfg["port"])
        server = SSEServer(config=config)
        apps.append(server.run())
    return await asyncio.gather(*apps)

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(run())
    except Exception as e:
        print(e)
        sys.exit(0)