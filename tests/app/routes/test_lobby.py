from application.routes.lobby import manager
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from main import app
import pytest

client = TestClient(app)

def test_create_lobby_success():
    """Test that a lobby can be created with valid player limits."""
    response = client.post("/lobby/create?max_players=4")
    assert response.status_code == 200
    assert "lobby_id" in response.json()
    lobby_id = response.json()["lobby_id"]
    assert lobby_id in manager.lobbies

def test_create_lobby_invalid_limits():
    """Test that a lobby cannot be created with invalid limits."""
    response = client.post("/lobby/create?max_players=0")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid player limits: max_players must be at least 1"

def test_websocket_connect_and_message():
    """Test that a client can connect to a lobby and send a message."""
    create_response = client.post("/lobby/create?max_players=4")
    lobby_id = create_response.json()["lobby_id"]
    assert lobby_id in manager.lobbies

    with client.websocket_connect(f"/lobby/join/{lobby_id}") as websocket:
        welcome = websocket.receive_text()
        assert welcome == f"Welcome to lobby '{lobby_id}'."
        
        lobby_info = websocket.receive_json()
        assert lobby_info["info"]["id"] == lobby_id
        assert len(lobby_info["info"]["connections"]) == 1
        
        test_message = "Hello, world!"
        websocket.send_text(test_message)
        
        response = websocket.receive_text()
        assert response == f"Server received your message: '{test_message}'"

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
    create_response = client.post("/lobby/create?max_players=1")
    lobby_id = create_response.json()["lobby_id"]
    
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws1:
        ws1.receive_text()
        
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws2:
                ws2.receive_text()
        
        assert excinfo.value.code == 1008
        assert excinfo.value.reason == "Lobby is full"

def test_websocket_broadcast_lobby_info():
    """Test that all clients receive updated lobby info when a new client joins."""
    create_response = client.post("/lobby/create?max_players=4")
    assert create_response.status_code == 200
    lobby_id = create_response.json()["lobby_id"]
    assert lobby_id in manager.lobbies

    # Connect first client
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws1:
        welcome1 = ws1.receive_text()
        assert welcome1 == f"Welcome to lobby '{lobby_id}'."
        # ws1 should receive lobby info as JSON
        lobby_info_msg1 = ws1.receive_json()
        assert len(lobby_info_msg1["info"]["connections"]) == 1
        assert lobby_info_msg1["info"]["id"] == lobby_id

        # Connect second client
        with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws2:
            welcome2 = ws2.receive_text()
            assert welcome2 == f"Welcome to lobby '{lobby_id}'."
            # ws2 should receive lobby info as JSON
            lobby_info_msg2 = ws2.receive_json()
            assert len(lobby_info_msg2["info"]["connections"]) == 2
            assert lobby_info_msg2["info"]["id"] == lobby_id

            # ws1 should also receive updated lobby info
            lobby_info_msg1_update = ws1.receive_json()
            assert lobby_info_msg1_update["type"] == "lobby_info"
            assert lobby_info_msg1_update["info"]["id"] == lobby_id
            assert len(lobby_info_msg1_update["info"]["connections"]) == 2

def test_player_ready_state_toggle():
    """Test that players can toggle their ready state."""
    import json
    
    create_response = client.post("/lobby/create?min_players=2&max_players=4")
    lobby_id = create_response.json()["lobby_id"]
    
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as websocket:
        # Skip welcome message and initial lobby info
        websocket.receive_text()
        initial_lobby_info = websocket.receive_json()
        
        # Verify player starts as not ready
        assert initial_lobby_info["info"]["connections"][0]["is_ready"] == False
        
        # Toggle ready state to True
        websocket.send_text(json.dumps({"type": "toggle_ready"}))
        
        # Check updated lobby info
        updated_lobby_info = websocket.receive_json()
        assert updated_lobby_info["type"] == "lobby_info"
        assert updated_lobby_info["info"]["connections"][0]["is_ready"] == True

        # Check ready response
        ready_response = websocket.receive_json()
        assert ready_response["type"] == "ready_toggled"
        assert ready_response["success"] == True
        assert ready_response["is_ready"] == True
        
        # Toggle ready state back to False
        websocket.send_text(json.dumps({"type": "toggle_ready"}))
        
        # Check updated lobby info
        updated_lobby_info2 = websocket.receive_json()
        assert updated_lobby_info2["type"] == "lobby_info"
        assert updated_lobby_info2["info"]["connections"][0]["is_ready"] == False

        # Check ready response
        ready_response2 = websocket.receive_json()
        assert ready_response2["type"] == "ready_toggled"
        assert ready_response2["success"] == True
        assert ready_response2["is_ready"] == False

def test_multiple_players_ready_state():
    """Test that multiple players can independently toggle their ready states."""
    import json
    
    create_response = client.post("/lobby/create?min_players=2&max_players=4")
    lobby_id = create_response.json()["lobby_id"]
    
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws1:
        # Player 1 connects
        ws1.receive_text()  # Welcome message
        ws1.receive_json()  # Initial lobby info
        
        with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws2:
            # Player 2 connects
            ws2.receive_text()  # Welcome message
            ws2.receive_json()  # Initial lobby info
            ws1.receive_json()  # Player 1 gets updated lobby info
            
            # Player 1 toggles ready
            ws1.send_text(json.dumps({"type": "toggle_ready"}))
            lobby_info_1 = ws1.receive_json()  # Updated lobby info
            lobby_info_2 = ws2.receive_json()  # Player 2 gets updated lobby info
            ready_response_1 = ws1.receive_json()  # Player 1 ready response
            
            # Verify Player 1 is ready, Player 2 is not
            assert lobby_info_1["info"]["connections"][0]["is_ready"] == True
            assert lobby_info_1["info"]["connections"][1]["is_ready"] == False
            assert lobby_info_2["info"]["connections"][0]["is_ready"] == True
            assert lobby_info_2["info"]["connections"][1]["is_ready"] == False
            assert ready_response_1["type"] == "ready_toggled"
            assert ready_response_1["success"] == True
            assert ready_response_1["is_ready"] == True
            
            # Player 2 toggles ready
            ws2.send_text(json.dumps({"type": "toggle_ready"}))
            lobby_info_1 = ws1.receive_json()  # Player 1 gets updated lobby info
            lobby_info_2 = ws2.receive_json()  # Updated lobby info
            ready_response_2 = ws2.receive_json()  # Player 2 ready response
            
            # Verify both players are ready
            assert lobby_info_1["info"]["connections"][0]["is_ready"] == True
            assert lobby_info_1["info"]["connections"][1]["is_ready"] == True
            assert lobby_info_2["info"]["connections"][0]["is_ready"] == True
            assert lobby_info_2["info"]["connections"][1]["is_ready"] == True
            assert ready_response_2["type"] == "ready_toggled"
            assert ready_response_2["success"] == True
            assert ready_response_2["is_ready"] == True
            
            # Player 1 toggles ready back to False
            ws1.send_text(json.dumps({"type": "toggle_ready"}))
            lobby_info_1 = ws1.receive_json()  # Updated lobby info
            lobby_info_2 = ws2.receive_json()  # Player 2 gets updated lobby info
            ready_response_1_final = ws1.receive_json()  # Player 1 ready response
            
            # Verify Player 1 is not ready, Player 2 is ready
            assert lobby_info_1["info"]["connections"][0]["is_ready"] == False
            assert lobby_info_1["info"]["connections"][1]["is_ready"] == True
            assert lobby_info_2["info"]["connections"][0]["is_ready"] == False
            assert lobby_info_2["info"]["connections"][1]["is_ready"] == True
            assert ready_response_1_final["type"] == "ready_toggled"
            assert ready_response_1_final["success"] == True
            assert ready_response_1_final["is_ready"] == False

def test_ready_state_preserved_in_lobby_info():
    """Test that ready states are properly included in all lobby info broadcasts."""
    import json
    
    create_response = client.post("/lobby/create?min_players=1&max_players=3")
    lobby_id = create_response.json()["lobby_id"]
    
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws1:
        ws1.receive_text()  # Welcome
        ws1.receive_json()  # Initial lobby info
        
        # Player 1 becomes ready
        ws1.send_text(json.dumps({"type": "toggle_ready"}))
        ws1.receive_json()  # Updated lobby info
        ws1.receive_json()  # Ready response
        
        # Player 2 joins
        with client.websocket_connect(f"/lobby/join/{lobby_id}") as ws2:
            ws2.receive_text()  # Welcome
            lobby_info_2 = ws2.receive_json()  # Lobby info for player 2
            lobby_info_1 = ws1.receive_json()  # Updated lobby info for player 1
            
            # Both should show Player 1 as ready, Player 2 as not ready
            assert len(lobby_info_1["info"]["connections"]) == 2
            assert lobby_info_1["info"]["connections"][0]["is_ready"] == True
            assert lobby_info_1["info"]["connections"][1]["is_ready"] == False
            
            assert len(lobby_info_2["info"]["connections"]) == 2
            assert lobby_info_2["info"]["connections"][0]["is_ready"] == True
            assert lobby_info_2["info"]["connections"][1]["is_ready"] == False

def test_start_new_round():
    import json
    
    create_response = client.post("/lobby/create?max_players=2")
    lobby_id = create_response.json()["lobby_id"]
    
    with client.websocket_connect(f"/lobby/join/{lobby_id}") as websocket1:
        websocket1.receive_text()
        websocket1.receive_json()
        
        with client.websocket_connect(f"/lobby/join/{lobby_id}") as websocket2:
            websocket2.receive_text()
            websocket2.receive_json()
            websocket1.receive_json()
            
            websocket1.send_text(json.dumps({"type": "toggle_ready"}))
            websocket1.receive_json()
            websocket1.receive_json()
            
            websocket2.send_text(json.dumps({"type": "toggle_ready"}))
            websocket2.receive_json()
            websocket2.receive_json()

            websocket1.send_text(json.dumps({"type": "start_game"}))
            
            websocket1.receive_json()
            websocket2.receive_json()
            
            new_round_message1 = websocket1.receive_json()
            new_round_message2 = websocket2.receive_json()
            
            assert new_round_message1["type"] == "new_round"
            assert "text" in new_round_message1["info"]
            assert "choices" in new_round_message1["info"]
            
            assert new_round_message2["type"] == "new_round"
            assert "text" in new_round_message2["info"]
            assert "choices" in new_round_message2["info"]