import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """In-memory registry of active WebSocket connections grouped by chartId ("room").

    Push-only: the server broadcasts tree-change signals to every viewer of a chart.
    This works within a single process (the app currently runs one uvicorn worker). To
    scale to multiple workers/instances, replace the body of broadcast() with a Redis
    pub/sub fan-out; the public interface can stay the same.
    """

    def __init__(self) -> None:
        # chartId -> { websocket: clientId | None }
        self._rooms: dict[str, dict[WebSocket, str | None]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, chart_id: str, websocket: WebSocket, client_id: str | None = None) -> None:
        async with self._lock:
            self._rooms.setdefault(chart_id, {})[websocket] = client_id

    async def disconnect(self, chart_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(chart_id)
            if room is not None:
                room.pop(websocket, None)
                if not room:
                    self._rooms.pop(chart_id, None)

    async def broadcast(self, chart_id: str, message: dict, exclude_client: str | None = None) -> None:
        """Send `message` (as JSON) to every connection in the chart room.

        `exclude_client` is a clientId (browser tab id); connections opened with that
        clientId are skipped so the tab that triggered the change does not refetch its
        own echo.
        """
        async with self._lock:
            targets = list(self._rooms.get(chart_id, {}).items())

        dead: list[WebSocket] = []
        for ws, client_id in targets:
            if exclude_client is not None and client_id == exclude_client:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                # Connection is already gone; mark it for cleanup.
                dead.append(ws)

        for ws in dead:
            await self.disconnect(chart_id, ws)


manager = ConnectionManager()
