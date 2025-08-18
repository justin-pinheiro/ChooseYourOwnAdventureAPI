from domain.map import Area, Map

from dataclasses import dataclass

@dataclass
class Adventure:
    """
    Class that store an adventure.
    """
    id: int
    title: str
    description: str
    minPlayers: int
    maxPlayers: int
    map: Map
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'minPlayers': self.minPlayers,
            'maxPlayers': self.maxPlayers,
            'map': self.map.to_dict()
        }