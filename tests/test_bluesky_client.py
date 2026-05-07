import json
import urllib.request

from reddit_automation.clients.bluesky_client import BlueskyClient
from reddit_automation.pipeline.fetch import fetch_candidates


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _thread_payload():
    return {
        "thread": {
            "$type": "app.bsky.feed.defs#threadViewPost",
            "post": {
                "uri": "at://did:plc:alice/app.bsky.feed.post/3kabc",
                "cid": "bafycidroot",
                "author": {
                    "did": "did:plc:alice",
                    "handle": "alice.example",
                    "displayName": "Alice",
                },
                "record": {
                    "text": "I accidentally started office chaos by labeling the fridge shelf 'evidence'.\nEveryone took it too seriously.",
                    "createdAt": "2026-05-07T12:30:00.000Z",
                },
                "likeCount": 12,
                "repostCount": 5,
                "replyCount": 2,
                "quoteCount": 1,
            },
            "replies": [
                {
                    "$type": "app.bsky.feed.defs#threadViewPost",
                    "post": {
                        "uri": "at://did:plc:bob/app.bsky.feed.post/3kdef",
                        "author": {"handle": "bob.example"},
                        "record": {
                            "text": "HR seeing the word evidence on dairy products is objectively funny.",
                            "createdAt": "2026-05-07T12:31:00.000Z",
                        },
                        "likeCount": 40,
                        "repostCount": 3,
                        "replyCount": 1,
                    },
                },
                {
                    "$type": "app.bsky.feed.defs#threadViewPost",
                    "post": {
                        "uri": "at://did:plc:carol/app.bsky.feed.post/3kghi",
                        "author": {"handle": "carol.example"},
                        "record": {
                            "text": "This is how every office gets a fridge policy.",
                            "createdAt": "2026-05-07T12:32:00.000Z",
                        },
                        "likeCount": 9,
                        "repostCount": 0,
                        "replyCount": 0,
                    },
                },
            ],
        }
    }


def test_bluesky_client_fetches_public_thread_url_and_normalizes_to_pipeline_candidate(monkeypatch):
    requested_urls = []

    def fake_urlopen(request, timeout=30):
        requested_urls.append(request.full_url)
        if request.full_url.startswith("https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle"):
            assert "handle=alice.example" in request.full_url
            return FakeResponse({"did": "did:plc:alice"})
        if request.full_url.startswith("https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"):
            assert "uri=at%3A%2F%2Fdid%3Aplc%3Aalice%2Fapp.bsky.feed.post%2F3kabc" in request.full_url
            assert "depth=2" in request.full_url
            return FakeResponse(_thread_payload())
        raise AssertionError(f"unexpected URL: {request.full_url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    candidates = BlueskyClient(
        {
            "comments": {"top_n_per_candidate": 2},
            "sources": {
                "bluesky_post_urls": ["https://bsky.app/profile/alice.example/post/3kabc"],
                "bluesky_reply_depth": 2,
            },
        }
    ).fetch()

    assert requested_urls == [
        "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=alice.example",
        "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri=at%3A%2F%2Fdid%3Aplc%3Aalice%2Fapp.bsky.feed.post%2F3kabc&depth=2&parentHeight=0",
    ]
    assert candidates == [
        {
            "source": "bluesky",
            "source_id": "at://did:plc:alice/app.bsky.feed.post/3kabc",
            "candidate_id": "bluesky:at://did:plc:alice/app.bsky.feed.post/3kabc",
            "source_community": "bluesky",
            "source_community": "alice.example",
            "title": "I accidentally started office chaos by labeling the fridge shelf 'evidence'.",
            "body": "I accidentally started office chaos by labeling the fridge shelf 'evidence'.\nEveryone took it too seriously.",
            "url": "https://bsky.app/profile/alice.example/post/3kabc",
            "author": "alice.example",
            "created_utc": 1778157000,
            "score": 20,
            "comment_count": 2,
            "raw_json": {"uri": "at://did:plc:alice/app.bsky.feed.post/3kabc", "source": "bluesky"},
            "top_comments": [
                {
                    "comment_id": "at://did:plc:bob/app.bsky.feed.post/3kdef",
                    "body": "HR seeing the word evidence on dairy products is objectively funny.",
                    "score": 44,
                    "author": "bob.example",
                    "created_utc": 1778157060,
                },
                {
                    "comment_id": "at://did:plc:carol/app.bsky.feed.post/3kghi",
                    "body": "This is how every office gets a fridge policy.",
                    "score": 9,
                    "author": "carol.example",
                    "created_utc": 1778157120,
                },
            ],
        }
    ]


def test_fetch_candidates_dispatches_bluesky_mode_without_reddit_credentials(monkeypatch):
    def fake_urlopen(request, timeout=30):
        if "resolveHandle" in request.full_url:
            return FakeResponse({"did": "did:plc:alice"})
        if "getPostThread" in request.full_url:
            return FakeResponse(_thread_payload())
        raise AssertionError(f"unexpected URL: {request.full_url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    candidates = fetch_candidates(
        {
            "comments": {"top_n_per_candidate": 1},
            "sources": {
                "source_mode": "bluesky",
                "bluesky_post_urls": ["https://bsky.app/profile/alice.example/post/3kabc"],
            },
        }
    )

    assert len(candidates) == 1
    assert candidates[0]["source"] == "bluesky"
    assert candidates[0]["candidate_id"].startswith("bluesky:at://")
    assert len(candidates[0]["top_comments"]) == 1
