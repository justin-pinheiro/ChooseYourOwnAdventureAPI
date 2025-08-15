from dataclasses import dataclass


@dataclass
class GameState:
    """Represents the current state of a running game."""
    started: bool = False
    round: int = 0

    def to_dict(self):
        return {
            "started": self.started,
            "round": self.round
        }
