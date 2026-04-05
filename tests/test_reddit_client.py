from reddit_automation.clients.reddit_client import RedditClient


def test_normalize_submission_builds_candidate_dict_with_top_comments():
    client = RedditClient(config={})
    submission = {
        "id": "abc123",
        "subreddit": "AskReddit",
        "title": "What is the funniest thing that happened at work?",
        "selftext": "Someone microwaved fish and the office melted down.",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 420,
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

    candidate = client.normalize_submission(submission, top_n_comments=2)

    assert candidate == {
        "reddit_post_id": "abc123",
        "subreddit": "AskReddit",
        "title": "What is the funniest thing that happened at work?",
        "body": "Someone microwaved fish and the office melted down.",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 420,
        "comment_count": 37,
        "raw_json": {"id": "abc123"},
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
    submission = {
        "id": "abc123",
        "subreddit": "AskReddit",
        "title": "What is the funniest thing that happened at work?",
        "selftext": "Someone microwaved fish and the office melted down.",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 420,
        "num_comments": 37,
        "comments": [
            {"id": "c1", "body": "First", "score": 101, "author": "user1", "created_utc": 1712345680},
            {"id": "c2", "body": "Second", "score": 99, "author": "user2", "created_utc": 1712345685},
            {"id": "c3", "body": "Third", "score": 88, "author": "user3", "created_utc": 1712345690},
        ],
    }

    candidate = client.normalize_submission(submission, top_n_comments=1)

    assert candidate["top_comments"] == [
        {
            "comment_id": "c1",
            "body": "First",
            "score": 101,
            "author": "user1",
            "created_utc": 1712345680,
        }
    ]


def test_fetch_returns_normalized_candidates_from_configured_raw_submissions():
    client = RedditClient(
        config={
            "comments": {"top_n_per_candidate": 2},
            "reddit_test_data": {
                "submissions": [
                    {
                        "id": "abc123",
                        "subreddit": "AskReddit",
                        "title": "What is the funniest thing that happened at work?",
                        "selftext": "Someone microwaved fish and the office melted down.",
                        "url": "https://reddit.com/r/AskReddit/comments/abc123",
                        "author": "kelvin",
                        "created_utc": 1712345678,
                        "score": 420,
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
                ]
            },
        }
    )

    candidates = client.fetch()

    assert candidates == [
        {
            "reddit_post_id": "abc123",
            "subreddit": "AskReddit",
            "title": "What is the funniest thing that happened at work?",
            "body": "Someone microwaved fish and the office melted down.",
            "url": "https://reddit.com/r/AskReddit/comments/abc123",
            "author": "kelvin",
            "created_utc": 1712345678,
            "score": 420,
            "comment_count": 37,
            "raw_json": {"id": "abc123"},
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
    ]
