from datetime import datetime, timezone

SCHEMA_VERSION = 1

# tree.changed event names — mirror the REST mutation that triggered them.
PERSON_CREATED = "person.created"
PERSON_UPDATED = "person.updated"
PERSON_DELETED = "person.deleted"
RELATIONSHIP_CREATED = "relationship.created"
RELATIONSHIP_DELETED = "relationship.deleted"


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string ending in 'Z'."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def tree_changed(
    chart_id: str,
    event: str,
    *,
    actor_id: str | None,
    actor_name: str | None,
    origin_id: str | None = None,
    data: dict | None = None,
) -> dict:
    """Build a `tree.changed` message (schema v1) for the realtime channel."""
    return {
        "v": SCHEMA_VERSION,
        "type": "tree.changed",
        "chartId": chart_id,
        "event": event,
        "actorId": actor_id,
        "actorName": actor_name,
        "originId": origin_id,
        "ts": now_iso(),
        "data": data or {},
    }
