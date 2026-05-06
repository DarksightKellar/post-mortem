from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PUBLIC_REDDIT_LISTING_TYPES = ("hot", "top")
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE_URL = "https://oauth.reddit.com"
DEFAULT_USER_AGENT = "Postmortem/0.1 by u/unknown"


class RedditClient:
    def __init__(self, config: dict, sleep_fn=None):
        self.config = config
        self._sleep = sleep_fn or time.sleep
        self._oauth_token: str | None = None
        self._last_request_at: float | None = None

    def normalize_submission(self, submission: dict[str, Any], top_n_comments: int) -> dict[str, Any]:
        return {
            "reddit_post_id": submission["id"],
            "subreddit": submission["subreddit"],
            "title": submission["title"],
            "body": submission.get("selftext", ""),
            "url": submission["url"],
            "author": submission.get("author"),
            "created_utc": submission["created_utc"],
            "score": submission.get("score", 0),
            "comment_count": submission.get("num_comments", 0),
            "raw_json": {"id": submission["id"]},
            "top_comments": [
                {
                    "comment_id": comment["id"],
                    "body": comment["body"],
                    "score": comment.get("score", 0),
                    "author": comment.get("author"),
                    "created_utc": comment.get("created_utc"),
                }
                for comment in submission.get("comments", [])[:top_n_comments]
            ],
        }

    def _get_test_submissions(self) -> list[dict[str, Any]] | None:
        reddit_test_data = self.config.get("reddit_test_data", {})
        submissions = reddit_test_data.get("submissions")
        return submissions if submissions else None

    def _get_public_subreddits(self) -> list[str] | None:
        subreddits = self.config.get("sources", {}).get("subreddits")
        return subreddits if subreddits else None

    def _get_post_urls(self) -> list[str] | None:
        post_urls = self.config.get("sources", {}).get("reddit_post_urls")
        return post_urls if post_urls else None

    def _source_mode(self) -> str | None:
        sources = self.config.get("sources", {})
        explicit_mode = sources.get("source_mode")
        if explicit_mode:
            return str(explicit_mode)
        if self._get_post_urls() is not None:
            return "post_urls"
        if self._get_public_subreddits() is not None:
            return "subreddits"
        return None

    def _reddit_config_value(self, key: str, env_name: str | None = None, default: Any = None) -> Any:
        value = self.config.get("reddit", {}).get(key)
        if value not in (None, ""):
            return value
        if env_name:
            env_value = os.getenv(env_name)
            if env_value not in (None, ""):
                return env_value
        return default

    def _reddit_retry_config(self) -> tuple[int, float]:
        reddit_config = self.config.get("reddit", {})
        retry_config = self.config.get("retry", {})
        max_retries = reddit_config.get("max_retries", retry_config.get("max_retries", 3))
        base_delay = reddit_config.get("base_delay_seconds", retry_config.get("base_delay", 2.0))
        return int(max_retries), float(base_delay)

    def _user_agent(self) -> str:
        return str(self._reddit_config_value("user_agent", "REDDIT_USER_AGENT", DEFAULT_USER_AGENT))

    def _require_oauth_credentials(self) -> tuple[str, str, str]:
        client_id = self._reddit_config_value("client_id", "REDDIT_CLIENT_ID")
        client_secret = self._reddit_config_value("client_secret", "REDDIT_CLIENT_SECRET")
        user_agent = self._user_agent()
        if not client_id or not client_secret:
            raise ValueError(
                "RedditClient live fetch requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET "
                "or config['reddit'].client_id/client_secret."
            )
        return str(client_id), str(client_secret), user_agent

    def _request_access_token(self) -> str:
        client_id, client_secret, user_agent = self._require_oauth_credentials()
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        request = urllib.request.Request(
            REDDIT_TOKEN_URL,
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {credentials}",
                "User-Agent": user_agent,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        payload = self._open_json(request)
        token = payload.get("access_token")
        if not token:
            raise ValueError("Reddit OAuth token response did not include access_token")
        return str(token)

    def _get_oauth_token(self) -> str:
        if self._oauth_token is None:
            self._oauth_token = self._request_access_token()
        return self._oauth_token

    def _pace_request(self) -> None:
        min_seconds = float(self.config.get("reddit", {}).get("min_seconds_between_requests", 0) or 0)
        if min_seconds <= 0 or self._last_request_at is None:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < min_seconds:
            self._sleep(min_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _open_json(self, request: urllib.request.Request) -> Any:
        max_retries, base_delay = self._reddit_retry_config()
        for attempt in range(1, max_retries + 1):
            try:
                self._pace_request()
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= max_retries:
                    raise
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = float(retry_after) if retry_after else base_delay * (2 ** (attempt - 1))
                self._sleep(delay)

        raise RuntimeError("unreachable Reddit retry state")

    def _fetch_json(self, url: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._get_oauth_token()}",
                "User-Agent": self._user_agent(),
            },
        )
        return self._open_json(request)

    def _build_listing_url(self, subreddit: str, mode: str, limit: int) -> str:
        subreddit_path = urllib.parse.quote(subreddit, safe="")
        base_url = f"{REDDIT_API_BASE_URL}/r/{subreddit_path}/{mode}.json"
        query_params: dict[str, str | int] = {"limit": limit, "raw_json": 1}
        if mode == "top":
            query_params["t"] = "day"
        return f"{base_url}?{urllib.parse.urlencode(query_params)}"

    def _build_comments_url(self, permalink: str, limit: int) -> str:
        clean_permalink = permalink.rstrip("/")
        parsed = urllib.parse.urlparse(clean_permalink)
        path = parsed.path if parsed.scheme else clean_permalink
        return f"{REDDIT_API_BASE_URL}{path}/.json?limit={limit}&raw_json=1"

    def _build_public_post_url(self, post_url: str, limit: int) -> str:
        clean_url = post_url.rstrip("/")
        parsed = urllib.parse.urlparse(clean_url)
        if parsed.scheme and parsed.netloc:
            path = parsed.path
        else:
            path = clean_url
        if not path.startswith("/"):
            path = f"/{path}"
        return f"https://www.reddit.com{path}/.json?limit={limit}&raw_json=1"

    def _extract_comments_from_thread_payload(self, thread_payload: Any, limit: int) -> list[dict[str, Any]]:
        if len(thread_payload) < 2:
            return []
        comment_listing = thread_payload[1].get("data", {}).get("children", [])
        return [
            child["data"]
            for child in comment_listing
            if child.get("kind") == "t1" and child.get("data", {}).get("body")
        ][:limit]

    def _fetch_comments(self, permalink: str, limit: int) -> list[dict[str, Any]]:
        comments_payload = self._fetch_json(self._build_comments_url(permalink, limit))
        return self._extract_comments_from_thread_payload(comments_payload, limit)

    def _fetch_post_url_submissions(self, post_urls: list[str], top_n_comments: int) -> list[dict[str, Any]]:
        submissions_by_id: dict[str, dict[str, Any]] = {}
        for post_url in post_urls:
            try:
                thread_payload = self._open_json(
                    urllib.request.Request(
                        self._build_public_post_url(post_url, top_n_comments),
                        headers={"User-Agent": self._user_agent()},
                    )
                )
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 429):
                    raise ValueError(
                        "Reddit blocked fetching the configured post URL. Paste the post title, body, "
                        "and useful comments into config['reddit_test_data']['submissions'] instead. "
                        f"Blocked URL: {post_url}"
                    ) from exc
                raise
            post_listing = thread_payload[0].get("data", {}).get("children", []) if thread_payload else []
            if not post_listing:
                continue
            submission = dict(post_listing[0].get("data", {}))
            submission_id = submission.get("id")
            if not submission_id or submission_id in submissions_by_id:
                continue
            submission["url"] = submission.get("url") or post_url
            submission["comments"] = self._extract_comments_from_thread_payload(thread_payload, top_n_comments)
            submissions_by_id[submission_id] = submission
        return list(submissions_by_id.values())

    def _fetch_public_submissions(self, top_n_comments: int) -> list[dict[str, Any]]:
        sources = self.config.get("sources", {})
        subreddits = sources.get("subreddits", [])
        listing_limit = sources.get("max_posts_per_subreddit_per_mode", 15)
        comment_thread_budget = int(self.config.get("reddit", {}).get("max_comment_threads_per_run", 10))
        submissions_by_id: dict[str, dict[str, Any]] = {}

        for subreddit in subreddits:
            for mode in PUBLIC_REDDIT_LISTING_TYPES:
                listing_payload = self._fetch_json(self._build_listing_url(subreddit, mode, listing_limit))
                listing_children = listing_payload.get("data", {}).get("children", [])
                for child in listing_children:
                    submission_data = child.get("data", {})
                    submission_id = submission_data.get("id")
                    permalink = submission_data.get("permalink")
                    if not submission_id or not permalink or submission_id in submissions_by_id:
                        continue

                    submission = dict(submission_data)
                    submission["url"] = submission.get("url") or f"https://www.reddit.com{permalink}"
                    submission["comments"] = []
                    submissions_by_id[submission_id] = submission

        submissions = sorted(
            submissions_by_id.values(),
            key=lambda submission: int(submission.get("score") or 0),
            reverse=True,
        )
        for submission in submissions[:comment_thread_budget]:
            permalink = submission.get("permalink")
            if permalink:
                submission["comments"] = self._fetch_comments(permalink, top_n_comments)

        return submissions

    def fetch(self) -> list[dict[str, Any]]:
        top_n_comments = self.config.get("comments", {}).get("top_n_per_candidate", 5)
        submissions = self._get_test_submissions()
        if submissions is not None:
            return [
                self.normalize_submission(submission, top_n_comments=top_n_comments)
                for submission in submissions
            ]

        source_mode = self._source_mode()
        post_urls = self._get_post_urls()
        if source_mode == "post_urls" and post_urls is not None:
            submissions = self._fetch_post_url_submissions(post_urls, top_n_comments=top_n_comments)
            return [
                self.normalize_submission(submission, top_n_comments=top_n_comments)
                for submission in submissions
            ]

        if source_mode == "subreddits" and self._get_public_subreddits() is not None:
            self._require_oauth_credentials()
            submissions = self._fetch_public_submissions(top_n_comments=top_n_comments)
            return [
                self.normalize_submission(submission, top_n_comments=top_n_comments)
                for submission in submissions
            ]

        raise ValueError(
            "RedditClient requires config['reddit_test_data']['submissions'], "
            "config['sources']['reddit_post_urls'], or config['sources']['subreddits'] "
            "plus authenticated config['reddit'] credentials."
        )
