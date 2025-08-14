from dataclasses import dataclass


@dataclass
class User:
    """Represents a User and its informations."""
    name: str

    def to_dict(self):
        return {"name": self.name}
