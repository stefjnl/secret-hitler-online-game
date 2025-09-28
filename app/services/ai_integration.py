"""
AI Integration Service for Secret Hitler Online.
Manages AI players and coordinates their actions with the game engine.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any

from .ai_players import AIDecisionManager, AIPlayer, AIPersonality
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_manager import GameManager
from ..models.game_models import Player

logger = logging.getLogger(__name__)

class AIIntegrationService:
    """Manages AI players and their integration with games."""

    def __init__(self, game_manager: "GameManager"):
        self.game_manager = game_manager
        self.ai_decision_manager = None  # Will be set when needed
        self.ai_players: Dict[str, AIPlayer] = {}  # player_id -> AIPlayer

    def _get_ai_decision_manager(self) -> AIDecisionManager:
        """Get or create the AI decision manager."""
        if self.ai_decision_manager is None:
            # Create a dummy game engine for now - this will be replaced with proper integration
            self.ai_decision_manager = AIDecisionManager(game_engine=None)
        return self.ai_decision_manager

    async def fill_with_ai_players(self, game_id: str, target_player_count: int = 7) -> None:
        """
        Fill a game with AI players to reach target player count.

        Args:
            game_id: ID of the game to fill
            target_player_count: Desired total player count
        """
        try:
            game_state = await self.game_manager.get_game_state(game_id)
            current_count = len(game_state.players)
            ai_needed = max(0, target_player_count - current_count)

            if ai_needed == 0:
                return

            # Add AI players
            for i in range(ai_needed):
                ai_name = f"AI_Player_{i+1}"
                join_result = await self.game_manager.join_game(game_id, ai_name)

                # Create AI player instance
                player_id = join_result["player_id"]
                personality = self._select_ai_personality(i)

                ai_player = AIPlayer(
                    player_id=player_id,
                    personality=personality
                )

                self.ai_players[player_id] = ai_player
                logger.info(f"Added AI player {ai_name} ({personality.value}) to game {game_id}")

        except Exception as e:
            logger.error(f"Failed to fill game {game_id} with AI players: {e}")
            raise

    async def process_ai_turns(self, game_id: str) -> None:
        """
        Process turns for all AI players in a game.

        Args:
            game_id: ID of the game
        """
        try:
            game_state = await self.game_manager.get_game_state(game_id)

            # Find AI players whose turn it is
            for player in game_state.players:
                if player.id in self.ai_players and not player.is_connected:  # AI players marked as disconnected
                    ai_player = self.ai_players[player.id]

                    # Check if it's this AI's turn
                    available_actions = await self.game_manager.get_available_actions(game_id, player.id)

                    if self._has_available_actions(available_actions):
                        await self._process_ai_action(game_id, ai_player, available_actions)
                        await asyncio.sleep(2)  # Realistic delay between AI actions

        except Exception as e:
            logger.error(f"Failed to process AI turns for game {game_id}: {e}")

    async def handle_ai_chat(self, game_id: str) -> None:
        """
        Generate and send AI chat messages.

        Args:
            game_id: ID of the game
        """
        try:
            game_state = await self.game_manager.get_game_state(game_id)

            # Randomly have AI players send chat messages
            for player in game_state.players:
                if player.id in self.ai_players:
                    ai_player = self.ai_players[player.id]

                    # 20% chance for AI to chat on each message
                    if asyncio.get_event_loop().time() % 5 < 1:  # Simple randomization
                        chat_message = ai_player.generate_chat_message("casual")
                        if chat_message:
                            await self.game_manager.send_chat_message(game_id, player.id, chat_message)
                            await asyncio.sleep(1)  # Delay between AI messages

        except Exception as e:
            logger.error(f"Failed to handle AI chat for game {game_id}: {e}")

    async def recover_from_ai_failure(self, game_id: str, failed_player_id: str) -> None:
        """
        Recover from an AI player failure.

        Args:
            game_id: ID of the game
            failed_player_id: ID of the failed AI player
        """
        try:
            if failed_player_id in self.ai_players:
                logger.warning(f"Recovering from AI failure for player {failed_player_id} in game {game_id}")

                # Remove the failed AI player
                del self.ai_players[failed_player_id]

                # Try to replace with a new AI player
                try:
                    await self.fill_with_ai_players(game_id, len(await self.game_manager.get_players(game_id)) + 1)
                except Exception as e:
                    logger.error(f"Could not replace failed AI player: {e}")

        except Exception as e:
            logger.error(f"Failed to recover from AI failure: {e}")

    def _select_ai_personality(self, index: int) -> AIPersonality:
        """Select an AI personality based on index."""
        personalities = [AIPersonality.CAUTIOUS_CONSERVATIVE, AIPersonality.BOLD_AGGRESSOR]
        return personalities[index % len(personalities)]

    def _has_available_actions(self, available_actions: Dict[str, Any]) -> bool:
        """Check if there are any available actions for an AI player."""
        action_fields = [
            'can_nominate_chancellor', 'can_vote', 'can_discard_policy',
            'can_enact_policy', 'can_use_power', 'can_veto'
        ]

        return any(available_actions.get(field, False) for field in action_fields)

    async def _process_ai_action(self, game_id: str, ai_player: AIPlayer, available_actions: Dict[str, Any]) -> None:
        """
        Process a single AI player's action.

        Args:
            game_id: ID of the game
            ai_player: The AI player instance
            available_actions: Available actions for this player
        """
        try:
            game_state = await self.game_manager.get_game_state(game_id)

            # Determine action type and execute
            if available_actions.get('can_nominate_chancellor', False):
                await self._ai_nominate_chancellor(game_id, ai_player, game_state)

            elif available_actions.get('can_vote', False):
                await self._ai_vote(game_id, ai_player, game_state)

            elif available_actions.get('can_discard_policy', False):
                await self._ai_discard_policy(game_id, ai_player, available_actions)

            elif available_actions.get('can_enact_policy', False):
                await self._ai_enact_policy(game_id, ai_player, available_actions)

            elif available_actions.get('can_use_power', False):
                await self._ai_use_power(game_id, ai_player, game_state, available_actions)

        except Exception as e:
            logger.error(f"AI action processing failed for player {ai_player.player_id}: {e}")
            # Continue without crashing - AI failures shouldn't break the game

    async def _ai_nominate_chancellor(self, game_id: str, ai_player: AIPlayer, game_state: Any) -> None:
        """AI nominates a chancellor."""
        try:
            # Get eligible players (excluding self and recent office holders)
            eligible_players = []
            for player in game_state.players:
                if player.id != ai_player.player_id and player.is_alive:
                    # TODO: Check term limits
                    eligible_players.append(player.id)

            if eligible_players:
                # AI makes decision
                decision = ai_player.decide_chancellor_nomination(eligible_players)
                if decision and decision in eligible_players:
                    await self.game_manager.nominate_chancellor(game_id, ai_player.player_id, decision)
                    logger.info(f"AI {ai_player.player_id} nominated {decision}")

        except Exception as e:
            logger.error(f"AI chancellor nomination failed: {e}")

    async def _ai_vote(self, game_id: str, ai_player: AIPlayer, game_state: Any) -> None:
        """AI submits a vote."""
        try:
            # AI makes voting decision
            vote = ai_player.decide_vote(game_state)
            await self.game_manager.submit_vote(game_id, ai_player.player_id, vote)
            logger.info(f"AI {ai_player.player_id} voted {'Ja' if vote else 'Nein'}")

        except Exception as e:
            logger.error(f"AI voting failed: {e}")

    async def _ai_discard_policy(self, game_id: str, ai_player: AIPlayer, available_actions: Dict[str, Any]) -> None:
        """AI discards a policy as president."""
        try:
            available_policies = available_actions.get('available_policies', [])
            if available_policies:
                # AI chooses which policy to discard
                policy_to_discard = ai_player.choose_policy_to_discard(available_policies)
                if policy_to_discard in available_policies:
                    await self.game_manager.discard_policy(game_id, ai_player.player_id, policy_to_discard)
                    logger.info(f"AI {ai_player.player_id} discarded {policy_to_discard.value}")

        except Exception as e:
            logger.error(f"AI policy discard failed: {e}")

    async def _ai_enact_policy(self, game_id: str, ai_player: AIPlayer, available_actions: Dict[str, Any]) -> None:
        """AI enacts a policy as chancellor."""
        try:
            available_policies = available_actions.get('available_policies', [])
            if available_policies:
                # AI chooses which policy to enact
                policy_to_enact = ai_player.choose_policy_to_enact(available_policies)
                if policy_to_enact in available_policies:
                    await self.game_manager.enact_policy(game_id, ai_player.player_id, policy_to_enact)
                    logger.info(f"AI {ai_player.player_id} enacted {policy_to_enact.value}")

        except Exception as e:
            logger.error(f"AI policy enactment failed: {e}")

    async def _ai_use_power(self, game_id: str, ai_player: AIPlayer, game_state: Any, available_actions: Dict[str, Any]) -> None:
        """AI uses a presidential power."""
        try:
            power_type = available_actions.get('presidential_power')
            if power_type:
                # Determine target based on power type
                target_id = None
                if power_type in ['investigate_loyalty', 'call_special_election', 'execution']:
                    # Select target
                    alive_players = [p for p in game_state.players if p.is_alive and p.id != ai_player.player_id]
                    if alive_players:
                        target_id = ai_player.choose_investigation_target(alive_players) if power_type == 'investigate_loyalty' else alive_players[0].id

                await self.game_manager.use_presidential_power(game_id, ai_player.player_id, target_id)
                logger.info(f"AI {ai_player.player_id} used power {power_type} on {target_id}")

        except Exception as e:
            logger.error(f"AI presidential power failed: {e}")

    async def get_ai_player_count(self, game_id: str) -> int:
        """Get the number of AI players in a game."""
        try:
            players = await self.game_manager.get_players(game_id)
            ai_count = sum(1 for player in players if player.id in self.ai_players)
            return ai_count
        except Exception:
            return 0

    async def remove_ai_player(self, player_id: str) -> None:
        """Remove an AI player."""
        if player_id in self.ai_players:
            del self.ai_players[player_id]
            logger.info(f"Removed AI player {player_id}")