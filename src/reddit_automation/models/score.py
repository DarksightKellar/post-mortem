from dataclasses import dataclass


@dataclass
class CandidateScore:
    reddit_post_id: str
    overall_score: float
    keep: bool
