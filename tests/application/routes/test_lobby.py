from unittest.mock import patch

from application.routes.lobby import lobby_manager
from domain.adventure import Adventure
from domain.lobby import Lobby
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from main import app
import pytest

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
    
    mock_lobby = Lobby(mock_lobby_id, 3, mock_adventure)
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

def test_websocket_join_full_lobby(create_mock_lobby, websocket_connection):
    """Test that a connection to a full lobby fails."""
    lobby_id = "1"
    
    with websocket_connection(f"/lobbies/join/{lobby_id}") as ws1:
        ws1.receive_json()
        with websocket_connection(f"/lobbies/join/{lobby_id}") as ws2:
            ws2.receive_json()
            with websocket_connection(f"/lobbies/join/{lobby_id}") as ws3:
                ws3.receive_json()
            
                with pytest.raises(WebSocketDisconnect) as excinfo:
                    with websocket_connection(f"/lobbies/join/{lobby_id}"):
                        pass

    assert excinfo.value.code == 1008
    assert excinfo.value.reason == f"Lobby with ID {lobby_id} is full."

def test_websocket_broadcast_lobby_info(create_mock_lobby, websocket_connection):
    """Test that all clients receive updated lobby info when a new client joins."""
    lobby_id = create_mock_lobby

    with websocket_connection(f"/lobbies/join/{lobby_id}") as ws1:
        lobby_info_1 = ws1.receive_json()
        assert lobby_info_1["type"] == "lobby_info"
        assert lobby_info_1["lobby"]["current_players"] == 1
        assert lobby_info_1["lobby"]["id"] == lobby_id

        with websocket_connection(f"/lobbies/join/{lobby_id}") as ws2:
            lobby_info_2 = ws2.receive_json()
            assert lobby_info_2["type"] == "lobby_info"
            assert lobby_info_2["lobby"]["current_players"] == 2
            assert lobby_info_2["lobby"]["id"] == lobby_id

            lobby_update = ws1.receive_json()
            assert lobby_update["type"] == "lobby_info"
            assert lobby_update["lobby"]["current_players"] == 2
            assert lobby_update["lobby"]["id"] == lobby_id

def test_get_all_lobbies_success(create_mock_lobby):
    """Test that the endpoint returns a list of all lobbies."""
    response = client.get("/lobbies/")
    assert response.status_code == 200
    data = response.json()
    assert "total_lobbies" in data
    assert "lobbies" in data
    assert data["total_lobbies"] == 1
    assert len(data["lobbies"]) == 1
    lobby = data["lobbies"][0]
    assert lobby["id"] == create_mock_lobby
    assert lobby["current_players"] == 0

def test_get_all_lobbies_empty():
    """Test that the endpoint returns an empty lobby list when no lobbies exist."""
    response = client.get("/lobbies/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_lobbies"] == 0
    assert data["lobbies"] == []

def test_get_lobby_info_success(create_mock_lobby):
    """Test that the endpoint returns detailed info for a specific lobby."""
    lobby_id = create_mock_lobby
    response = client.get(f"/lobbies/{lobby_id}")
    assert response.status_code == 200
    lobby_info = response.json()
    assert lobby_info["id"] == lobby_id
    assert lobby_info["current_players"] == 0
    assert "max_players" in lobby_info
    assert "adventure_title" in lobby_info
    assert "adventure_description" in lobby_info
    assert lobby_info["adventure_title"] == "title"
    assert lobby_info["adventure_description"] == "description"

def test_get_lobby_info_not_found():
    """Test that the endpoint returns a 404 for a non-existent lobby."""
    response = client.get("/lobbies/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Lobby with id : 'nonexistent' was not found."

def test_websocket_client_disconnects(create_mock_lobby, websocket_connection):
    """Test that the lobby manager handles client disconnections gracefully."""
    lobby_id = create_mock_lobby
    
    with websocket_connection(f"/lobbies/join/{lobby_id}") as ws1:
        initial_info = ws1.receive_json()
        assert initial_info["type"] == "lobby_info"
        assert initial_info["lobby"]["current_players"] == 1

        with websocket_connection(f"/lobbies/join/{lobby_id}") as ws2:
            ws2_initial_info = ws2.receive_json()
            ws1_update = ws1.receive_json()
            
            assert ws2_initial_info["lobby"]["current_players"] == 2
            assert ws1_update["lobby"]["current_players"] == 2

        ws1_disconnect_update = ws1.receive_json()
        assert ws1_disconnect_update["lobby"]["current_players"] == 1

    assert lobby_id not in lobby_manager.lobbies
