from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

PUBLIC_BSKY_API_BASE_URL = "https://public.api.bsky.app/xrpc"
DEFAULT_USER_AGENT = "Postmortem/0.1"


class BlueskyClient:
    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[dict[str, Any]]:
        sources = self.config.get("sources", {})
        post_urls = sources.get("bluesky_post_urls") or []
        top_n_replies = int(self.config.get("comments", {}).get("top_n_per_candidate", 5))
        depth = int(sources.get("bluesky_reply_depth", top_n_replies))

        candidates_by_id: dict[str, dict[str, Any]] = {}
        for post_url in post_urls:
            thread_uri = self._post_url_to_at_uri(post_url)
            thread_payload = self._fetch_thread(thread_uri, depth=depth)
            candidate = self._normalize_thread(thread_payload, canonical_url=post_url, top_n_replies=top_n_replies)
            source_id = candidate["source_id"]
            if source_id not in candidates_by_id:
                candidates_by_id[source_id] = candidate
        return list(candidates_by_id.values())

    def _fetch_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_url_to_at_uri(self, post_url: str) -> str:
        if post_url.startswith("at://"):
            return post_url

        parsed = urllib.parse.urlparse(post_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 4 or path_parts[0] != "profile" or path_parts[2] != "post":
            raise ValueError(f"Unsupported Bluesky post URL: {post_url}")

        handle = path_parts[1]
        rkey = path_parts[3]
        did = self._resolve_handle(handle)
        return f"at://{did}/app.bsky.feed.post/{rkey}"

    def _resolve_handle(self, handle: str) -> str:
        query = urllib.parse.urlencode({"handle": handle})
        payload = self._fetch_json(f"{PUBLIC_BSKY_API_BASE_URL}/com.atproto.identity.resolveHandle?{query}")
        did = payload.get("did")
        if not did:
            raise ValueError(f"Bluesky handle resolution did not return a DID for {handle}")
        return str(did)

    def _fetch_thread(self, uri: str, depth: int) -> dict[str, Any]:
        query = urllib.parse.urlencode({"uri": uri, "depth": depth, "parentHeight": 0})
        return self._fetch_json(f"{PUBLIC_BSKY_API_BASE_URL}/app.bsky.feed.getPostThread?{query}")

    def _normalize_thread(self, thread_payload: dict[str, Any], canonical_url: str, top_n_replies: int) -> dict[str, Any]:
        thread = thread_payload.get("thread", {})
        post = thread.get("post", {})
        record = post.get("record", {})
        author = post.get("author", {})
        text = str(record.get("text") or "")
        source_id = str(post.get("uri") or "")
        author_handle = str(author.get("handle") or "bluesky")

        return {
            "source": "bluesky",
            "source_id": source_id,
            "candidate_id": f"bluesky:{source_id}",
            "source_community": author_handle,
            "title": self._title_from_text(text),
            "body": text,
            "url": canonical_url,
            "author": author_handle,
            "created_utc": self._created_at_to_epoch(record.get("createdAt")),
            "score": self._engagement_score(post),
            "comment_count": int(post.get("replyCount") or 0),
            "raw_json": {"uri": source_id, "source": "bluesky"},
            "top_comments": self._normalize_replies(thread.get("replies") or [], top_n_replies),
        }

    def _normalize_replies(self, replies: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        normalized = []
        for reply in self._flatten_reply_posts(replies):
            record = reply.get("record", {})
            text = str(record.get("text") or "")
            if not text.strip():
                continue
            normalized.append(
                {
                    "comment_id": str(reply.get("uri") or ""),
                    "body": text,
                    "score": self._engagement_score(reply),
                    "author": str(reply.get("author", {}).get("handle") or ""),
                    "created_utc": self._created_at_to_epoch(record.get("createdAt")),
                }
            )
        normalized.sort(key=lambda reply: int(reply.get("score") or 0), reverse=True)
        return normalized[:limit]

    def _flatten_reply_posts(self, replies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for reply in replies:
            post = reply.get("post")
            if isinstance(post, dict):
                output.append(post)
            child_replies = reply.get("replies")
            if isinstance(child_replies, list):
                output.extend(self._flatten_reply_posts(child_replies))
        return output

    def _engagement_score(self, post: dict[str, Any]) -> int:
        return int(post.get("likeCount") or 0) + int(post.get("repostCount") or 0) + int(post.get("quoteCount") or 0) + int(post.get("replyCount") or 0)

    def _created_at_to_epoch(self, created_at: Any) -> int:
        if not created_at:
            return 0
        value = str(created_at)
        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())

    def _title_from_text(self, text: str) -> str:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Untitled Bluesky thread")
        if len(first_line) <= 120:
            return first_line
        return f"{first_line[:119].rstrip()}…"
