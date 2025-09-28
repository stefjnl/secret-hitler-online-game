"""
Integration tests for the AI player system with the GameEngine.
"""

import unittest
import asyncio
from app.services.game_engine import GameEngine
from app.models.game_models import Game, Player, Role, GamePhase
from app.services.ai_players import AIPersonality


class TestAIIntegration(unittest.TestCase):
    """Tests for AI player integration with the GameEngine."""

    def setUp(self):
        """Set up a game with one AI player."""
        player_names = ["Human1", "Human2", "Human3", "Human4", "AIPlayer"]
        self.game = Game.create_new_game(player_names)
        self.ai_player_model = self.game.players[4]
        self.ai_player_model.is_human = False
        self.engine = GameEngine(self.game)
        self.engine.register_ai_players()

    def test_ai_chancellor_nomination(self):
        """Test that the AI can be asked to nominate a chancellor."""
        self.engine.start_game()
        self.game.game_state.phase = GamePhase.ELECTION
        self.game.game_state.presidential_candidate_id = self.ai_player_model.id

        async def run_test():
            eligible_players = self.game.get_eligible_chancellors(self.ai_player_model.id)
            options = {"eligible_players": eligible_players}
            nomination = await self.engine.ai_manager.request_ai_decision(
                self.ai_player_model.id, "nominate_chancellor", options
            )
            self.assertIn(nomination, [p.id for p in eligible_players])

        asyncio.run(run_test())


    def test_full_ai_game(self):
        """Test a full game with only AI players."""
        player_names = ["AI1", "AI2", "AI3", "AI4", "AI5"]
        game = Game.create_new_game(player_names)
        for player in game.players:
            player.is_human = False
        engine = GameEngine(game)
        engine.register_ai_players()

        async def run_game():
            engine.start_game()
            while not engine.is_game_over():
                await asyncio.sleep(1) # Allow time for AI decisions

        asyncio.run(run_game())
        self.assertTrue(engine.is_game_over())
        self.assertIsNotNone(engine.get_winner())


if __name__ == '__main__':
    unittest.main()