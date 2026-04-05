from dataclasses import dataclass


@dataclass
class Episode:
    episode_date: str
    title: str = ""
    status: str = "draft"
