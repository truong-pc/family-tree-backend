from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException
import nh3

from app.core.config import settings
from app.db.mongo import mongo
from app.models.news_model import NewsCreate
from app.utils.cloudinary_helper import delete_images, is_cloudinary_url


def _news_coll():
    """Return the 'news' MongoDB collection."""
    return mongo.client[settings.MONGODB_DB].news


def _now():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def sanitize_html(html: str) -> str:
    """Strip dangerous markup (script tags, on* event handlers, javascript: URLs) from
    editor-generated HTML while preserving safe rich-text elements. Cloudinary images
    (<img src="https://...">) are kept because https is an allowed scheme by default in nh3.

    Note: passing `attributes` REPLACES nh3's default allow-list entirely (it does not merge), so
    img sizing attributes (width/height) that nh3 normally allows must be listed explicitly here,
    otherwise they get stripped on save."""
    return nh3.clean(
        html,
        attributes={
            "*": {"class", "id", "style", "title", "alt"},
            # nh3 auto-adds rel="noopener noreferrer" to links via its default link_rel setting,
            # so target="_blank" links are safe against reverse tabnabbing without listing "rel".
            "a": {"href", "target"},
            "img": {"src", "width", "height"},
        },
    )


class _ImgSrcCollector(HTMLParser):
    """Collect every <img src> value while parsing an HTML fragment."""

    def __init__(self):
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            for key, value in attrs:
                if key == "src" and value:
                    self.srcs.append(value)


def extract_content_image_urls(html: str) -> list[str]:
    """Collect the Cloudinary <img src> URLs embedded in (already sanitized) news HTML, deduped
    in document order. Stored alongside the post so deletion can clean up Cloudinary without
    re-parsing the HTML. Non-Cloudinary images are ignored — we only delete assets we own."""
    collector = _ImgSrcCollector()
    collector.feed(html)
    urls: list[str] = []
    for src in collector.srcs:
        if is_cloudinary_url(src) and src not in urls:
            urls.append(src)
    return urls


async def _cleanup_draft_orphans(candidate_urls, kept_urls) -> None:
    """Delete Cloudinary images that the saved post no longer references. `candidate_urls` are
    images that might be orphaned — leftover draft uploads and/or body images removed during an
    edit; `kept_urls` are the URLs the post actually references (body images + cover). Any candidate
    not among the kept URLs is removed from Cloudinary. Best-effort via delete_images, which ignores
    non-Cloudinary/unparseable URLs and never raises, so saving the post always succeeds."""
    if not candidate_urls:
        return
    kept = {u for u in kept_urls if u}
    orphans = [u for u in candidate_urls if u and u not in kept]
    if orphans:
        await delete_images(orphans)


def _parse_object_id(postId: str) -> ObjectId:
    """Convert a hex string to a BSON ObjectId. Raises HTTP 400 if the format is invalid."""
    try:
        return ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid postId")


def _doc_to_out(doc) -> dict:
    """Map a raw MongoDB document to the full NewsOut response shape (includes contentHtml)."""
    return {
        "postId": str(doc["_id"]),
        "chartId": doc["chartId"],
        "authorId": doc["authorId"],
        "title": doc["title"],
        "contentHtml": doc["contentHtml"],
        "coverImageUrl": doc.get("coverImageUrl"),
        "tags": doc.get("tags") or [],
        "public": doc["public"],
        "publishedAt": doc.get("publishedAt"),
        "createdAt": doc["createdAt"],
        "updatedAt": doc["updatedAt"],
    }


def _doc_to_card(doc) -> dict:
    """Map a raw MongoDB document to the lightweight NewsCardOut shape (excludes contentHtml).
    Used for list and feed endpoints to keep response payloads small."""
    return {
        "postId": str(doc["_id"]),
        "chartId": doc["chartId"],
        "chartName": doc.get("chartName"),
        "authorId": doc["authorId"],
        "authorName": doc.get("authorName"),
        "title": doc["title"],
        "coverImageUrl": doc.get("coverImageUrl"),
        "tags": doc.get("tags") or [],
        "public": doc["public"],
        "publishedAt": doc.get("publishedAt"),
        "createdAt": doc["createdAt"],
        "updatedAt": doc["updatedAt"],
    }


# --- Cursor-based pagination for the feed (sorted by publishedAt desc, then _id desc) ---

def _encode_cursor(doc) -> str:
    """Encode the last document in a page into an opaque cursor string.
    Format: '<publishedAt ISO>|<_id hex>' — used by the client to fetch the next page."""
    pub = doc.get("publishedAt")
    pub_iso = pub.isoformat() if pub else ""
    return f"{pub_iso}|{str(doc['_id'])}"


def _decode_cursor(cursor: str):
    """Decode a cursor string back into (publishedAt, ObjectId) for use in a MongoDB $or query.
    Raises HTTP 400 if the cursor is malformed."""
    try:
        pub_iso, id_hex = cursor.rsplit("|", 1)
        pub = datetime.fromisoformat(pub_iso) if pub_iso else None
        return pub, ObjectId(id_hex)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")


# --- Public news feed ---

async def list_public_feed(
    limit: int,
    cursor: Optional[str],
    chartId: Optional[str],
    tag: Optional[str],
) -> dict:
    """Return a paginated list of public posts, optionally filtered by chartId and/or tag.
    Results are sorted newest-first. Pass the returned nextCursor to fetch the next page."""
    match: dict = {"public": True}
    if chartId:
        match["chartId"] = chartId
    if tag:
        match["tags"] = tag
    if cursor:
        pub, oid = _decode_cursor(cursor)
        match["$or"] = [
            {"publishedAt": {"$lt": pub}},
            {"publishedAt": pub, "_id": {"$lt": oid}},
        ]

    pipeline = [
        {"$match": match},
        {"$sort": {"publishedAt": -1, "_id": -1}},
        {"$limit": limit + 1},
        {"$lookup": {"from": "charts_meta", "localField": "chartId",
                     "foreignField": "_id", "as": "chart"}},
        {"$lookup": {"from": "users", "localField": "authorId",
                     "foreignField": "_id", "as": "author"}},
        {"$addFields": {
            "chartName": {"$first": "$chart.name"},
            "authorName": {"$first": "$author.fullName"},
        }},
        {"$project": {"contentHtml": 0, "chart": 0, "author": 0}},
    ]
    docs = await _news_coll().aggregate(pipeline).to_list(length=limit + 1)

    # Fetch one extra doc to check if there is a next page without a separate count query.
    next_cursor = None
    if len(docs) > limit:
        docs = docs[:limit]
        next_cursor = _encode_cursor(docs[-1])
    return {"items": [_doc_to_card(d) for d in docs], "nextCursor": next_cursor}


async def list_public_tags() -> list[dict]:
    """Return the distinct tags used across public posts, each with the number of public
    posts carrying it. Sorted by count desc, then tag asc."""
    pipeline = [
        {"$match": {"public": True}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]
    docs = await _news_coll().aggregate(pipeline).to_list(length=1000)
    return [{"tag": d["_id"], "count": d["count"]} for d in docs]


async def get_public_post(postId: str) -> dict:
    """Fetch a single public post by ID. Returns HTTP 404 if the post doesn't exist or is private."""
    oid = _parse_object_id(postId)
    doc = await _news_coll().find_one({"_id": oid, "public": True})
    if not doc:
        raise HTTPException(status_code=404, detail="News post not found")
    return _doc_to_out(doc)


# --- Chart-scoped news management ---

async def list_chart_news(
    chartId: str,
    author_id: Optional[str],
    public: Optional[bool],
    tag: Optional[str],
) -> list[dict]:
    """Return all posts belonging to a chart, newest first.
    Can be filtered by author, visibility (public/private), and tag.
    Includes authorName via a lookup but excludes contentHtml for a lighter payload."""
    match: dict = {"chartId": chartId}
    if author_id:
        match["authorId"] = author_id
    if public is not None:
        match["public"] = public
    if tag:
        match["tags"] = tag

    pipeline = [
        {"$match": match},
        {"$sort": {"createdAt": -1}},
        {"$lookup": {"from": "users", "localField": "authorId",
                     "foreignField": "_id", "as": "author"}},
        {"$addFields": {"authorName": {"$first": "$author.fullName"}}},
        {"$project": {"contentHtml": 0, "author": 0}},
    ]
    docs = await _news_coll().aggregate(pipeline).to_list(length=1000)
    return [_doc_to_card(d) for d in docs]


async def get_post_raw(chartId: str, postId: str) -> dict:
    """Fetch the raw MongoDB document (including authorId) for permission checks in the router."""
    oid = _parse_object_id(postId)
    doc = await _news_coll().find_one({"_id": oid, "chartId": chartId})
    if not doc:
        raise HTTPException(status_code=404, detail="News post not found")
    return doc


async def get_chart_post(chartId: str, postId: str) -> dict:
    """Fetch a post by chartId + postId and return the full NewsOut shape (includes contentHtml)."""
    return _doc_to_out(await get_post_raw(chartId, postId))


async def create_news(chartId: str, authorId: str, body: NewsCreate) -> dict:
    """Insert a new news post. If the post is created as public, publishedAt is set immediately."""
    now = _now()
    content_html = sanitize_html(body.contentHtml)
    content_image_urls = extract_content_image_urls(content_html)
    doc = {
        "chartId": chartId,
        "authorId": authorId,
        "title": body.title.strip(),
        "contentHtml": content_html,
        "contentImageUrls": content_image_urls,
        "coverImageUrl": body.coverImageUrl,
        "tags": body.tags,
        "public": body.public,
        "publishedAt": now if body.public else None,
        "createdAt": now,
        "updatedAt": now,
    }
    res = await _news_coll().insert_one(doc)
    doc["_id"] = res.inserted_id
    await _cleanup_draft_orphans(body.draftPhotoUrls, content_image_urls + [body.coverImageUrl])
    return _doc_to_out(doc)


async def update_news(chartId: str, postId: str, patch: dict) -> dict:
    """Apply a partial update to an existing post.
    Title and contentHtml are sanitized if present in the patch."""
    if not patch:
        raise HTTPException(status_code=400, detail="Nothing to update")
    oid = _parse_object_id(postId)
    existing = await _news_coll().find_one({"_id": oid, "chartId": chartId})
    if not existing:
        raise HTTPException(status_code=404, detail="News post not found")

    update_doc = dict(patch)
    # draftPhotoUrls is a transient cleanup hint, not a stored field — pull it out before $set.
    draft_photo_urls = update_doc.pop("draftPhotoUrls", None)
    if update_doc.get("title") is not None:
        update_doc["title"] = update_doc["title"].strip()
    # Body images the user removed during this edit. draftPhotoUrls only covers freshly
    # uploaded images; an image that was already in the saved post and got deleted from the
    # new contentHtml would otherwise be orphaned on Cloudinary, so track it for cleanup too.
    removed_body_images: list[str] = []
    if update_doc.get("contentHtml") is not None:
        update_doc["contentHtml"] = sanitize_html(update_doc["contentHtml"])
        # Recompute the stored Cloudinary image list whenever the body changes.
        new_image_urls = extract_content_image_urls(update_doc["contentHtml"])
        update_doc["contentImageUrls"] = new_image_urls
        removed_body_images = [
            u for u in (existing.get("contentImageUrls") or []) if u not in new_image_urls
        ]

    # publishedAt is stamped the very first time a post goes public.
    # It is intentionally never cleared — even if the post is later set back to private —
    # so the original publish date is preserved as a historical record.
    merged_public = update_doc.get("public", existing.get("public", False))
    if merged_public and not existing.get("publishedAt"):
        update_doc["publishedAt"] = _now()

    update_doc["updatedAt"] = _now()
    await _news_coll().update_one({"_id": oid}, {"$set": update_doc})
    doc = await _news_coll().find_one({"_id": oid})

    # Clean up images that aren't referenced by the saved post (body images + cover): both
    # leftover draft uploads and body images removed in this edit. Anything still referenced
    # (e.g. a removed body image that is also the cover) is kept by the kept_urls guard.
    kept_urls = list(doc.get("contentImageUrls") or [])
    kept_urls.append(doc.get("coverImageUrl"))
    candidate_orphans = list(draft_photo_urls or []) + removed_body_images
    await _cleanup_draft_orphans(candidate_orphans, kept_urls)

    return _doc_to_out(doc)


async def delete_news(chartId: str, postId: str) -> bool:
    """Permanently delete a post, first cleaning up its Cloudinary images (embedded body images
    plus the cover image). Cloudinary cleanup is best-effort — failures are logged, not raised —
    so the post is always removed from the database. Returns HTTP 404 if the post doesn't exist."""
    oid = _parse_object_id(postId)
    doc = await _news_coll().find_one({"_id": oid, "chartId": chartId})
    if not doc:
        raise HTTPException(status_code=404, detail="News post not found")

    image_urls = list(doc.get("contentImageUrls") or [])
    if doc.get("coverImageUrl"):
        image_urls.append(doc["coverImageUrl"])
    await delete_images(image_urls)

    await _news_coll().delete_one({"_id": oid})
    return True


async def delete_news_by_chart(chartId: str) -> int:
    """Delete every news post belonging to a chart, cleaning up all their Cloudinary
    images (embedded body images plus cover images) first. Cloudinary cleanup is
    best-effort. Returns the number of posts deleted. Used when a chart is hard-deleted."""
    image_urls: list[str] = []
    cursor = _news_coll().find(
        {"chartId": chartId},
        {"contentImageUrls": 1, "coverImageUrl": 1},
    )
    async for doc in cursor:
        image_urls.extend(doc.get("contentImageUrls") or [])
        if doc.get("coverImageUrl"):
            image_urls.append(doc["coverImageUrl"])

    if image_urls:
        await delete_images(image_urls)

    res = await _news_coll().delete_many({"chartId": chartId})
    return res.deleted_count
