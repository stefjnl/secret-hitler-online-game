"""
Game Manager service for Secret Hitler Online.
Handles game lifecycle, player management, and action processing.
"""
import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from ..models.game_models import Game, GameState, Player, PolicyType
from ..services.game_engine import GameEngine
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.ai_integration import AIIntegrationService
    from ..api.websocket_manager import WebSocketManager
from ..api.models import (
    GameStateResponse, PlayerResponse, BoardStateResponse,
    GameHistoryEntry, AvailableActionsResponse, GameStatus, GamePhase
)

logger = logging.getLogger(__name__)

class GameManager:
    """Manages multiple concurrent games and their lifecycles."""

    def __init__(self, websocket_manager: Optional["WebSocketManager"] = None):
        self.websocket_manager = websocket_manager
        self.active_games: Dict[str, Dict[str, Any]] = {}
        self.player_sessions: Dict[str, str] = {}  # player_id -> game_id
        self.game_cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self.game_cleanup_task is None or self.game_cleanup_task.done():
            self.game_cleanup_task = asyncio.create_task(self._cleanup_inactive_games())

    async def broadcast_game_update(self, game_id: str, event_type: str, event_data: Dict[str, Any]) -> None:
        """Broadcast a game update to all connected players."""
        if not self.websocket_manager:
            return

        try:
            message = {
                "type": "game_update",
                "event_type": event_type,
                "game_id": game_id,
                "data": event_data
            }
            await self.websocket_manager.broadcast_to_game(game_id, message)
        except Exception as e:
            logger.error(f"Failed to broadcast game update for {game_id}: {e}")

    async def broadcast_player_action(self, game_id: str, player_id: str, action_type: str, action_data: Dict[str, Any]) -> None:
        """Broadcast a player action to all connected players."""
        if not self.websocket_manager:
            return

        try:
            message = {
                "type": "player_action",
                "player_id": player_id,
                "action_type": action_type,
                "game_id": game_id,
                "data": action_data
            }
            await self.websocket_manager.broadcast_to_game(game_id, message)
        except Exception as e:
            logger.error(f"Failed to broadcast player action for {game_id}: {e}")

    async def create_game(self, creator_name: str) -> str:
        """Create a new game room."""
        game_id = str(uuid.uuid4())

        # Create game with initial player
        player_names = [creator_name]
        game = Game.create_new_game(player_names)

        # Initialize game context
        game_context = {
            "game": game,
            "engine": GameEngine(game),
            "players": {game.players[0].id: game.players[0]},
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "status": GameStatus.WAITING
        }

        self.active_games[game_id] = game_context
        self.player_sessions[game.players[0].id] = game_id

        logger.info(f"Created game {game_id} with creator {creator_name}")
        return game_id

    async def join_game(self, game_id: str, player_name: str) -> Dict[str, Any]:
        """Join an existing game."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]

        if game_context["status"] != GameStatus.WAITING:
            raise ValueError("Game has already started")

        if len(game_context["players"]) >= 10:  # Max players
            raise ValueError("Game is full")

        # Check for duplicate names
        existing_names = [p.name for p in game_context["players"].values()]
        if player_name in existing_names:
            raise ValueError("Player name already taken")

        # Add player to game
        player = Player(id=str(uuid.uuid4()), name=player_name, is_human=True)
        game_context["game"].players.append(player)
        game_context["players"][player.id] = player
        game_context["last_activity"] = datetime.now()
        self.player_sessions[player.id] = game_id

        logger.info(f"Player {player_name} joined game {game_id}")
        return {
            "player_id": player.id,
            "game_id": game_id,
            "player_count": len(game_context["players"])
        }

    async def start_game(self, game_id: str) -> Dict[str, Any]:
        """Start a game when ready."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]

        if game_context["status"] != GameStatus.WAITING:
            raise ValueError("Game has already started")

        player_count = len(game_context["players"])
        if player_count < 5:
            raise ValueError("Need at least 5 players to start")

        # Start the game
        game_context["engine"].start_game()
        game_context["status"] = GameStatus.IN_PROGRESS
        game_context["last_activity"] = datetime.now()

        logger.info(f"Started game {game_id} with {player_count} players")
        return {
            "status": "started",
            "player_count": player_count,
            "game_phase": game_context["engine"].get_current_phase()
        }

    async def leave_game(self, game_id: str, player_id: str) -> None:
        """Remove a player from a game."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]

        if player_id not in game_context["players"]:
            raise ValueError("Player not in game")

        # Remove player
        player = game_context["players"].pop(player_id)
        game_context["game"].players.remove(player)

        if player_id in self.player_sessions:
            del self.player_sessions[player_id]

        game_context["last_activity"] = datetime.now()

        # End game if too few players remain
        remaining_players = len(game_context["players"])
        if remaining_players < 5 and game_context["status"] == GameStatus.IN_PROGRESS:
            game_context["status"] = GameStatus.COMPLETED
            logger.info(f"Game {game_id} ended due to insufficient players")

        logger.info(f"Player {player.name} left game {game_id}")

    async def get_game_state(self, game_id: str) -> GameStateResponse:
        """Get the current state of a game."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        game = game_context["game"]

        # Convert to API response format
        players = [
            PlayerResponse(
                id=p.id,
                name=p.name,
                is_alive=p.is_alive,
                role=p.role if p.role else None,
                is_president=(game.current_president == p.id),
                is_chancellor=(game.current_chancellor == p.id),
                is_connected=True  # TODO: Implement connection tracking
            )
            for p in game.players
        ]

        board = BoardStateResponse(
            liberal_policies=game.liberal_policies_enacted,
            fascist_policies=game.fascist_policies_enacted,
            election_tracker=game.election_tracker,
            failed_elections=game.failed_elections,
            veto_power_available=game.can_veto()
        )

        winner = None
        if game.winner:
            winner = game.winner.value

        return GameStateResponse(
            id=game_id,
            status=game_context["status"],
            phase=GamePhase(game.current_phase.value),
            players=players,
            board=board,
            current_president=game.current_president,
            current_chancellor=game.current_chancellor,
            winner=winner
        )

    async def get_players(self, game_id: str) -> List[PlayerResponse]:
        """Get all players in a game."""
        game_state = await self.get_game_state(game_id)
        return game_state.players

    async def get_board_state(self, game_id: str) -> BoardStateResponse:
        """Get the current board state."""
        game_state = await self.get_game_state(game_id)
        return game_state.board

    async def get_game_history(self, game_id: str, limit: int = 50) -> List[GameHistoryEntry]:
        """Get game action history."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        # TODO: Implement proper history tracking
        # For now, return empty list
        return []

    async def get_available_actions(self, game_id: str, player_id: str) -> AvailableActionsResponse:
        """Get available actions for a player."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        # Get available actions from engine
        actions = engine.get_available_actions(player_id)

        return AvailableActionsResponse(
            can_nominate_chancellor=actions.get("nominate_chancellor", False),
            can_vote=actions.get("vote", False),
            can_discard_policy=actions.get("discard_policy", False),
            can_enact_policy=actions.get("enact_policy", False),
            can_use_power=actions.get("use_power", False),
            can_veto=actions.get("veto", False),
            eligible_chancellors=actions.get("eligible_chancellors", []),
            available_policies=actions.get("available_policies", []),
            presidential_power=actions.get("presidential_power")
        )

    async def get_current_phase(self, game_id: str) -> Dict[str, Any]:
        """Get current game phase information."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        return {
            "phase": engine.get_current_phase(),
            "phase_data": {}  # TODO: Add phase-specific data
        }

    async def get_current_turn(self, game_id: str) -> Dict[str, Any]:
        """Get whose turn it currently is."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        return {
            "current_player": engine.get_current_player(),
            "is_player_turn": engine.is_player_turn
        }

    # Action methods - these delegate to the GameEngine
    async def nominate_chancellor(self, game_id: str, president_id: str, chancellor_id: str) -> Dict[str, Any]:
        """Nominate a chancellor."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        result = engine.nominate_chancellor(president_id, chancellor_id)
        game_context["last_activity"] = datetime.now()

        # Broadcast the nomination
        await self.broadcast_player_action(game_id, president_id, "nominate_chancellor", {
            "chancellor_id": chancellor_id,
            "result": result
        })

        return result

    async def submit_vote(self, game_id: str, player_id: str, vote: bool) -> Dict[str, Any]:
        """Submit an election vote."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        result = engine.submit_vote(player_id, vote)
        game_context["last_activity"] = datetime.now()

        return result

    async def discard_policy(self, game_id: str, player_id: str, policy: PolicyType) -> Dict[str, Any]:
        """Discard a policy as president."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        result = engine.president_discard_policy(policy)
        game_context["last_activity"] = datetime.now()

        return result

    async def enact_policy(self, game_id: str, player_id: str, policy: PolicyType) -> Dict[str, Any]:
        """Enact a policy as chancellor."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        result = engine.chancellor_enact_policy(policy)
        game_context["last_activity"] = datetime.now()

        return result

    async def use_presidential_power(self, game_id: str, player_id: str, target_id: Optional[str]) -> Dict[str, Any]:
        """Use a presidential power."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]
        engine = game_context["engine"]

        # Determine which power to use based on current game state
        # TODO: Implement power selection logic
        result = {"power_used": "investigate_loyalty", "target": target_id}
        game_context["last_activity"] = datetime.now()

        return result

    async def send_chat_message(self, game_id: str, player_id: str, message: str) -> Dict[str, Any]:
        """Send a chat message."""
        if game_id not in self.active_games:
            raise ValueError("Game not found")

        game_context = self.active_games[game_id]

        # TODO: Implement chat message storage and broadcasting
        result = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": player_id,
            "message": message
        }
        game_context["last_activity"] = datetime.now()

        return result

    async def cleanup_all_games(self) -> None:
        """Clean up all active games."""
        for game_id, game_context in list(self.active_games.items()):
            try:
                await self._cleanup_game(game_id)
            except Exception as e:
                logger.error(f"Error cleaning up game {game_id}: {e}")

    async def _cleanup_inactive_games(self) -> None:
        """Background task to clean up inactive games."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                cutoff_time = datetime.now() - timedelta(hours=1)
                inactive_games = [
                    game_id for game_id, context in self.active_games.items()
                    if context["last_activity"] < cutoff_time
                ]

                for game_id in inactive_games:
                    logger.info(f"Cleaning up inactive game {game_id}")
                    await self._cleanup_game(game_id)

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _cleanup_game(self, game_id: str) -> None:
        """Clean up a specific game."""
        if game_id in self.active_games:
            game_context = self.active_games[game_id]

            # Remove player sessions
            for player_id in list(game_context["players"].keys()):
                if player_id in self.player_sessions:
                    del self.player_sessions[player_id]

            # Remove game
            del self.active_games[game_id]
            logger.info(f"Cleaned up game {game_id}")