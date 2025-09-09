from application.app.adventure.adventure_exceptions import AdventureNotFoundException
from application.app.game_manager import GameManager
from application.app.lobby.lobbies_manager import LobbiesManager
from application.app.lobby.lobby_exceptions import LobbyIsFullException, LobbyNotFound
from domain.adventure import Adventure
from domain.lobby import Lobby
import pytest
from unittest.mock import Mock, patch
from typing import Dict, List

# --- Mocks for Dependencies ---

class MockAdventure:
    def __init__(self, adventure_id: int, title: str):
        self.id = adventure_id
        self.title = title

class MockWebSocket:
    async def accept(self):
        pass

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
