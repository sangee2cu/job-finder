from dataclasses import dataclass
from typing import Optional

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    source: str = ""
    published_at: Optional[str] = None
    score: int = 0
    explanation: str = ""

    @property
    def key(self) -> str:
        return self.url.strip().lower() or f"{self.company}|{self.title}|{self.location}".lower()
