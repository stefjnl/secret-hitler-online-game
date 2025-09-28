"""
Unit tests for the AI player system.
"""

import unittest
from app.services.ai_players import AIPlayer, AIPersonality, GameAnalysis, AIMemory
from app.models.game_models import Game, Player, Role, Party


class TestAIFramework(unittest.TestCase):
    """Tests for the foundational AI framework classes."""

    def setUp(self):
        """Set up a mock game and AI player for testing."""
        player_names = ["Alice", "Bob", "Charlie", "David", "Eve"]
        self.game = Game.create_new_game(player_names)
        self.ai_player_model = self.game.players[0]
        self.ai_player = AIPlayer(
            player_id=self.ai_player_model.id,
            personality=AIPersonality.CAUTIOUS_CONSERVATIVE
        )

    def test_ai_player_initialization(self):
        """Test that the AIPlayer class initializes correctly."""
        self.assertEqual(self.ai_player.player_id, self.ai_player_model.id)
        self.assertEqual(self.ai_player.personality, AIPersonality.CAUTIOUS_CONSERVATIVE)
        self.assertIsInstance(self.ai_player.memory, AIMemory)

    def test_game_analysis_initialization(self):
        """Test that the GameAnalysis class initializes correctly."""
        analysis = self.ai_player.analyze_game_state(self.game)
        self.assertIsInstance(analysis, GameAnalysis)
        self.assertEqual(analysis.game, self.game)
        self.assertEqual(analysis.player_perspective, self.ai_player_model)

    def test_placeholder_methods(self):
        """Test that the placeholder methods run without errors."""
        analysis = self.ai_player.analyze_game_state(self.game)
        self.assertIsInstance(analysis.calculate_suspicion_levels(), dict)
        self.assertIsInstance(analysis.identify_likely_fascists(), list)
        self.assertIsInstance(analysis.assess_win_probability(), dict)
        self.assertIsInstance(analysis.evaluate_policy_implications(None), dict)
        self.assertIsInstance(analysis.analyze_voting_patterns(), dict)
        self.assertIsNone(self.ai_player.generate_chat_message("test"))
        self.assertIsNone(self.ai_player.update_memory({}))

    def test_decide_chancellor_nomination_as_liberal(self):
        """Test chancellor nomination as a liberal."""
        self.ai_player_model.role = Role.LIBERAL
        self.ai_player.analyze_game_state(self.game)
        eligible_players = [p for p in self.game.players if p.id != self.ai_player_model.id]
        options = {"eligible_players": eligible_players}
        nomination = self.ai_player.make_decision("nominate_chancellor", options)
        # Liberals should nominate the player with the lowest suspicion (mocked as the first player)
        self.assertEqual(nomination, eligible_players[0].id)

    def test_decide_vote_as_liberal(self):
        """Test voting as a liberal."""
        self.ai_player_model.role = Role.LIBERAL
        self.ai_player.analyze_game_state(self.game)
        president = self.game.players[1]
        chancellor = self.game.players[2]
        options = {"president": president, "chancellor": chancellor}
        vote = self.ai_player.make_decision("vote", options)
        # Liberals should vote 'ja' on a low-suspicion government
        self.assertTrue(vote)

    def test_decide_vote_as_fascist(self):
        """Test voting as a fascist."""
        self.ai_player_model.role = Role.FASCIST
        self.ai_player.analyze_game_state(self.game)
        president = self.game.players[1]
        president.role = Role.FASCIST
        chancellor = self.game.players[2]
        options = {"president": president, "chancellor": chancellor}
        vote = self.ai_player.make_decision("vote", options)
        # Fascists should vote 'ja' for their own party members
        self.assertTrue(vote)

    def test_fascist_coordination_nomination(self):
        """Test that fascists nominate each other."""
        self.ai_player_model.role = Role.FASCIST
        fascist_teammate = self.game.players[1]
        fascist_teammate.role = Role.FASCIST
        self.ai_player.analyze_game_state(self.game)
        eligible_players = [p for p in self.game.players if p.id != self.ai_player_model.id]
        options = {"eligible_players": eligible_players}
        nomination = self.ai_player.make_decision("nominate_chancellor", options)
        self.assertEqual(nomination, fascist_teammate.id)

    def test_choose_policy_to_discard_as_liberal(self):
        """Test policy discard as a liberal."""
        self.ai_player_model.role = Role.LIBERAL
        self.ai_player.analyze_game_state(self.game)
        policies = [PolicyType.LIBERAL, PolicyType.FASCIST, PolicyType.LIBERAL]
        options = {"policies": policies}
        discarded = self.ai_player.make_decision("discard_policy", options)
        self.assertEqual(discarded, PolicyType.FASCIST)

    def test_choose_policy_to_discard_as_fascist(self):
        """Test policy discard as a fascist."""
        self.ai_player_model.role = Role.FASCIST
        self.ai_player.analyze_game_state(self.game)
        policies = [PolicyType.LIBERAL, PolicyType.FASCIST, PolicyType.FASCIST]
        options = {"policies": policies}
        discarded = self.ai_player.make_decision("discard_policy", options)
        self.assertEqual(discarded, PolicyType.LIBERAL)

    def test_choose_policy_to_enact(self):
        """Test policy enactment."""
        policies = [PolicyType.FASCIST, PolicyType.LIBERAL]
        options = {"policies": policies}
        enacted = self.ai_player.make_decision("enact_policy", options)
        self.assertEqual(enacted, PolicyType.FASCIST)

    def test_choose_investigation_target_as_liberal(self):
        """Test investigation target selection as a liberal."""
        self.ai_player_model.role = Role.LIBERAL
        self.ai_player.analyze_game_state(self.game)
        eligible_players = [p for p in self.game.players if p.id != self.ai_player_model.id]
        options = {"eligible_players": eligible_players}
        target = self.ai_player.make_decision("investigate_loyalty", options)
        # Should investigate the most suspicious player (mocked as the last player)
        self.assertEqual(target, eligible_players[-1].id)

    def test_choose_execution_target_as_liberal(self):
        """Test execution target selection as a liberal."""
        self.ai_player_model.role = Role.LIBERAL
        self.ai_player.analyze_game_state(self.game)
        eligible_players = [p for p in self.game.players if p.id != self.ai_player_model.id]
        options = {"eligible_players": eligible_players}
        target = self.ai_player.make_decision("execute_player", options)
        # Should execute the most suspicious player (mocked as the last player)
        self.assertEqual(target, eligible_players[-1].id)

    def test_choose_special_election_nominee_as_liberal(self):
        """Test special election nominee selection as a liberal."""
        self.ai_player_model.role = Role.LIBERAL
        self.ai_player.analyze_game_state(self.game)
        eligible_players = [p for p in self.game.players if p.id != self.ai_player_model.id]
        options = {"eligible_players": eligible_players}
        nominee = self.ai_player.make_decision("call_special_election", options)
        # Should nominate the least suspicious player (mocked as the first player)
        self.assertEqual(nominee, eligible_players[0].id)

    def test_generate_chat_message(self):
        """Test the generate_chat_message method."""
        self.ai_player.personality = AIPersonality.BOLD_AGGRESSOR
        message = self.ai_player.generate_chat_message("confidence")
        self.assertEqual(message, "Trust me on this one.")

    def test_beginner_difficulty(self):
        """Test that beginner AI has a chance of making random decisions."""
        self.ai_player.difficulty = AIDifficulty.BEGINNER
        # This is a probabilistic test, so we run it multiple times.
        random_decisions = 0
        for _ in range(100):
            vote = self.ai_player.make_decision("vote", {"president": self.game.players[1], "chancellor": self.game.players[2]})
            if vote != (self.ai_player.analyze_game_state(self.game).calculate_suspicion_levels().get(self.game.players[1].id, 0.5) < 0.6):
                random_decisions += 1
        self.assertGreater(random_decisions, 0)


if __name__ == '__main__':
    unittest.main()