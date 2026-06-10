from dataclasses import dataclass
from datetime import datetime


@dataclass
class VoteSession:
    session_id: str
    candidates: list[str]
    end_time: datetime