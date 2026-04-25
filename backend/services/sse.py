import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator


class SSEManager:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[str]] = defaultdict(asyncio.Queue)

    async def publish(self, session_id: str, message: str) -> None:
        await self._queues[session_id].put(message)

    async def subscribe(self, session_id: str) -> AsyncGenerator[str, None]:
        queue = self._queues[session_id]
        try:
            while True:
                message = await asyncio.wait_for(queue.get(), timeout=120.0)
                if message == "__DONE__":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps({'type': 'log', 'message': message})}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    async def close(self, session_id: str) -> None:
        await self._queues[session_id].put("__DONE__")


sse_manager = SSEManager()
