from dataclasses import dataclass


@dataclass
class UserContext:
    enroll_id: int
    name: str | None = None