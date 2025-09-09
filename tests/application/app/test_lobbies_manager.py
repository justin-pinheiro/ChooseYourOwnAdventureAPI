from application.app.adventure.adventure_exceptions import AdventureNotFoundException
from application.app.game_manager import GameManager
from application.app.lobby.lobbies_manager import LobbiesManager
from application.app.lobby.lobby_exceptions import ConnectionNotFoundException, LobbyIsFullException, LobbyNotFound
from domain.adventure import Adventure
from domain.connection import Connection
from domain.lobby import Lobby
from domain.user import User
import pytest
from unittest.mock import Mock, patch
from starlette.websockets import WebSocketDisconnect

# --- Mocks for Dependencies ---

class MockAdventure:
    def __init__(self, adventure_id: int, title: str):
        self.id = adventure_id
        self.title = title

class MockWebSocket:
    async def accept(self):
        pass
    async def send_json(self, message):
        pass

class MockConnection:
    def __init__(self, websocket):
        self.socket = websocket

# --- Fixtures for Tests ---

@pytest.fixture
def mock_game_manager():
    return Mock(spec=GameManager)

@pytest.fixture
def mock_adventure_loader():
    """
    Mocks the AdventureLoader class to control its behavior in tests.
    We are patching the entire class and defining the behavior of its static methods.
    """
    with patch('application.app.adventure.adventure_loader.AdventureLoader') as MockedAdventureLoader:
        mock_adventure = MockAdventure(adventure_id=1, title="The Lost Treasure")
        
        MockedAdventureLoader.get_adventure_by_id.return_value = mock_adventure
        MockedAdventureLoader.load_adventures_from_json.return_value = [mock_adventure]
        
        yield MockedAdventureLoader
        
@pytest.fixture
def lobbies_manager(mock_game_manager, mock_adventure_loader):
    """Fixture to create a clean LobbiesManager instance for each test."""
    manager = LobbiesManager(mock_game_manager)
    manager.lobbies = {}
    return manager

# --- Unit Tests for create_lobby method ---

def test_create_lobby_success(lobbies_manager):
    """Test that a new lobby is successfully created with a valid adventure ID."""
    max_players = 4
    adventure_id = 1
    
    lobby_id = lobbies_manager.create_lobby(max_players, adventure_id)
    
    assert isinstance(lobby_id, str)
    assert len(lobby_id) == 8
    assert lobby_id in lobbies_manager.lobbies
    
    new_lobby = lobbies_manager.lobbies[lobby_id]
    assert new_lobby.max_players == max_players
    assert new_lobby.adventure.id == adventure_id

def test_create_lobby_with_invalid_max_players_raises_error(lobbies_manager):
    """Test that creating a lobby with max_players less than 1 raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid player limits"):
        lobbies_manager.create_lobby(max_players=0, adventure_id=1)

def test_create_lobby_with_non_existent_adventure_raises_error(lobbies_manager):
    """Test that creating a lobby with a non-existent adventure ID raises an AdventureNotFoundException."""
    non_existent_adventure_id = 99
    
    with pytest.raises(AdventureNotFoundException, match=str(non_existent_adventure_id)):
        lobbies_manager.create_lobby(max_players=4, adventure_id=non_existent_adventure_id)

# --- Unit Tests for get_lobby method ---

def test_get_lobby_success(lobbies_manager):
    """Test that an existing lobby can be successfully retrieved."""
    lobby_id = lobbies_manager.create_lobby(max_players=2, adventure_id=1)
    
    retrieved_lobby = lobbies_manager.get_lobby(lobby_id)
    
    assert retrieved_lobby is not None
    assert retrieved_lobby.id == lobby_id
    assert retrieved_lobby.max_players == 2

def test_get_lobby_raises_not_found_for_non_existent_id(lobbies_manager):
    """Test that a LobbyNotFound exception is raised for a non-existent lobby ID."""
    non_existent_id = "nonexistent"
    
    with pytest.raises(LobbyNotFound, match=non_existent_id):
        lobbies_manager.get_lobby(non_existent_id)

# --- Unit tests for get_all_lobbies method

def test_get_all_lobbies_success(lobbies_manager):
    """Test that get_all_lobbies returns correct information for multiple lobbies."""
    lobby1_id = "lobby_1"
    lobby2_id = "lobby_2"
    lobbies_manager.lobbies[lobby1_id] = Lobby(lobby1_id, max_players=4, adventure=Mock())
    lobbies_manager.lobbies[lobby2_id] = Lobby(lobby2_id, max_players=2, adventure=Mock())

    lobbies_data = lobbies_manager.get_all_lobbies()

    assert lobbies_data["total_lobbies"] == 2
    assert len(lobbies_data["lobbies"]) == 2
    
    lobby_ids = [lobby["id"] for lobby in lobbies_data["lobbies"]]
    assert lobby1_id in lobby_ids
    assert lobby2_id in lobby_ids

def test_get_all_lobbies_empty(lobbies_manager):
    """Test that get_all_lobbies returns empty information when no lobbies exist."""
    
    lobbies_data = lobbies_manager.get_all_lobbies()
    
    assert lobbies_data["total_lobbies"] == 0
    assert len(lobbies_data["lobbies"]) == 0
    assert lobbies_data["lobbies"] == []

# --- Unit tests for connect method ---

@pytest.mark.asyncio
async def test_connect_success(lobbies_manager):
    """
    Test a successful connection to an existing, non-full lobby.
    """
    lobby_id = "test_lobby"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    lobbies_manager.lobbies[lobby_id] = lobby
    mock_websocket = MockWebSocket()

    await lobbies_manager.connect(mock_websocket, lobby_id)

    assert len(lobby.connections) == 1
    assert lobby.connections[0].socket == mock_websocket

@pytest.mark.asyncio
async def test_connect_raises_lobby_not_found(lobbies_manager):
    """
    Test that connecting to a non-existent lobby raises LobbyNotFound.
    """
    non_existent_id = "non_existent"
    mock_websocket = MockWebSocket()

    with pytest.raises(LobbyNotFound, match=non_existent_id):
        await lobbies_manager.connect(mock_websocket, non_existent_id)

@pytest.mark.asyncio
async def test_connect_raises_lobby_is_full(lobbies_manager):
    """
    Test that connecting to a full lobby raises LobbyIsFullException.
    """
    full_lobby_id = "full_lobby"
    with patch("domain.lobby.Lobby.is_full",return_value=True):
        lobby = Lobby(full_lobby_id, max_players=2, adventure=Mock(1, "adventure"))
        lobbies_manager.lobbies[full_lobby_id] = lobby
        mock_websocket = MockWebSocket()
        
        with pytest.raises(LobbyIsFullException, match=full_lobby_id):
            await lobbies_manager.connect(mock_websocket, full_lobby_id)

# --- Unit Tests for disconnect method ---

def test_disconnect_success_with_multiple_clients(lobbies_manager):
    """Test that a client is successfully disconnected and the lobby remains."""
    lobby_id = "test_lobby_multi"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    
    socket1 = MockWebSocket()
    socket2 = MockWebSocket()
    lobby.connections.append(MockConnection(socket1))
    lobby.connections.append(MockConnection(socket2))
    lobbies_manager.lobbies[lobby_id] = lobby
    
    lobbies_manager.disconnect(socket1, lobby_id)
    assert len(lobby.connections) == 1
    assert lobby.connections[0].socket == socket2
    assert lobby_id in lobbies_manager.lobbies

def test_disconnect_last_client_removes_lobby(lobbies_manager):
    """Test that disconnecting the last client removes the lobby."""
    lobby_id = "test_lobby_single"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    
    socket1 = MockWebSocket()
    lobby.connections.append(MockConnection(socket1))
    lobbies_manager.lobbies[lobby_id] = lobby
    
    lobbies_manager.disconnect(socket1, lobby_id)
    
    assert lobby_id not in lobbies_manager.lobbies
    assert not lobby.connections

def test_disconnect_non_existent_client_leaves_others_untouched(lobbies_manager):
    """Test that attempting to disconnect a non-existent client does not affect others."""
    lobby_id = "test_lobby_non_existent_client"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    
    socket1 = MockWebSocket()
    lobby.connections.append(MockConnection(socket1))
    lobbies_manager.lobbies[lobby_id] = lobby
    
    non_existent_socket = MockWebSocket()
    lobbies_manager.disconnect(non_existent_socket, lobby_id)
    
    assert len(lobby.connections) == 1
    assert lobby.connections[0].socket == socket1
    assert lobby_id in lobbies_manager.lobbies

def test_disconnect_from_non_existent_lobby_does_nothing(lobbies_manager):
    """Test that attempting to disconnect from a non-existent lobby does not raise an error."""
    non_existent_id = "non_existent_lobby"
    socket = MockWebSocket()
    assert len(lobbies_manager.lobbies) == 0
    lobbies_manager.disconnect(socket, non_existent_id)
    assert len(lobbies_manager.lobbies) == 0

# --- Unit Tests for broadcast_lobby_info method ---

@pytest.mark.asyncio
async def test_broadcast_lobby_info_success(lobbies_manager):
    """Test that broadcasting lobby info successfully sends a message to all clients."""
    lobby_id = "broadcast_test_lobby"
    lobby = Lobby(lobby_id, max_players=4, adventure=Adventure(1, "adventure", "description", 2, 4, None))
    
    socket1 = Mock(spec=MockWebSocket)
    socket2 = Mock(spec=MockWebSocket)
    lobby.connections.append(Connection(socket1, User("name1"), False, "id1"))
    lobby.connections.append(Connection(socket2, User("name2"), True, "id2"))
    lobbies_manager.lobbies[lobby_id] = lobby
    
    await lobbies_manager.broadcast_lobby_info(lobby_id)
    
    expected_message = {
        'type': 'lobby_info',
        'lobby': {
            "id": "broadcast_test_lobby",
            "max_players": 4,
            "current_players": 2,
            "adventure_title": "adventure",
            "adventure_description": "description",
            "game_started": False,
            "current_round": 0,
            "players": [
                {
                    "name": "name1",
                    "is_ready": False
                },
                {
                    "name": "name2",
                    "is_ready": True
                },
            ],
            "is_full": False
        }
    }
    
    socket1.send_json.assert_called_once_with(expected_message)
    socket1.send_json.assert_called_once_with(expected_message)

@pytest.mark.asyncio
async def test_broadcast_lobby_info_disconnects_client_on_websocket_disconnect(lobbies_manager):
    """Test that a client is disconnected when a WebSocketDisconnect exception occurs."""
    lobby_id = "disconnect_on_broadcast"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    lobby.to_dict = Mock(return_value={"id": lobby_id, "players": 2})

    mock_socket1 = Mock(spec=MockWebSocket)
    mock_socket1.send_json.side_effect = WebSocketDisconnect
    mock_socket2 = Mock(spec=MockWebSocket)
    
    lobby.connections.append(MockConnection(mock_socket1))
    lobby.connections.append(MockConnection(mock_socket2))
    lobbies_manager.lobbies[lobby_id] = lobby
    
    with patch.object(lobbies_manager, "disconnect") as mock_disconnect:
        await lobbies_manager.broadcast_lobby_info(lobby_id)
        mock_disconnect.assert_called_once_with(mock_socket1, lobby_id)
        mock_socket2.send_json.assert_called_once()

# --- Unit tests for switch_client_ready_state method ---

@pytest.mark.asyncio
async def test_switch_client_ready_state_success(lobbies_manager):
    """Test that a client's ready state is successfully toggled."""
    lobby_id = "ready_state_lobby"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    
    mock_socket = MockWebSocket()
    mock_user = User("test_user")
    connection = Connection(mock_socket, mock_user)
    connection.is_ready = False
    
    lobby.connections.append(connection)
    lobbies_manager.lobbies[lobby_id] = lobby
    
    result = await lobbies_manager.switch_client_ready_state(mock_socket, lobby_id)
    assert result is True
    assert connection.is_ready is True
    
    result = await lobbies_manager.switch_client_ready_state(mock_socket, lobby_id)
    assert result is False
    assert connection.is_ready is False

@pytest.mark.asyncio
async def test_switch_client_ready_state_raises_connection_not_found(lobbies_manager):
    """Test that an error is handled when the connection is not found."""
    lobby_id = "test_lobby"
    lobby = Lobby(lobby_id, max_players=4, adventure=MockAdventure(1, "adventure"))
    lobbies_manager.lobbies[lobby_id] = lobby
    
    non_existent_socket = MockWebSocket()
    
    with pytest.raises(ConnectionNotFoundException):
        await lobbies_manager.switch_client_ready_state(non_existent_socket, lobby_id)

@pytest.mark.asyncio
async def test_switch_client_ready_state_raises_value_error_if_lobby_not_found(lobbies_manager):
    """Test that a ValueError is handled when the lobby does not exist."""
    non_existent_id = "non_existent_id"
    mock_socket = MockWebSocket()
    
    with pytest.raises(LobbyNotFound):
        await lobbies_manager.switch_client_ready_state(mock_socket, non_existent_id)
