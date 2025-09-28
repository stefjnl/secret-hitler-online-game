"""
Comprehensive test suite for the GameEngine class.

This module tests all aspects of the game engine including:
- Phase transitions and state management
- Election logic and validation
- Legislative session mechanics
- Presidential power execution
- Error handling and edge cases
- Complete game scenarios
"""

import pytest
from unittest.mock import patch
from datetime import datetime

from app.models.game_models import (
    Game, GameState, Player, PolicyType, GamePhase,
    PresidentialPower, Party, Role
)
from app.services.game_engine import (
    GameEngine, GameEngineError, InvalidActionError, WrongPhaseError,
    NotPlayerTurnError, InvalidTargetError, GameOverError, EventType
)


class TestGameEngineInitialization:
    """Test GameEngine initialization and setup."""

    def test_engine_initialization(self):
        """Test successful engine initialization."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        assert engine.game == game
        assert engine.event_history == []
        assert engine.get_current_phase() == GamePhase.LOBBY

    def test_engine_initialization_invalid_game(self):
        """Test engine initialization with invalid game."""
        with pytest.raises(ValueError, match="Game instance is required"):
            GameEngine(None)

    def test_engine_initialization_wrong_phase(self):
        """Test engine initialization with game not in lobby."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        game.game_state.phase = GamePhase.ELECTION

        with pytest.raises(ValueError, match="Game must start in LOBBY phase"):
            GameEngine(game)


class TestGameStart:
    """Test game starting functionality."""

    def test_start_game_success(self):
        """Test successful game start."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        result = engine.start_game()

        assert result.phase == GamePhase.ROLE_REVEAL
        assert len(engine.event_history) == 2  # Phase change + game started
        assert any(event["event_type"] == EventType.GAME_STARTED.value for event in engine.event_history)

    def test_start_game_already_started(self):
        """Test starting game that's already started."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        with pytest.raises(InvalidActionError, match="Game has already started"):
            engine.start_game()

    def test_start_game_insufficient_players(self):
        """Test starting game with too few players."""
        # Create a valid game and then modify it to have insufficient players
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        # Remove a player to make it insufficient
        game.players.pop()
        game.game_state.liberal_policies = 0  # Reset any policy changes

        with pytest.raises(InvalidActionError, match="Need at least 5 players to start"):
            engine.start_game()


class TestAvailableActions:
    """Test available actions for different players and phases."""

    def test_lobby_phase_actions(self):
        """Test available actions in lobby phase."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        actions = engine.get_available_actions("player_0")
        assert "start_game" in actions

    def test_election_phase_president_actions(self):
        """Test president actions in election phase."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Transition to election phase
        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        actions = engine.get_available_actions("player_0")
        assert "nominate_chancellor" in actions

    def test_election_phase_voter_actions(self):
        """Test voter actions in election phase."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Transition to election phase
        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        actions = engine.get_available_actions("player_1")
        assert "submit_vote" in actions

    def test_invalid_player_actions(self):
        """Test actions for invalid player."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        actions = engine.get_available_actions("invalid_player")
        assert actions == []


class TestPlayerTurnValidation:
    """Test player turn validation."""

    def test_is_player_turn_president_election(self):
        """Test president turn in election phase."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        assert engine.is_player_turn("player_0") is True
        assert engine.is_player_turn("player_1") is True  # Can vote

    def test_is_player_turn_invalid_player(self):
        """Test turn validation for invalid player."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        assert engine.is_player_turn("invalid_player") is False


class TestChancellorNomination:
    """Test chancellor nomination functionality."""

    def test_nominate_chancellor_success(self):
        """Test successful chancellor nomination."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        result = engine.nominate_chancellor("player_0", "player_1")

        assert result["status"] == "nomination_successful"
        assert game.game_state.chancellor_candidate_id == "player_1"
        assert len(engine.event_history) >= 1

    def test_nominate_chancellor_wrong_phase(self):
        """Test nomination in wrong phase."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)

        with pytest.raises(WrongPhaseError):
            engine.nominate_chancellor("player_0", "player_1")

    def test_nominate_chancellor_not_president(self):
        """Test nomination by non-president."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        with pytest.raises(NotPlayerTurnError):
            engine.nominate_chancellor("player_1", "player_2")

    def test_nominate_chancellor_invalid_target(self):
        """Test nomination of invalid chancellor."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        with pytest.raises(InvalidTargetError):
            engine.nominate_chancellor("player_0", "player_0")  # Self-nomination


class TestVoting:
    """Test voting functionality."""

    def test_submit_vote_success(self):
        """Test successful vote submission."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.chancellor_candidate_id = "player_1"

        result = engine.submit_vote("player_2", True)

        assert result["status"] == "vote_recorded"
        assert game.game_state.votes["player_2"] is True

    def test_submit_vote_duplicate(self):
        """Test duplicate vote submission."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.chancellor_candidate_id = "player_1"
        game.game_state.votes["player_2"] = True

        with pytest.raises(InvalidActionError, match="Player has already voted"):
            engine.submit_vote("player_2", False)

    def test_submit_vote_president_cannot_vote(self):
        """Test that president cannot vote."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.chancellor_candidate_id = "player_1"

        with pytest.raises(InvalidActionError, match="President and chancellor cannot vote"):
            engine.submit_vote("player_0", True)


class TestElectionProcessing:
    """Test election result processing."""

    def test_successful_election(self):
        """Test processing of successful election."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.chancellor_candidate_id = "player_1"

        # Add majority yes votes
        for i in range(2, 5):  # 3 yes votes out of 5 total (3-2 majority)
            game.game_state.votes[f"player_{i}"] = True

        result = engine.process_election_results()

        assert result["status"] == "government_formed"
        assert game.game_state.phase == GamePhase.LEGISLATIVE_SESSION
        assert len(game.game_state.government_history) == 1

    def test_failed_election(self):
        """Test processing of failed election."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.chancellor_candidate_id = "player_1"

        # Create a fresh game state to ensure clean state
        game.game_state.election_tracker = 0  # Ensure clean state
        game.game_state.votes = {}  # Ensure clean votes

        # Add majority no votes (3 no votes out of 5 total = 3-2 majority against)
        game.game_state.votes = {
            "player_2": False,
            "player_3": False,
            "player_4": False
        }

        result = engine.process_election_results()

        assert result["status"] == "election_failed"
        assert game.game_state.election_tracker == 1
        assert game.game_state.phase == GamePhase.ELECTION


class TestLegislativeSession:
    """Test legislative session functionality."""

    def test_draw_policies_for_president(self):
        """Test drawing policies for president."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Set up legislative session
        game.game_state.phase = GamePhase.LEGISLATIVE_SESSION
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.chancellor_candidate_id = "player_1"

        policies = engine.draw_policies_for_president()

        assert len(policies) == 3
        assert all(policy in [PolicyType.LIBERAL, PolicyType.FASCIST] for policy in policies)

    def test_president_discard_policy(self):
        """Test president discarding policy."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.LEGISLATIVE_SESSION
        game.game_state.presidential_candidate_id = "player_0"

        result = engine.president_discard_policy(PolicyType.LIBERAL)

        assert result["status"] == "policy_discarded"
        assert PolicyType.LIBERAL in game.discard_pile

    def test_chancellor_enact_policy(self):
        """Test chancellor enacting policy."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.LEGISLATIVE_SESSION
        game.game_state.chancellor_candidate_id = "player_1"

        result = engine.chancellor_enact_policy(PolicyType.FASCIST)

        assert result["status"] == "policy_enacted"
        assert game.game_state.fascist_policies == 1


class TestPresidentialPowers:
    """Test presidential power execution."""

    def test_execute_investigate_loyalty(self):
        """Test investigate loyalty power."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Set up presidential power
        game.game_state.phase = GamePhase.PRESIDENTIAL_POWER
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.pending_presidential_power = PresidentialPower.INVESTIGATE_LOYALTY

        result = engine.execute_investigate_loyalty("player_1")

        assert result["status"] == "investigation_complete"
        assert "player_1" in game.game_state.investigated_players
        assert game.game_state.pending_presidential_power is None

    def test_execute_execution_hitler(self):
        """Test execution power on Hitler."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Find Hitler
        hitler = next(p for p in game.players if p.is_hitler())

        # Set up presidential power
        game.game_state.phase = GamePhase.PRESIDENTIAL_POWER
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.pending_presidential_power = PresidentialPower.EXECUTION

        result = engine.execute_execution(hitler.id)

        assert result["status"] == "execution_complete"
        assert not hitler.is_alive
        assert game.game_state.phase == GamePhase.GAME_OVER  # Hitler executed

    def test_execute_policy_peek(self):
        """Test policy peek power."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Set up presidential power
        game.game_state.phase = GamePhase.PRESIDENTIAL_POWER
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.pending_presidential_power = PresidentialPower.POLICY_PEEK

        policies = engine.execute_policy_peek()

        assert len(policies) == 3
        assert game.game_state.pending_presidential_power is None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_game_over_error(self):
        """Test actions after game is over."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # End the game
        game.game_state.phase = GamePhase.GAME_OVER

        with pytest.raises(GameOverError):
            engine.nominate_chancellor("player_0", "player_1")

    def test_wrong_phase_error(self):
        """Test actions in wrong phase."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Try to nominate in role reveal phase
        with pytest.raises(WrongPhaseError):
            engine.nominate_chancellor("player_0", "player_1")

    def test_invalid_target_error(self):
        """Test invalid target handling."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.PRESIDENTIAL_POWER
        game.game_state.presidential_candidate_id = "player_0"
        game.game_state.pending_presidential_power = PresidentialPower.INVESTIGATE_LOYALTY

        with pytest.raises(InvalidTargetError):
            engine.execute_investigate_loyalty("invalid_player")


class TestGameScenarios:
    """Test complete game scenarios."""

    def test_liberal_victory_scenario(self):
        """Test complete liberal victory game."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Simulate 5 liberal policies enacted (each requiring a new government)
        for i in range(5):
            # Set up election for each policy
            game.game_state.phase = GamePhase.ELECTION
            game.game_state.presidential_candidate_id = "player_0"
            game.game_state.chancellor_candidate_id = "player_1"
            game.game_state.votes = {
                "player_2": True,
                "player_3": True,
                "player_4": True
            }

            result = engine.process_election_results()
            assert result["status"] == "government_formed"
            assert game.game_state.phase == GamePhase.LEGISLATIVE_SESSION

            # Enact the policy
            engine.chancellor_enact_policy(PolicyType.LIBERAL)

        assert engine.is_game_over()
        assert engine.get_winner() == Party.LIBERAL

    def test_fascist_victory_scenario(self):
        """Test complete fascist victory game."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Simulate 6 fascist policies enacted (each requiring a new government)
        for i in range(6):
            # Set up election for each policy
            game.game_state.phase = GamePhase.ELECTION
            game.game_state.presidential_candidate_id = "player_0"
            game.game_state.chancellor_candidate_id = "player_1"
            game.game_state.votes = {
                "player_2": True,
                "player_3": True,
                "player_4": True
            }

            result = engine.process_election_results()
            assert result["status"] == "government_formed"
            assert game.game_state.phase == GamePhase.LEGISLATIVE_SESSION

            # Enact the policy
            engine.chancellor_enact_policy(PolicyType.FASCIST)

        assert engine.is_game_over()
        assert engine.get_winner() == Party.FASCIST

    def test_hitler_chancellor_victory(self):
        """Test Hitler chancellor victory scenario."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Find Hitler and set up scenario
        hitler = next(p for p in game.players if p.is_hitler())
        game.game_state.fascist_policies = 3
        game.game_state.government_history = [("player_0", hitler.id)]

        # Check win condition
        winner = game.check_win_condition()
        assert winner == Party.FASCIST


class TestEventSystem:
    """Test event generation and history."""

    def test_event_generation(self):
        """Test that events are properly generated."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        assert len(engine.event_history) == 2  # Phase change + game started
        game_started_event = next(event for event in engine.event_history
                                if event["event_type"] == EventType.GAME_STARTED.value)
        assert game_started_event["event_type"] == EventType.GAME_STARTED.value
        assert "timestamp" in game_started_event
        assert "game_id" in game_started_event
        assert "data" in game_started_event
        assert "game_state" in game_started_event

    def test_event_types(self):
        """Test different event types are generated."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Transition to election
        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        # Nominate chancellor
        engine.nominate_chancellor("player_0", "player_1")

        events = [event["event_type"] for event in engine.event_history]
        assert EventType.GAME_STARTED.value in events
        assert EventType.PHASE_CHANGED.value in events
        assert EventType.CHANCELLOR_NOMINATED.value in events


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_player_elimination_during_game(self):
        """Test handling of player elimination."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Find Hitler and eliminate them
        hitler = next(p for p in game.players if p.is_hitler())
        game.eliminate_player(hitler.id)

        assert engine.is_game_over()
        assert engine.get_winner() == Party.LIBERAL

    def test_policy_deck_reshuffle(self):
        """Test policy deck reshuffling."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        # Empty the deck
        game.policy_deck = []
        game.discard_pile = [PolicyType.LIBERAL] * 17

        # Draw policies should trigger reshuffle
        game.game_state.phase = GamePhase.LEGISLATIVE_SESSION
        game.game_state.presidential_candidate_id = "player_0"

        policies = engine.draw_policies_for_president()
        assert len(policies) == 3
        assert len(game.policy_deck) == 14  # 17 - 3 drawn


class TestPerformance:
    """Test performance characteristics."""

    def test_action_processing_speed(self):
        """Test that actions process within target time."""
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        engine = GameEngine(game)
        engine.start_game()

        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = "player_0"

        import time
        start_time = time.time()

        engine.nominate_chancellor("player_0", "player_1")

        processing_time = time.time() - start_time
        assert processing_time < 0.1  # Should be much faster than 100ms

    def test_large_game_state_serialization(self):
        """Test serialization performance."""
        game = Game.create_new_game([f"Player{i}" for i in range(10)])
        engine = GameEngine(game)

        import time
        start_time = time.time()

        # Serialize game state multiple times
        for _ in range(100):
            game.model_dump()

        total_time = time.time() - start_time
        assert total_time < 0.05  # Should be much faster than 50ms