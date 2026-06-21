"""Server-side Cloudinary image cleanup.

Generic helper so any feature that stores a Cloudinary URL (news contentImageUrls / coverImageUrl,
person photoUrl, ...) can delete the underlying asset when its record is removed.

Cloudinary's delete API works on *public_id*, not on the delivery URL, so the main job here is
turning a stored `secure_url` back into its public_id. Deletion is best-effort: if Cloudinary is
not configured or the API call fails, we log a warning and return instead of raising, so the caller
can still delete its database record.
"""
import asyncio
import logging
import re
from typing import Iterable, Optional
from urllib.parse import urlparse

import cloudinary
import cloudinary.api

from app.core.config import settings

logger = logging.getLogger("app.cloudinary")

# Configure the SDK once at import time. All three values must be present to enable deletion.
_CONFIGURED = bool(
    settings.CLOUDINARY_CLOUD_NAME
    and settings.CLOUDINARY_API_KEY
    and settings.CLOUDINARY_API_SECRET
)
if _CONFIGURED:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )

_VERSION_RE = re.compile(r"^v\d+$")
_EXT_RE = re.compile(r"\.[^/.]+$")
_DELETE_BATCH = 100  # Cloudinary admin API caps delete_resources at 100 public_ids per call.


def is_cloudinary_url(url: str) -> bool:
    """True if the URL points at our own Cloudinary cloud (host res.cloudinary.com and our cloud name
    in the path). Used to avoid trying to delete images hosted somewhere else."""
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host != "res.cloudinary.com":
        return False
    cloud = settings.CLOUDINARY_CLOUD_NAME
    return not cloud or f"/{cloud}/" in parsed.path


def public_id_from_url(url: str) -> Optional[str]:
    """Extract the Cloudinary public_id (including folders, without extension) from a delivery URL.

    Handles the common shape produced by unsigned uploads:
        https://res.cloudinary.com/<cloud>/image/upload/v1700000000/folder/name.jpg  -> folder/name
    Any transformation segments before the version are dropped. Returns None if the URL is not a
    parseable Cloudinary upload URL.
    """
    if not is_cloudinary_url(url):
        return None
    path = urlparse(url).path
    marker = "/upload/"
    idx = path.find(marker)
    if idx == -1:
        return None
    parts = [p for p in path[idx + len(marker):].split("/") if p]
    if not parts:
        return None
    # Skip everything up to and including a version segment (vNNN); transformations sit before it.
    start = 0
    for i, seg in enumerate(parts):
        if _VERSION_RE.match(seg):
            start = i + 1
            break
    public_parts = parts[start:]
    if not public_parts:
        return None
    public_id = "/".join(public_parts)
    return _EXT_RE.sub("", public_id) or None


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


async def delete_images(urls: Iterable[str]) -> dict:
    """Best-effort deletion of Cloudinary images by their delivery URLs.

    Non-Cloudinary URLs and unparseable URLs are ignored. Never raises: configuration gaps and API
    errors are logged at WARNING and swallowed so the caller's own deletion can proceed.
    Returns a dict mapping public_id -> Cloudinary status (e.g. "deleted", "not_found").
    """
    public_ids = []
    for url in urls or []:
        pid = public_id_from_url(url)
        if pid and pid not in public_ids:
            public_ids.append(pid)

    if not public_ids:
        return {}

    if not _CONFIGURED:
        logger.warning(
            "Cloudinary not configured; skipping delete of %d image(s): %s",
            len(public_ids), public_ids,
        )
        return {}

    result: dict = {}
    for chunk in _chunks(public_ids, _DELETE_BATCH):
        try:
            resp = await asyncio.to_thread(cloudinary.api.delete_resources, chunk)
        except Exception as err:  # network/auth/SDK errors — log and keep going.
            logger.warning("Cloudinary cleanup failed for public_ids=%s: %s", chunk, err)
            continue
        deleted = resp.get("deleted", {}) or {}
        result.update(deleted)
        leftovers = {k: v for k, v in deleted.items() if v != "deleted"}
        if leftovers:
            logger.warning("Cloudinary did not delete some images: %s", leftovers)
    return result
