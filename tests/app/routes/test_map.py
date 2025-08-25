import pytest
from domain.map import Area, Map

def test_area_creation():
    area = Area(1, "Test Area", "A test description")
    
    assert area.id == 1
    assert area.name == "Test Area"
    assert area.description == "A test description"

def test_map_creation():
    areas = [
        Area(0, "Area 1", "First area"),
        Area(1, "Area 2", "Second area")
    ]
    game_map = Map(1, areas)
    
    assert game_map.id == 1
    assert len(game_map.areas) == 2
    assert len(game_map.connections) == 0

def test_add_connection():
    areas = [Area(0, "Area 1", "First"), Area(1, "Area 2", "Second")]
    game_map = Map(1, areas)
    
    game_map.add_connection(0, 1)
    
    assert 1 in game_map.get_connected_areas(0)
    assert 0 in game_map.get_connected_areas(1)

def test_get_connected_areas():
    areas = [Area(0, "A"), Area(1, "B"), Area(2, "C")]
    game_map = Map(1, areas)
    
    game_map.add_connection(0, 1)
    game_map.add_connection(0, 2)
    
    connected = game_map.get_connected_areas(0)
    assert len(connected) == 2
    assert 1 in connected
    assert 2 in connected

def test_remove_connection():
    areas = [Area(0, "A"), Area(1, "B")]
    game_map = Map(1, areas)
    
    game_map.add_connection(0, 1)
    game_map.remove_connection(0, 1)
    
    assert len(game_map.get_connected_areas(0)) == 0
    assert len(game_map.get_connected_areas(1)) == 0

def test_get_area_by_id():
    areas = [Area(0, "Test Area", "Description")]
    game_map = Map(1, areas)
    
    area = game_map.get_area_by_id(0)
    assert area is not None
    assert area.name == "Test Area"
    
    invalid_area = game_map.get_area_by_id(99)
    assert invalid_area is None

def test_is_connected():
    areas = [Area(0, "A"), Area(1, "B"), Area(2, "C")]
    game_map = Map(1, areas)
    
    game_map.add_connection(0, 1)
    
    assert game_map.is_connected(0, 1) == True
    assert game_map.is_connected(1, 0) == True
    assert game_map.is_connected(0, 2) == False

def test_get_all_areas():
    areas = [Area(0, "A"), Area(1, "B")]
    game_map = Map(1, areas)
    
    all_areas = game_map.get_all_areas()
    assert len(all_areas) == 2
    assert all_areas[0].name == "A"
    assert all_areas[1].name == "B"

def test_add_area():
    game_map = Map(1, [])
    new_area = Area(0, "New Area", "Description")
    
    game_map.add_area(new_area)
    
    assert len(game_map.areas) == 1
    assert game_map.areas[0].name == "New Area"

def test_load_from_json():
    map_data = {
        "id": 1,
        "areas": {
            "entrance": {
                "name": "Entrance",
                "description": "The entrance",
                "connections": ["corridor"]
            },
            "corridor": {
                "name": "Corridor", 
                "description": "A corridor",
                "connections": ["entrance"]
            }
        }
    }
    
    game_map = Map.load(map_data)
    
    assert game_map.id == 1
    assert len(game_map.areas) == 2
    assert game_map.areas[0].name == "Entrance"
    assert game_map.areas[1].name == "Corridor"
    assert game_map.is_connected(0, 1) == True

def test_load_complex_map():
    map_data = {
        "id": 2,
        "areas": {
            "entrance": {
                "name": "Crypt Entrance",
                "description": "A weathered stone archway",
                "connections": ["corridor"]
            },
            "corridor": {
                "name": "Main Corridor",
                "description": "A long hallway",
                "connections": ["entrance", "chamber", "guard_room"]
            },
            "chamber": {
                "name": "Ritual Chamber",
                "description": "A circular room",
                "connections": ["corridor"]
            },
            "guard_room": {
                "name": "Guardian's Lair",
                "description": "A vast chamber",
                "connections": ["corridor"]
            }
        }
    }
    
    game_map = Map.load(map_data)
    
    assert len(game_map.areas) == 4
    corridor_connections = game_map.get_connected_areas(1)
    assert len(corridor_connections) == 3
    assert 0 in corridor_connections
    assert 2 in corridor_connections
    assert 3 in corridor_connections