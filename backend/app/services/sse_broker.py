"""SSE Event Broker for real-time push to frontend clients."""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any, List

logger = logging.getLogger("sse_broker")


class SSEBroker:
    """Manages SSE subscriptions and broadcasts events to connected clients."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, user_id: str) -> asyncio.Queue:
        """Subscribe a user to receive SSE events."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        if user_id not in self._subscribers:
            self._subscribers[user_id] = []
        self._subscribers[user_id].append(q)
        logger.debug("User %s subscribed (total: %d)", user_id, len(self._subscribers[user_id]))
        return q

    def unsubscribe(self, user_id: str, q: asyncio.Queue) -> None:
        """Remove a user's subscription."""
        if user_id in self._subscribers:
            try:
                self._subscribers[user_id].remove(q)
            except ValueError:
                pass
            if not self._subscribers[user_id]:
                del self._subscribers[user_id]

    async def publish_to_user(self, user_id: str, event: Dict[str, Any]) -> None:
        """Send an event to a specific user's SSE connections."""
        if user_id not in self._subscribers:
            logger.debug("No SSE subscribers for user %s", user_id)
            return
        queues = list(self._subscribers[user_id])
        logger.debug("Publishing to user %s (%d connections)", user_id, len(queues))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for user %s", user_id)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        """Broadcast an event to all connected users."""
        for user_id in list(self._subscribers.keys()):
            await self.publish_to_user(user_id, event)

    def publish_nowait(self, user_id: str, event: Dict[str, Any]) -> None:
        """Sync-safe helper to publish without awaiting."""
        if user_id not in self._subscribers:
            return
        for q in list(self._subscribers[user_id]):
            try:
                q.put_nowait(event)
            except Exception:
                pass


broker = SSEBroker()


async def sse_event_stream(
    user_id: str,
    q: asyncio.Queue,
    keepalive_seconds: int = 20,
) -> AsyncIterator[bytes]:
    """Generate SSE byte stream for a user connection."""
    # Send initial connected event immediately so proxies flush headers
    # and EventSource fires onopen
    yield b"data: {\"type\":\"connected\"}\n\n"
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=keepalive_seconds)
                data = json.dumps(event, default=str)
                yield f"data: {data}\n\n".encode("utf-8")
            except asyncio.TimeoutError:
                yield b"data: {\"type\":\"keepalive\"}\n\n"
    finally:
        broker.unsubscribe(user_id, q)
