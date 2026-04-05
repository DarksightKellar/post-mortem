from dataclasses import dataclass


@dataclass
class Candidate:
    reddit_post_id: str
    subreddit: str
    title: str
    body: str
