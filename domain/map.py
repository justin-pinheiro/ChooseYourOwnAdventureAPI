class Area:
    
    """Represents an area of a map."""
    def __init__(self, id : int, name : str, description : str):
        self.id = id
        self.title = name
        self.description = description

class Map:
    
    """Represents a map."""
    def __init__(self, id : int, areas : list[Area], connections : dict[int, set[int]] = None):
        self.id = id
        self.areas = areas
        self.connections = connections or {}
    
    
    def addConnection(self, areaIdOne: int, areaIdTwo: int):
        """
        @brief Add a connection between two areas
        @param The two connections
        """
        if areaIdOne not in self.connections:
            self.connections[areaIdOne] = set()
        if areaIdTwo not in self.connections:
            self.connections[areaIdTwo] = set()
        
        self.connections[areaIdOne].add(areaIdTwo)
        self.connections[areaIdTwo].add(areaIdOne)
    
    def getConnectedAreas(self, areaId: int) -> set[int]:
        """
        @brief Add a connection between two areas
        @param The two connections
        """
        return self.connections.get(areaId, set())
    
    @staticmethod
    def load(mapData) -> "Map":
        """
        @brief Creates a Map instance from JSON data
        @param mapData Dictionary containing map structure with areas and connections
        @return New Map instance with loaded areas and connections
        """
        areas = []
        connections = {}
        areaIdMap = {}
        
        for i, (areaKey, areaData) in enumerate(mapData["areas"].items()):
            area = Area(i, areaData["name"], areaData["description"])
            areas.append(area)
            areaIdMap[areaKey] = i
        
        for areaKey, areaData in mapData["areas"].items():
            areaId = areaIdMap[areaKey]
            connections[areaId] = set()
            
            for connectedAreaKey in areaData["connections"]:
                connectedAreaId = areaIdMap[connectedAreaKey]
                connections[areaId].add(connectedAreaId)
        
        return Map(mapData["id"], areas, connections)
