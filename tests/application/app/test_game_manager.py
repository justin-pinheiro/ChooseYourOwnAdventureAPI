import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from application.app.game_manager import GameManager
from domain.game_state import GameState
from domain.adventure import Adventure
from domain.chapter import Chapter
from domain.map import Map, Area

# Configure pytest for asyncio
pytest_plugins = ('pytest_asyncio',)


class TestGameManager:
    """Test suite for GameManager class"""

    @pytest.fixture
    def game_manager(self) -> GameManager:
        """Create a GameManager instance for testing"""
        return GameManager()

    @pytest.fixture
    def mock_adventure(self):
        """Create a mock Adventure object"""
        # Create a simple map with one area
        area = Area(id=0, name="Starting Area", description="Where the adventure begins")
        test_map = Map(id=1, areas=[area])
        
        return Adventure(
            id=1,
            title="Test Adventure",
            description="A test adventure",
            minPlayers=1,
            maxPlayers=4,
            map=test_map
        )

    @pytest.fixture
    def game_state(self):
        """Create a GameState instance for testing"""
        return GameState()

    @pytest.fixture
    def sample_chapter(self):
        """Create a sample Chapter for testing"""
        return Chapter(
            text="You find yourself in a dark forest...",
            possiblities=["Go left", "Go right", "Stay put"],
            choice=None
        )

    def test_game_manager_initialization(self, game_manager):
        """Test that GameManager initializes correctly"""
        assert game_manager is not None
        assert hasattr(game_manager, 'story_manager')
        assert game_manager.story_manager is not None

    @pytest.mark.asyncio
    async def test_submit_choice_with_existing_chapter(self, game_manager, game_state, sample_chapter):
        """Test submitting a choice when player has existing chapters"""
        # Setup
        player_id = str(uuid.uuid4())
        game_state.chapters[player_id] = [sample_chapter]
        message = {"choice_index": 1}

        # Execute
        await game_manager.submit_choice(game_state, player_id, message)

        # Assert
        assert game_state.chapters[player_id][0].choice == 1

    @pytest.mark.asyncio
    async def test_submit_choice_with_no_chapters(self, game_manager, game_state):
        """Test submitting a choice when player has no chapters"""
        # Setup
        player_id = str(uuid.uuid4())
        game_state.chapters[player_id] = []
        message = {"choice_index": 1}

        # Execute - should not raise an exception
        await game_manager.submit_choice(game_state, player_id, message)

        # Assert - no chapters should still be empty
        assert game_state.chapters[player_id] == []

    @pytest.mark.asyncio
    async def test_submit_choice_with_nonexistent_player(self, game_manager, game_state):
        """Test submitting a choice for a player that doesn't exist"""
        # Setup
        player_id = "nonexistent-player"
        message = {"choice_index": 1}

        # Execute - should not raise an exception
        await game_manager.submit_choice(game_state, player_id, message)

        # Assert - game state should remain unchanged
        assert player_id not in game_state.chapters

    @pytest.mark.asyncio
    @patch('application.app.game_manager.StoryManager')
    async def test_start_new_round_increments_round(self, mock_story_manager_class, game_manager, game_state, mock_adventure, sample_chapter):
        """Test that starting a new round increments the round number"""
        # Setup
        mock_story_manager = Mock()
        mock_story_manager.generate_chapter = AsyncMock(return_value=sample_chapter)
        mock_story_manager_class.return_value = mock_story_manager
        game_manager.story_manager = mock_story_manager
        
        player_id = str(uuid.uuid4())
        game_state.chapters[player_id] = []
        initial_round = game_state.round

        # Execute
        await game_manager.start_new_round(game_state, mock_adventure)

        # Assert
        assert game_state.round == initial_round + 1

    @pytest.mark.asyncio
    @patch('application.app.game_manager.StoryManager')
    async def test_start_new_round_generates_chapters_for_all_players(self, mock_story_manager_class, game_manager, game_state, mock_adventure, sample_chapter):
        """Test that starting a new round generates chapters for all players"""
        # Setup
        mock_story_manager = Mock()
        mock_story_manager.generate_chapter = AsyncMock(return_value=sample_chapter)
        mock_story_manager_class.return_value = mock_story_manager
        game_manager.story_manager = mock_story_manager

        player1_id = str(uuid.uuid4())
        player2_id = str(uuid.uuid4())
        game_state.chapters[player1_id] = []
        game_state.chapters[player2_id] = []

        # Execute
        await game_manager.start_new_round(game_state, mock_adventure)

        # Assert
        assert len(game_state.chapters[player1_id]) == 1
        assert len(game_state.chapters[player2_id]) == 1
        assert game_state.chapters[player1_id][0] == sample_chapter
        assert game_state.chapters[player2_id][0] == sample_chapter
        
        # Verify story manager was called for each player
        assert mock_story_manager.generate_chapter.call_count == 2

    @pytest.mark.asyncio
    @patch('application.app.game_manager.StoryManager')
    async def test_start_new_round_with_existing_chapters(self, mock_story_manager_class, game_manager, game_state, mock_adventure, sample_chapter):
        """Test starting a new round when players already have chapters"""
        # Setup
        mock_story_manager = Mock()
        new_chapter = Chapter(
            text="A new chapter begins...",
            possiblities=["New choice 1", "New choice 2"],
            choice=None
        )
        mock_story_manager.generate_chapter = AsyncMock(return_value=new_chapter)
        mock_story_manager_class.return_value = mock_story_manager
        game_manager.story_manager = mock_story_manager

        player_id = str(uuid.uuid4())
        game_state.chapters[player_id] = [sample_chapter]

        # Execute
        await game_manager.start_new_round(game_state, mock_adventure)

        # Assert
        assert len(game_state.chapters[player_id]) == 2
        assert game_state.chapters[player_id][0] == sample_chapter
        assert game_state.chapters[player_id][1] == new_chapter

    @pytest.mark.asyncio
    @patch('application.app.game_manager.StoryManager')
    async def test_start_new_round_story_manager_called_with_correct_params(self, mock_story_manager_class, game_manager, game_state, mock_adventure, sample_chapter):
        """Test that story manager is called with correct parameters"""
        # Setup
        mock_story_manager = Mock()
        mock_story_manager.generate_chapter = AsyncMock(return_value=sample_chapter)
        mock_story_manager_class.return_value = mock_story_manager
        game_manager.story_manager = mock_story_manager

        player_id = str(uuid.uuid4())
        game_state.chapters[player_id] = []

        # Execute
        await game_manager.start_new_round(game_state, mock_adventure)

        # Assert
        mock_story_manager.generate_chapter.assert_called_once_with(
            player_name="Jean",
            adventure=mock_adventure,
            previous_chapters=None,
            last_choice=None
        )

    @pytest.mark.asyncio
    async def test_start_new_round_with_empty_game_state(self, game_manager, game_state, mock_adventure):
        """Test starting a new round with no players"""
        # Setup - empty game state
        initial_round = game_state.round

        # Execute
        await game_manager.start_new_round(game_state, mock_adventure)

        # Assert
        assert game_state.round == initial_round + 1
        assert len(game_state.chapters) == 0