"""
Unit tests for Secret Hitler Online API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.main import app
from app.services.game_manager import GameManager
from app.services.ai_integration import AIIntegrationService

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)

@pytest.fixture
def mock_game_manager():
    """Mock GameManager fixture."""
    manager = AsyncMock(spec=GameManager)
    manager.create_game.return_value = "test-game-id"
    manager.join_game.return_value = {"player_id": "test-player-id", "game_id": "test-game-id"}
    manager.start_game.return_value = {"status": "started"}
    manager.get_game_state.return_value = MagicMock()
    return manager

@pytest.fixture
def mock_ai_integration():
    """Mock AIIntegrationService fixture."""
    integration = AsyncMock(spec=AIIntegrationService)
    return integration

class TestGameManagementEndpoints:
    """Test game management endpoints."""

    def test_create_game_success(self, client, mock_game_manager, mock_ai_integration):
        """Test successful game creation."""
        with patch('app.api.main.game_manager', mock_game_manager), \
             patch('app.api.main.ai_integration', mock_ai_integration):

            response = client.post("/api/games/create", json={"creator_name": "TestPlayer"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "game_id" in data["data"]

    def test_create_game_invalid_name(self, client):
        """Test game creation with invalid name."""
        response = client.post("/api/games/create", json={"creator_name": ""})

        assert response.status_code == 422  # Validation error

    def test_join_game_success(self, client, mock_game_manager):
        """Test successful game join."""
        with patch('app.api.main.game_manager', mock_game_manager):
            response = client.post("/api/games/test-game/join",
                                 json={"player_name": "NewPlayer"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "player_id" in data["data"]

    def test_join_game_not_found(self, client, mock_game_manager):
        """Test joining non-existent game."""
        mock_game_manager.join_game.side_effect = ValueError("Game not found")

        with patch('app.api.main.game_manager', mock_game_manager):
            response = client.post("/api/games/invalid-game/join",
                                 json={"player_name": "Player"})

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "Game not found" in data["error"]["details"]["message"]

    def test_start_game_success(self, client, mock_game_manager, mock_ai_integration):
        """Test successful game start."""
        with patch('app.api.main.game_manager', mock_game_manager), \
             patch('app.api.main.ai_integration', mock_ai_integration):

            response = client.post("/api/games/test-game/start")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "started"

class TestPlayerActionEndpoints:
    """Test player action endpoints."""

    def test_nominate_chancellor_success(self, client, mock_game_manager, mock_ai_integration):
        """Test successful chancellor nomination."""
        mock_game_manager.nominate_chancellor.return_value = {"nominated": "player-2"}

        with patch('app.api.main.game_manager', mock_game_manager), \
             patch('app.api.main.ai_integration', mock_ai_integration):

            response = client.post("/api/games/test-game/nominate?player_id=player-1",
                                 json={"chancellor_id": "player-2"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_submit_vote_success(self, client, mock_game_manager, mock_ai_integration):
        """Test successful vote submission."""
        mock_game_manager.submit_vote.return_value = {"vote": True}

        with patch('app.api.main.game_manager', mock_game_manager), \
             patch('app.api.main.ai_integration', mock_ai_integration):

            response = client.post("/api/games/test-game/vote?player_id=player-1",
                                 json={"vote": True})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_send_chat_message_success(self, client, mock_game_manager, mock_ai_integration):
        """Test successful chat message sending."""
        mock_game_manager.send_chat_message.return_value = {
            "message_id": "msg-123",
            "timestamp": "2024-01-01T00:00:00",
            "sender": "player-1",
            "message": "Hello!"
        }

        with patch('app.api.main.game_manager', mock_game_manager), \
             patch('app.api.main.ai_integration', mock_ai_integration):

            response = client.post("/api/games/test-game/chat?player_id=player-1",
                                 json={"message": "Hello!"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["message"] == "Hello!"

class TestGameStateEndpoints:
    """Test game state endpoints."""

    def test_get_game_state_success(self, client, mock_game_manager):
        """Test successful game state retrieval."""
        mock_game_state = MagicMock()
        mock_game_state.id = "test-game"
        mock_game_state.status.value = "in_progress"
        mock_game_state.phase.value = "election"
        mock_game_state.players = []
        mock_game_state.board = MagicMock()
        mock_game_state.current_president = "player-1"
        mock_game_state.current_chancellor = "player-2"
        mock_game_state.winner = None

        mock_game_manager.get_game_state.return_value = mock_game_state

        with patch('app.api.main.game_manager', mock_game_manager):
            response = client.get("/api/games/test-game")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-game"
            assert data["status"] == "in_progress"

    def test_get_players_success(self, client, mock_game_manager):
        """Test successful players list retrieval."""
        mock_players = [MagicMock(id="p1", name="Player1", is_alive=True)]
        mock_game_manager.get_players.return_value = mock_players

        with patch('app.api.main.game_manager', mock_game_manager):
            response = client.get("/api/games/test-game/players")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_available_actions_success(self, client, mock_game_manager):
        """Test successful available actions retrieval."""
        mock_actions = MagicMock()
        mock_actions.can_nominate_chancellor = True
        mock_actions.can_vote = False
        mock_game_manager.get_available_actions.return_value = mock_actions

        with patch('app.api.main.game_manager', mock_game_manager):
            response = client.get("/api/games/test-game/available?player_id=player-1")

            assert response.status_code == 200
            data = response.json()
            assert "can_nominate_chancellor" in data

class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "secret-hitler-api"

class TestErrorHandling:
    """Test error handling."""

    def test_global_exception_handler(self, client, mock_game_manager):
        """Test global exception handling."""
        mock_game_manager.create_game.side_effect = Exception("Unexpected error")

        with patch('app.api.main.game_manager', mock_game_manager):
            response = client.post("/api/games/create", json={"creator_name": "Test"})

            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_validation_error(self, client):
        """Test request validation error."""
        response = client.post("/api/games/create", json={})  # Missing required field

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data