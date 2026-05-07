import base64
import json
import urllib.error
import urllib.request
from io import BytesIO

import pytest

from reddit_automation.clients.reddit_client import RedditClient


def _submission(post_id="abc123", *, score=420, permalink="/r/AskReddit/comments/abc123/funniest_thing/"):
    return {
        "id": post_id,
        "source_community": "AskReddit",
        "title": "What is the funniest thing that happened at work?",
        "selftext": "Someone microwaved fish and the office melted down.",
        "url": f"https://reddit.com/r/AskReddit/comments/{post_id}",
        "permalink": permalink,
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": score,
        "num_comments": 37,
        "comments": [
            {
                "id": "c1",
                "body": "This should qualify as chemical warfare.",
                "score": 101,
                "author": "user1",
                "created_utc": 1712345680,
            },
            {
                "id": "c2",
                "body": "Microwaved fish is a hostile work environment.",
                "score": 99,
                "author": "user2",
                "created_utc": 1712345685,
            },
        ],
    }


def _listing_payload(*submissions):
    return {"data": {"children": [{"kind": "t3", "data": submission} for submission in submissions]}}


def _comments_payload():
    return [
        {"data": {"children": []}},
        {
            "data": {
                "children": [
                    {"kind": "t1", "data": _submission()["comments"][0]},
                    {"kind": "t1", "data": _submission()["comments"][1]},
                ]
            }
        },
    ]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _oauth_config(**reddit_overrides):
    reddit = {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "user_agent": "Postmortem/0.1 by u/kelvin",
        "max_retries": 2,
        "base_delay_seconds": 0.1,
        "min_seconds_between_requests": 0,
        "max_comment_threads_per_run": 10,
    }
    reddit.update(reddit_overrides)
    return {
        "comments": {"top_n_per_candidate": 2},
        "sources": {
            "subreddits": ["AskReddit"],
            "max_posts_per_subreddit_per_mode": 1,
        },
        "reddit": reddit,
    }


def _fake_token_response():
    return FakeResponse({"access_token": "token-123", "token_type": "bearer", "expires_in": 3600})


def test_normalize_submission_builds_candidate_dict_with_top_comments():
    client = RedditClient(config={})

    candidate = client.normalize_submission(_submission(), top_n_comments=2)

    assert candidate == {
        "candidate_id": "reddit:abc123",
        "source": "reddit",
        "source_id": "abc123",
        "source_community": "AskReddit",
        "title": "What is the funniest thing that happened at work?",
        "body": "Someone microwaved fish and the office melted down.",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 420,
        "comment_count": 37,
        "raw_json": {"id": "abc123", "source": "reddit"},
        "top_comments": [
            {
                "comment_id": "c1",
                "body": "This should qualify as chemical warfare.",
                "score": 101,
                "author": "user1",
                "created_utc": 1712345680,
            },
            {
                "comment_id": "c2",
                "body": "Microwaved fish is a hostile work environment.",
                "score": 99,
                "author": "user2",
                "created_utc": 1712345685,
            },
        ],
    }


def test_normalize_submission_limits_top_comments_to_requested_count():
    client = RedditClient(config={})

    candidate = client.normalize_submission(_submission(), top_n_comments=1)

    assert candidate["top_comments"] == [
        {
            "comment_id": "c1",
            "body": "This should qualify as chemical warfare.",
            "score": 101,
            "author": "user1",
            "created_utc": 1712345680,
        }
    ]


def test_fetch_returns_normalized_candidates_from_configured_raw_submissions(monkeypatch):
    def fail_if_network_is_used(*args, **kwargs):
        raise AssertionError("fixture fetch must not call the network")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_network_is_used)
    client = RedditClient(
        config={
            "comments": {"top_n_per_candidate": 2},
            "reddit_test_data": {"submissions": [_submission()]},
        }
    )

    candidates = client.fetch()

    assert candidates[0]["candidate_id"] == "reddit:abc123"
    assert len(candidates[0]["top_comments"]) == 2


def test_fetch_raises_clear_error_when_no_test_data_or_public_sources_are_present():
    client = RedditClient(config={"comments": {"top_n_per_candidate": 2}})

    with pytest.raises(ValueError) as exc:
        client.fetch()

    assert str(exc.value) == (
        "RedditClient requires config['reddit_test_data']['submissions'], "
        "config['sources']['reddit_post_urls'], or config['sources']['subreddits'] "
        "plus authenticated config['reddit'] credentials."
    )


def test_fetches_configured_reddit_post_urls_without_oauth(monkeypatch):
    requested_urls = []
    thread_url = "https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"

    def fake_urlopen(request, timeout=30):
        requested_urls.append(request.full_url)
        if request.full_url == "https://www.reddit.com/api/v1/access_token":
            raise AssertionError("post URL mode must not request OAuth credentials")
        assert request.get_header("User-agent") == "Postmortem/0.1 by u/unknown"
        assert request.full_url == f"{thread_url}.json?limit=2&raw_json=1"
        return FakeResponse([_listing_payload(_submission()), _comments_payload()[1]])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = RedditClient(
        {
            "comments": {"top_n_per_candidate": 2},
            "sources": {"reddit_post_urls": [thread_url], "subreddits": ["AskReddit"]},
        }
    )

    candidates = client.fetch()

    assert requested_urls == [f"{thread_url}.json?limit=2&raw_json=1"]
    assert candidates[0]["candidate_id"] == "reddit:abc123"
    assert candidates[0]["top_comments"] == [
        {
            "comment_id": "c1",
            "body": "This should qualify as chemical warfare.",
            "score": 101,
            "author": "user1",
            "created_utc": 1712345680,
        },
        {
            "comment_id": "c2",
            "body": "Microwaved fish is a hostile work environment.",
            "score": 99,
            "author": "user2",
            "created_utc": 1712345685,
        },
    ]



def test_post_url_mode_explains_manual_fallback_when_reddit_blocks_fetch(monkeypatch):
    thread_url = "https://www.reddit.com/r/AskReddit/comments/abc123/funniest_thing/"

    def fake_urlopen(request, timeout=30):
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            {"Retry-After": "1"},
            BytesIO(b"rate limited"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = RedditClient(
        {
            "comments": {"top_n_per_candidate": 2},
            "sources": {"reddit_post_urls": [thread_url]},
            "reddit": {"max_retries": 1},
        }
    )

    with pytest.raises(ValueError) as exc:
        client.fetch()

    assert str(exc.value) == (
        "Reddit blocked fetching the configured post URL. Paste the post title, body, "
        "and useful comments into config['reddit_test_data']['submissions'] instead. "
        f"Blocked URL: {thread_url}"
    )



def test_live_fetch_uses_oauth_token_and_authenticated_reddit_host(monkeypatch):
    requests = []
    expected_basic = base64.b64encode(b"client-id:client-secret").decode("ascii")

    def fake_urlopen(request, timeout=30):
        requests.append(request)
        if request.full_url == "https://www.reddit.com/api/v1/access_token":
            assert request.get_header("Authorization") == f"Basic {expected_basic}"
            assert request.get_header("User-agent") == "Postmortem/0.1 by u/kelvin"
            assert request.data == b"grant_type=client_credentials"
            return _fake_token_response()
        assert request.full_url.startswith("https://oauth.reddit.com/r/AskReddit/")
        assert request.get_header("Authorization") == "Bearer token-123"
        assert request.get_header("User-agent") == "Postmortem/0.1 by u/kelvin"
        return FakeResponse(_listing_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    candidates = RedditClient(_oauth_config()).fetch()

    assert candidates == []
    assert [request.full_url for request in requests] == [
        "https://www.reddit.com/api/v1/access_token",
        "https://oauth.reddit.com/r/AskReddit/hot.json?limit=1&raw_json=1",
        "https://oauth.reddit.com/r/AskReddit/top.json?limit=1&raw_json=1&t=day",
    ]


def test_live_fetch_retries_429_with_retry_after_before_failing_or_continuing(monkeypatch):
    data_request_count = 0
    sleep_calls = []

    def fake_urlopen(request, timeout=30):
        nonlocal data_request_count
        if request.full_url == "https://www.reddit.com/api/v1/access_token":
            return _fake_token_response()
        data_request_count += 1
        if data_request_count == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {"Retry-After": "7"},
                BytesIO(b"rate limited"),
            )
        return FakeResponse(_listing_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    candidates = RedditClient(_oauth_config(max_retries=2), sleep_fn=sleep_calls.append).fetch()

    assert candidates == []
    assert sleep_calls == [7.0]
    assert data_request_count == 3


def test_live_fetch_gets_comments_only_for_top_budgeted_candidates_after_deduping(monkeypatch):
    requested_urls = []
    low_score = _submission("low", score=10, permalink="/r/AskReddit/comments/low/low_score/")
    high_score = _submission("high", score=999, permalink="/r/AskReddit/comments/high/high_score/")

    def fake_urlopen(request, timeout=30):
        requested_urls.append(request.full_url)
        if request.full_url == "https://www.reddit.com/api/v1/access_token":
            return _fake_token_response()
        if request.full_url.endswith("/hot.json?limit=2&raw_json=1"):
            return FakeResponse(_listing_payload(low_score, high_score))
        if request.full_url.endswith("/top.json?limit=2&raw_json=1&t=day"):
            return FakeResponse(_listing_payload(high_score))
        if request.full_url.endswith("/comments/high/high_score/.json?limit=2&raw_json=1"):
            return FakeResponse(_comments_payload())
        raise AssertionError(f"unexpected URL requested: {request.full_url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    config = _oauth_config(max_comment_threads_per_run=1)
    config["sources"]["max_posts_per_subreddit_per_mode"] = 2

    candidates = RedditClient(config).fetch()

    comment_urls = [url for url in requested_urls if "/comments/" in url]
    assert comment_urls == ["https://oauth.reddit.com/r/AskReddit/comments/high/high_score/.json?limit=2&raw_json=1"]
    assert [candidate["candidate_id"] for candidate in candidates] == ["reddit:high", "reddit:low"]
    assert len(candidates[0]["top_comments"]) == 2
    assert candidates[1]["top_comments"] == []
