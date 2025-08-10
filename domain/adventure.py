
class Adventure:
    """Represents an adventure which correspond to a full story."""
    def __init__(self, id: int, title: str, description: str, min_players: int, max_players: int):
        self.id = id
        self.title = title
        self.description = description
        self.min_players = min_players
        self.max_players = max_players
