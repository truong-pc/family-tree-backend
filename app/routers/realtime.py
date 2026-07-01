import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from app.utils.deps import get_user_from_token, get_chart_or_404, can_write
from app.realtime.manager import manager
from app.realtime.events import SCHEMA_VERSION, now_iso

router = APIRouter(prefix="/api/v1/charts/{chartId}", tags=["Realtime"])


@router.websocket("/ws")
async def tree_ws(
    websocket: WebSocket,
    chartId: str,
    token: str | None = Query(default=None),
    clientId: str | None = Query(default=None),
):
    """Realtime channel for a chart. Push-only: the server emits `tree.changed` when a
    person/relationship mutation happens; clients refetch `GET /tree`. Only owner/editor
    (can_write) may connect.

    We accept() first so custom close codes (4401/4403/4404) reach the browser — codes
    sent before the handshake completes are reported as 1006 instead.
    """
    await websocket.accept()

    user = await get_user_from_token(token)
    if user is None:
        await websocket.close(code=4401)
        return

    try:
        chart = await get_chart_or_404(chartId)
    except HTTPException:
        await websocket.close(code=4404)
        return

    if not can_write(chart, user["_id"]):
        await websocket.close(code=4403)
        return

    role = "owner" if chart["ownerId"] == user["_id"] else "editor"
    await manager.connect(chartId, websocket, clientId)
    try:
        await websocket.send_json(
            {"v": SCHEMA_VERSION, "type": "connected", "chartId": chartId, "role": role}
        )
        # Loop to detect disconnect and answer optional app-level heartbeats.
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict) and data.get("type") == "ping":
                await websocket.send_json({"v": SCHEMA_VERSION, "type": "pong", "ts": now_iso()})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(chartId, websocket)
