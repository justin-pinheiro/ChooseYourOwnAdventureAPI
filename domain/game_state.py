from dataclasses import dataclass, field
import uuid
from domain.adventure import Adventure
from domain.chapter import Chapter

@dataclass
class GameState:
    """Represents the current state of a running game."""
    started: bool = False
    round: int = 0
    chapters: dict[uuid.UUID, list[Chapter]] = field(default_factory=dict)

    def to_dict(self):
        return {
            "started": self.started,
            "round": self.round,
        }
