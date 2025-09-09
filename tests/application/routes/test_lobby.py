from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from application.app.lobby.lobby_exceptions import LobbyNotFound
from application.routes.lobby import lobby_manager
from domain.adventure import Adventure
from domain.lobby import Lobby
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from main import app
import pytest
import json

client = TestClient(app)

# --- fixtures

@pytest.fixture(autouse=True)
def clean_lobbies():
    """Clean up lobbies before and after each test"""
    lobby_manager.lobbies.clear()
    yield
    lobby_manager.lobbies.clear()

@pytest.fixture
def websocket_connection():
    """Fixture to manage WebSocket connections and ensure they're closed after each test"""
    active_connections = []
    
    def _create_connection(path):
        ws = client.websocket_connect(path)
        active_connections.append(ws)
        return ws
    
    yield _create_connection
    
    # Clean up all connections after the test
    for ws in active_connections:
        try:
            ws.close()
        except Exception:
            pass  # Connection might already be closed

@pytest.fixture
def mock_adventure():
    """Fixture to provide a mock adventure"""
    with patch(
        "application.app.adventure.adventure_loader.AdventureLoader.get_adventure_by_id",
        return_value=Adventure(1, "title", "description", 2, 4, None),
    ) as mock:
        yield mock

@pytest.fixture
def create_mock_lobby():
    """
    Fixture to create and return a mock lobby with a predefined ID. 
    The lobby is added directly to the lobby_manager for testing.
    """
    mock_lobby_id = "1"
    mock_adventure = Adventure(1, "title", "description", 2, 4, None)
    
    mock_lobby = Lobby(mock_lobby_id, 4, mock_adventure)
    lobby_manager.lobbies[mock_lobby_id] = mock_lobby
    
    yield mock_lobby_id

# --- tests

def test_create_lobby_success(mock_adventure):
    
    response = client.post(
        "/lobbies/create",
        params={"max_players": 4, "adventure_id": 1}
    )

    assert response.status_code == 200
    assert "lobby_id" in response.json()
    lobby_id = response.json()["lobby_id"]
    assert lobby_id in lobby_manager.lobbies

def test_create_lobby_invalid_limits(mock_adventure):
    """Test that a lobby cannot be created with invalid limits."""
    response = client.post(
        "/lobbies/create",
        params={"max_players": 0, "adventure_id": 1}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid player limits: max_players must be at least 1"

def test_websocket_joins_non_existent_lobby(mock_adventure, websocket_connection):
    """Test that a connection to a non-existent lobby fails."""
    non_existent_id = "nonexistent"

    with pytest.raises(WebSocketDisconnect) as e:
        with websocket_connection(f"/lobbies/join/{non_existent_id}"):
            pass

    assert e.value.code == 1008
    assert "Lobby with id : 'nonexistent' was not found." in str(e.value.reason)
    
def test_websocket_joins_lobby_successfully(create_mock_lobby, websocket_connection):
    """Test that a client can connect to a lobby."""
    lobby_id = "1"
    
    with websocket_connection(f"/lobbies/join/{lobby_id}") as websocket:
        lobby_info = websocket.receive_json()
        assert "type" in lobby_info
        assert lobby_info["type"] == "lobby_info"
        assert lobby_info["lobby"]["id"] == lobby_id
        assert lobby_info["lobby"]["current_players"] == 1


# def test_websocket_join_full_lobby(create_test_lobby):
#     """Test that a connection to a full lobby fails."""
#     lobby_id = create_test_lobby(max_players=1)
    
#     with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws1:
#         ws1.receive_json()  # Initial lobby info
        
#         with pytest.raises(WebSocketDisconnect) as excinfo:
#             with client.websocket_connect(f"/lobbies/join/{lobby_id}"):
#                 pass
        
#         assert excinfo.value.code == 1008
#         assert excinfo.value.reason == f"Lobby with ID {lobby_id} is full."

# def test_websocket_broadcast_lobby_info():
#     """Test that all clients receive updated lobby info when a new client joins."""
    
#     with patch(
#         "application.app.adventure.adventure_loader.AdventureLoader.get_adventure_by_id",
#         return_value=Adventure(1, "title", "description", 2, 4, None),
#     ):
#         create_response = client.post(
#             "/lobbies/create",
#             params={"max_players": 4, "adventure_id": 1}
#         )
        
#     assert create_response.status_code == 200
#     lobby_id = create_response.json()["lobby_id"]
#     assert lobby_id in lobby_manager.lobbies

#     # Connect first client
#     with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws1:
        
#         # ws1 should receive lobby info as JSON
#         lobby_info_msg1 = ws1.receive_json()
#         assert lobby_info_msg1["info"]["lobby"]["current_players"] == 1
#         assert lobby_info_msg1["info"]["lobby"]["id"] == lobby_id

#         # Connect second client
#         with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws2:
#             # ws2 should receive lobby info as JSON
#             lobby_info_msg2 = ws2.receive_json()
#             assert lobby_info_msg2["info"]["lobby"]["current_players"] == 2
#             assert lobby_info_msg2["info"]["lobby"]["id"] == lobby_id

#             # ws1 should also receive updated lobby info
#             lobby_info_msg1_update = ws1.receive_json()
#             assert lobby_info_msg1_update["type"] == "lobby_info"
#             assert lobby_info_msg1_update["info"]["lobby"]["id"] == lobby_id
#             assert lobby_info_msg1_update["info"]["lobby"]["current_players"] == 2

#             ws2.close()
        
#         ws1.close()

# def test_player_ready_state_toggle(create_test_lobby):
#     """Test that players can toggle their ready state."""
#     lobby_id = create_test_lobby()
    
#     with client.websocket_connect(f"/lobbies/join/{lobby_id}") as websocket:
#         websocket.receive_json()  # Initial lobby info
        
#         # Toggle ready state to True
#         websocket.send_text(json.dumps({"type": "toggle_ready"}))
        
#         lobby_update = websocket.receive_json()
#         assert lobby_update["type"] == "lobby_info"
#         assert lobby_update["info"]["lobby"]["players"][0]["is_ready"] == True

#         ready_response = websocket.receive_json()
#         assert ready_response["type"] == "ready_toggled"
#         assert ready_response["success"] == True
#         assert ready_response["is_ready"] == True
        
#         # Toggle ready state back to False
#         websocket.send_text(json.dumps({"type": "toggle_ready"}))
        
#         lobby_update = websocket.receive_json()
#         assert lobby_update["type"] == "lobby_info"
#         assert lobby_update["info"]["lobby"]["players"][0]["is_ready"] == False

#         ready_response = websocket.receive_json()
#         assert ready_response["type"] == "ready_toggled"
#         assert ready_response["success"] == True
#         assert ready_response["is_ready"] == False

#         websocket.close()

# def test_multiple_players_ready_state(create_test_lobby):
#     """Test that multiple players can independently toggle their ready states."""
#     lobby_id = create_test_lobby(max_players=4)
    
#     with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws1:
#         # Player 1 connects and gets initial lobby info
#         ws1.receive_json()  # Initial lobby info
        
#         with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws2:
#             # Player 2 connects
#             ws2.receive_json()  # Initial lobby info for ws2
#             ws1.receive_json()  # Updated lobby info for ws1 with new player

#             # Player 1 toggles ready
#             ws1.send_text(json.dumps({"type": "toggle_ready"}))
            
#             # Get lobby updates and ready response
#             p1_lobby_update = ws1.receive_json()
#             p2_lobby_update = ws2.receive_json()
#             ready_response = ws1.receive_json()
            
#             # Verify initial ready state
#             assert p1_lobby_update["info"]["lobby"]["players"][0]["is_ready"] == True
#             assert p2_lobby_update["info"]["lobby"]["players"][0]["is_ready"] == True
#             assert ready_response["type"] == "ready_toggled"
#             assert ready_response["is_ready"] == True

#             # Player 2 toggles ready
#             ws2.send_text(json.dumps({"type": "toggle_ready"}))
            
#             # Get updates for player 2's ready toggle
#             p2_lobby_update = ws2.receive_json()
#             p1_lobby_update = ws1.receive_json()
#             p2_ready_response = ws2.receive_json()
            
#             # Verify both players ready state
#             assert p1_lobby_update["info"]["lobby"]["players"][0]["is_ready"] == True
#             assert p1_lobby_update["info"]["lobby"]["players"][1]["is_ready"] == True
#             assert p2_ready_response["type"] == "ready_toggled"
#             assert p2_ready_response["is_ready"] == True

#             ws2.close()

#         ws1.close()

# def test_ready_state_preserved_in_lobby_info(create_test_lobby):
    # """Test that ready states are properly included in all lobby info broadcasts."""
    # lobby_id = create_test_lobby(max_players=3)
    
    # with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws1:
    #     ws1.receive_json()  # Initial lobby info
        
    #     # Player 1 becomes ready
    #     ws1.send_text(json.dumps({"type": "toggle_ready"}))
    #     lobby_update = ws1.receive_json()  # Updated lobby info
    #     ready_response = ws1.receive_json()  # Ready response
        
    #     assert lobby_update["type"] == "lobby_info"
    #     assert lobby_update["info"]["lobby"]["players"][0]["is_ready"] == True
    #     assert ready_response["type"] == "ready_toggled"
        
    #     # Player 2 joins
    #     with client.websocket_connect(f"/lobbies/join/{lobby_id}") as ws2:
    #         p2_initial_info = ws2.receive_json()  # Initial info for player 2
    #         p1_update = ws1.receive_json()  # Updated info for player 1
            
    #         # Verify both players see the correct ready states
    #         assert len(p2_initial_info["info"]["lobby"]["players"]) == 2
    #         assert p2_initial_info["info"]["lobby"]["players"][0]["is_ready"] == True
    #         assert p2_initial_info["info"]["lobby"]["players"][1]["is_ready"] == False
            
    #         assert len(p1_update["info"]["lobby"]["players"]) == 2
    #         assert p1_update["info"]["lobby"]["players"][0]["is_ready"] == True
    #         assert p1_update["info"]["lobby"]["players"][1]["is_ready"] == False

    #         ws2.close()
    #     ws1.close()