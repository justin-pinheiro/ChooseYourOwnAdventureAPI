from adventure import Adventure
from map import Area, Map

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
