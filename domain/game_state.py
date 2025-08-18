from dataclasses import dataclass, field
from domain.adventure import Adventure
from domain.chapter import Chapter

@dataclass
class GameState:
    """Represents the current state of a running game."""
    started: bool = False
    round: int = 0
    adventure: Adventure | None = None
    chapters: list[Chapter] = field(default_factory=list)

    def to_dict(self):
        return {
            "started": self.started,
            "round": self.round,
            "adventure": self.adventure,
        }
