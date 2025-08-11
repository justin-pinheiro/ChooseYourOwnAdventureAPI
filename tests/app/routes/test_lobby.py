from application.routes.lobby import manager
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from main import app
import pytest

client = TestClient(app)

def test_create_lobby_success():
    """Test that a lobby can be created with valid player limits."""
    response = client.post("/lobby/create?min_players=2&max_players=4")
    assert response.status_code == 200
    assert "lobby_id" in response.json()
    lobby_id = response.json()["lobby_id"]
    assert lobby_id in manager.lobbies

def test_create_lobby_invalid_limits():
    """Test that a lobby cannot be created with invalid limits."""
    response = client.post("/lobby/create?min_players=5&max_players=4")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid player limits: min_players must be at least 1 and less than or equal to max_players"

def test_websocket_connect_and_message():
    """Test that a client can connect to a lobby and send a message."""
    create_response = client.post("/lobby/create?min_players=2&max_players=4")
    print(f"create_response: {create_response.json()}")
    lobby_id = create_response.json()["lobby_id"]
    assert lobby_id in manager.lobbies

    with client.websocket_connect(f"/lobby/join/{lobby_id}") as websocket:
        data = websocket.receive_text()
        assert data == f"Welcome to lobby '{lobby_id}'."
        test_message = "Hello, world!"
        websocket.send_text(test_message)
        response_data = websocket.receive_text()
        assert response_data == f"Server received your message: '{test_message}'"

def test_websocket_join_non_existent_lobby():
    """Test that a connection to a non-existent lobby fails."""
    non_existent_id = "nonexistent"
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/lobby/join/{non_existent_id}") as websocket:
            websocket.receive_text()
    assert excinfo.value.code == 1008
    assert excinfo.value.reason == "Lobby not found"

def test_websocket_join_full_lobby():
    """Test that a connection to a full lobby fails."""
    create_response = client.post("/lobby/create?min_players=1&max_players=1")
    lobby_id = create_response.json()["lobby_id"]
    
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws1:
        ws1.receive_text()
        
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws2:
                ws2.receive_text()
        
        assert excinfo.value.code == 1008
        assert excinfo.value.reason == "Lobby is full"