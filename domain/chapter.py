from dataclasses import dataclass
@dataclass
class Chapter:
    """Represents a single lobby with player limits and connections."""
    text: str
    possiblities: list[str]
    choice: int | None = -1

    def to_dict(self):
        return {
            "text": self.text,
            "possiblities": [possiblity for possiblity in self.possiblities],
            "results": [possiblity for possiblity in self.possiblities],
            "choice": self.choice
        }