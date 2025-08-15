class Area:
    
    """Represents an area of a map."""
    def __init__(self, id : int, name : str, description : str):
        self.id = id
        self.title = name
        self.description = description

class Map:
    
    """Represents a map."""
    def __init__(self, id : int, areas : list[Area]):
        self.id = id
        self.areas = areas