from typing import Dict, List
from application.app.game_manager import GameManager
from application.app.lobby_manager import LobbyManager
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from fastapi import WebSocketDisconnect
from domain.connection import Connection
from domain.user import User


@pytest.fixture
def mock_websocket():
    return AsyncMock()

@pytest.fixture
def mock_lobby_manager():
    return AsyncMock(spec=LobbyManager)

@pytest.fixture
def game_manager(mock_lobby_manager):
    return GameManager(lobby_manager=mock_lobby_manager)

@pytest.fixture
def mock_story_manager(monkeypatch):
    mock_sm = AsyncMock()
    monkeypatch.setattr('application.app.story_manager', mock_sm)
    return mock_sm

@pytest.fixture
def new_lobby():
    lobby_id = "test-lobby"
    return MockLobby(lobby_id)

@pytest.fixture
def filled_lobby():
    lobby = MockLobby("filled-lobby")
    for i in range(3):
        user = User(name=f"Player{i}")
        ws = AsyncMock()
        conn = Connection(user=user, socket=ws)
        conn.is_ready = True
        lobby.connections.append(conn)
    return lobby


class MockChapter:
    def __init__(self, text, possibilities, choice=-1):
        self.text = text
        self.possiblities = possibilities
        self.choice = choice

class MockGameState:
    def __init__(self):
        self.started = False
        self.round = 0
        self.adventure = "test-adventure"
        self.chapters: Dict[uuid.UUID, List[MockChapter]] = {}

class MockLobby:
    def __init__(self, lobby_id: str):
        self.id = lobby_id
        self.connections: List[Connection] = []
        self.game_state = MockGameState()


@pytest.mark.asyncio
async def test_start_lobby_success(game_manager, mock_lobby_manager, filled_lobby):
    """Test start_lobby successfully starts a game."""
    mock_lobby_manager.get_lobby.return_value = filled_lobby
    await game_manager.start_lobby(filled_lobby.id)
    assert filled_lobby.game_state.started is True
    for conn in filled_lobby.connections:
        conn.socket.send_json.assert_called_once()
        sent_message = conn.socket.send_json.call_args[0][0]
        assert sent_message["type"] == "start_adventure"
        assert sent_message["info"]["success"] is True

@pytest.mark.asyncio
async def test_start_lobby_not_found(game_manager, mock_lobby_manager):
    """Test start_lobby raises an exception if the lobby is not found."""
    mock_lobby_manager.get_lobby.return_value = None
    with pytest.raises(Exception, match="Lobby .* not found"):
        await game_manager.start_lobby("non-existent-lobby")

@pytest.mark.asyncio
async def test_start_lobby_not_all_players_ready(game_manager, mock_lobby_manager, new_lobby, mock_websocket):
    """Test start_lobby raises an exception if not all players are ready."""
    user = User(name="TestUser")
    conn = Connection(mock_websocket, user)
    conn.is_ready = False
    new_lobby.connections.append(conn)
    mock_lobby_manager.get_lobby.return_value = new_lobby
    with pytest.raises(Exception, match="All players must be ready"):
        await game_manager.start_lobby(new_lobby.id)

@pytest.mark.asyncio
async def test_start_lobby_websocket_disconnect(game_manager, mock_lobby_manager, filled_lobby):
    """Test start_lobby handles WebSocketDisconnect gracefully."""
    mock_lobby_manager.get_lobby.return_value = filled_lobby
    # Force a WebSocketDisconnect on the first connection
    filled_lobby.connections[0].socket.send_json.side_effect = WebSocketDisconnect
    await game_manager.start_lobby(filled_lobby.id)
    # Assert disconnect method was called for the disconnected user
    mock_lobby_manager.disconnect.assert_called_once_with(filled_lobby.connections[0].socket, filled_lobby.id)

# --------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_choice_all_choices_made_triggers_new_round(game_manager, mock_lobby_manager, filled_lobby):
    """Test submit_choice triggers a new round when all choices are made."""
    mock_lobby_manager.get_lobby.return_value = filled_lobby
    
    # Pre-populate chapters for all but the last player
    for conn in filled_lobby.connections[:-1]:
        conn_uuid = uuid.UUID(conn.id)
        chapter = MockChapter("Some text", ["choice A", "choice B"], choice=1)
        filled_lobby.game_state.chapters[conn_uuid] = [chapter]
    
    # Mock start_new_round method
    game_manager.start_new_round = AsyncMock()

    # The last player submits their choice
    last_player_conn = filled_lobby.connections[-1]
    last_player_uuid = uuid.UUID(last_player_conn.id)
    filled_lobby.game_state.chapters[last_player_uuid] = [MockChapter("Some text", ["choice C", "choice D"], choice=-1)]
    
    message = {"choice_index": 0}
    await game_manager.submit_choice(filled_lobby.id, last_player_conn.socket, message)

    # Assert start_new_round was called
    game_manager.start_new_round.assert_called_once_with(filled_lobby.id)
    
    # Assert the last player's choice was updated
    assert filled_lobby.game_state.chapters[last_player_uuid][-1].choice == 0

@pytest.mark.asyncio
async def test_submit_choice_not_all_choices_made(game_manager, mock_lobby_manager, filled_lobby):
    """Test submit_choice updates the choice but doesn't trigger a new round."""
    mock_lobby_manager.get_lobby.return_value = filled_lobby
    game_manager.start_new_round = AsyncMock()

    # Only one player submits a choice
    first_player_conn = filled_lobby.connections[0]
    first_player_uuid = uuid.UUID(first_player_conn.id)
    filled_lobby.game_state.chapters[first_player_uuid] = [MockChapter("Some text", ["choice X", "choice Y"], choice=-1)]
    
    message = {"choice_index": 0}
    await game_manager.submit_choice(filled_lobby.id, first_player_conn.socket, message)

    # Assert start_new_round was NOT called
    game_manager.start_new_round.assert_not_called()
    
    # Assert the choice was updated for the submitting player
    assert filled_lobby.game_state.chapters[first_player_uuid][-1].choice == 0
    # Assert other players' choices remain at the default -1
    for conn in filled_lobby.connections[1:]:
        conn_uuid = uuid.UUID(conn.id)
        if conn_uuid in filled_lobby.game_state.chapters:
            assert filled_lobby.game_state.chapters[conn_uuid][-1].choice == -1

@pytest.mark.asyncio
async def test_submit_choice_no_lobby_found(game_manager, mock_lobby_manager, mock_websocket):
    """Test submit_choice gracefully returns if the lobby is not found."""
    mock_lobby_manager.get_lobby.return_value = None
    # Method should not raise an error or crash
    await game_manager.submit_choice("non-existent-lobby", mock_websocket, {"choice_index": 0})
    mock_lobby_manager.get_lobby.assert_called_once_with("non-existent-lobby")

@pytest.mark.asyncio
async def test_start_new_round_no_lobby(game_manager, mock_lobby_manager):
    """Test start_new_round handles a non-existent lobby."""
    mock_lobby_manager.get_lobby.return_value = None
    await game_manager.start_new_round("non-existent-lobby")
    # Assert nothing breaks and it just returns
    mock_lobby_manager.get_lobby.assert_called_once_with("non-existent-lobby")

@pytest.mark.asyncio
async def test_start_new_round_no_adventure(game_manager, mock_lobby_manager, new_lobby):
    """Test start_new_round handles a lobby without a set adventure."""
    mock_lobby_manager.get_lobby.return_value = new_lobby
    new_lobby.game_state.adventure = None
    await game_manager.start_new_round(new_lobby.id)
    # Assert it returns without errors
    mock_lobby_manager.get_lobby.assert_called_once_with(new_lobby.id)
