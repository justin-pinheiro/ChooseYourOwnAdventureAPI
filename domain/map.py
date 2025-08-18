class Area:
    
    def __init__(self, id: int, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description

class Map:
    
    def __init__(self, id: int, areas: list[Area], connections: dict[int, set[int]] = None):
        self.id = id
        self.areas = areas
        self.connections = connections or {}
    
    def add_connection(self, area_id_one: int, area_id_two: int):
        if area_id_one not in self.connections:
            self.connections[area_id_one] = set()
        if area_id_two not in self.connections:
            self.connections[area_id_two] = set()
        
        self.connections[area_id_one].add(area_id_two)
        self.connections[area_id_two].add(area_id_one)
    
    def get_connected_areas(self, area_id: int) -> set[int]:
        return self.connections.get(area_id, set())
    
    def remove_connection(self, area_id_one: int, area_id_two: int):
        if area_id_one in self.connections:
            self.connections[area_id_one].discard(area_id_two)
        if area_id_two in self.connections:
            self.connections[area_id_two].discard(area_id_one)
    
    def get_area_by_id(self, area_id: int) -> Area:
        if 0 <= area_id < len(self.areas):
            return self.areas[area_id]
        return None
    
    def is_connected(self, area_id_one: int, area_id_two: int) -> bool:
        return area_id_two in self.connections.get(area_id_one, set())
    
    def get_all_areas(self) -> list[Area]:
        return self.areas.copy()
    
    def add_area(self, area: Area):
        self.areas.append(area)
    
    def remove_area(self, area_id: int):
        if 0 <= area_id < len(self.areas):
            for connected_id in list(self.connections.get(area_id, set())):
                self.remove_connection(area_id, connected_id)
            
            if area_id in self.connections:
                del self.connections[area_id]
            
            self.areas.pop(area_id)
            
            new_connections = {}
            for old_id, connected_set in self.connections.items():
                new_id = old_id if old_id < area_id else old_id - 1
                new_connected_set = set()
                for connected in connected_set:
                    if connected != area_id:
                        new_connected = connected if connected < area_id else connected - 1
                        new_connected_set.add(new_connected)
                new_connections[new_id] = new_connected_set
            
            self.connections = new_connections
            
            for area in self.areas[area_id:]:
                area.id -= 1
    
    @staticmethod
    def load(map_data) -> "Map":
        areas = []
        connections = {}
        area_id_map = {}
        
        for i, (area_key, area_data) in enumerate(map_data["areas"].items()):
            area = Area(i, area_data["name"], area_data["description"])
            areas.append(area)
            area_id_map[area_key] = i
        
        for area_key, area_data in map_data["areas"].items():
            area_id = area_id_map[area_key]
            connections[area_id] = set()
            
            for connected_area_key in area_data["connections"]:
                connected_area_id = area_id_map[connected_area_key]
                connections[area_id].add(connected_area_id)
        
        return Map(map_data["id"], areas, connections)
