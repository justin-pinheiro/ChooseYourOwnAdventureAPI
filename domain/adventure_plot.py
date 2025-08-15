from adventure import Adventure
from map import Area, Map

class AdventurePlot:
    
    """Represents an adventure plot."""
    def __init__(self, id: int, title: str, description: str, min_players: int, max_players: int, map : Map):
        self.id = id
        self.title = title
        self.description = description
        self.min_players = min_players
        self.max_players = max_players
        self.map = map
        
    """Return the related adventure"""
    def generateAdventure() -> Adventure:
        pass