import logging

from app.realtime.manager import manager
from app.realtime import events

logger = logging.getLogger(__name__)


def _actor_name(user: dict) -> str | None:
    return user.get("fullName") or user.get("email")


async def publish_tree_change(
    chart_id: str,
    event: str,
    user: dict,
    origin_id: str | None = None,
    data: dict | None = None,
) -> None:
    """Broadcast a tree change to everyone viewing `chart_id`.

    Best-effort: any failure is logged and swallowed so it never breaks the mutation
    request that already succeeded. The tab identified by `origin_id` (X-Client-Id) is
    excluded so the actor does not refetch its own echo.
    """
    try:
        message = events.tree_changed(
            chart_id,
            event,
            actor_id=user.get("_id"),
            actor_name=_actor_name(user),
            origin_id=origin_id,
            data=data,
        )
        await manager.broadcast(chart_id, message, exclude_client=origin_id)
    except Exception:
        logger.exception("Failed to broadcast tree change for chart %s", chart_id)
