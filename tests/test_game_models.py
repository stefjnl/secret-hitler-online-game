"""
Unit tests for the core game models in Secret Hitler Online.

This module tests all models, enums, and game logic to ensure correctness
and robustness of the data structures.
"""

import pytest
from app.models.game_models import (
    Role, Party, PolicyType, GamePhase, PresidentialPower,
    Player, GameState, Game
)


class TestEnums:
    """Test enum definitions and values."""

    def test_role_enum_values(self):
        assert Role.LIBERAL == "liberal"
        assert Role.FASCIST == "fascist"
        assert Role.HITLER == "hitler"

    def test_party_enum_values(self):
        assert Party.LIBERAL == "liberal"
        assert Party.FASCIST == "fascist"

    def test_policy_type_enum_values(self):
        assert PolicyType.LIBERAL == "liberal"
        assert PolicyType.FASCIST == "fascist"

    def test_game_phase_enum_values(self):
        assert GamePhase.LOBBY == "lobby"
        assert GamePhase.ROLE_REVEAL == "role_reveal"
        assert GamePhase.ELECTION == "election"
        assert GamePhase.LEGISLATIVE_SESSION == "legislative_session"
        assert GamePhase.PRESIDENTIAL_POWER == "presidential_power"
        assert GamePhase.GAME_OVER == "game_over"

    def test_presidential_power_enum_values(self):
        assert PresidentialPower.NONE == "none"
        assert PresidentialPower.INVESTIGATE_LOYALTY == "investigate_loyalty"
        assert PresidentialPower.CALL_SPECIAL_ELECTION == "call_special_election"
        assert PresidentialPower.POLICY_PEEK == "policy_peek"
        assert PresidentialPower.EXECUTION == "execution"


class TestPlayerModel:
    """Test Player model functionality."""

    def test_player_creation(self):
        player = Player(id="p1", name="Alice", role=Role.LIBERAL, is_human=True)
        assert player.id == "p1"
        assert player.name == "Alice"
        assert player.role == Role.LIBERAL
        assert player.party == Party.LIBERAL
        assert player.is_human is True
        assert player.is_alive is True
        assert player.investigated_by is None

    def test_party_derivation_from_role(self):
        liberal_player = Player(id="p1", name="Alice", role=Role.LIBERAL, is_human=True)
        fascist_player = Player(id="p2", name="Bob", role=Role.FASCIST, is_human=True)
        hitler_player = Player(id="p3", name="Charlie", role=Role.HITLER, is_human=True)

        assert liberal_player.party == Party.LIBERAL
        assert fascist_player.party == Party.FASCIST
        assert hitler_player.party == Party.FASCIST

    def test_is_fascist_method(self):
        liberal = Player(id="p1", name="Alice", role=Role.LIBERAL, is_human=True)
        fascist = Player(id="p2", name="Bob", role=Role.FASCIST, is_human=True)
        hitler = Player(id="p3", name="Charlie", role=Role.HITLER, is_human=True)

        assert not liberal.is_fascist()
        assert fascist.is_fascist()
        assert hitler.is_fascist()

    def test_is_hitler_method(self):
        liberal = Player(id="p1", name="Alice", role=Role.LIBERAL, is_human=True)
        fascist = Player(id="p2", name="Bob", role=Role.FASCIST, is_human=True)
        hitler = Player(id="p3", name="Charlie", role=Role.HITLER, is_human=True)

        assert not liberal.is_hitler()
        assert not fascist.is_hitler()
        assert hitler.is_hitler()

    def test_player_json_serialization(self):
        player = Player(id="p1", name="Alice", role=Role.LIBERAL, is_human=True)
        data = player.model_dump()
        assert data["role"] == "liberal"
        assert data["party"] == "liberal"


class TestGameStateModel:
    """Test GameState model functionality."""

    def test_game_state_creation(self):
        state = GameState()
        assert state.phase == GamePhase.LOBBY
        assert state.election_tracker == 0
        assert state.liberal_policies == 0
        assert state.fascist_policies == 0
        assert state.votes == {}
        assert state.government_history == []

    def test_game_state_json_serialization(self):
        state = GameState(phase=GamePhase.ELECTION, election_tracker=2)
        data = state.model_dump()
        assert data["phase"] == "election"
        assert data["election_tracker"] == 2


class TestGameModel:
    """Test Game model and game logic."""

    def test_create_new_game_invalid_player_count(self):
        with pytest.raises(ValueError, match="Secret Hitler requires 5-10 players"):
            Game.create_new_game(["Alice", "Bob"])  # 2 players

        with pytest.raises(ValueError, match="Secret Hitler requires 5-10 players"):
            Game.create_new_game([f"Player{i}" for i in range(11)])  # 11 players

    def test_create_new_game_5_players(self):
        players = ["Alice", "Bob", "Charlie", "Dave", "Eve"]
        game = Game.create_new_game(players)

        assert len(game.players) == 5
        assert len(game.policy_deck) == 17  # 6 liberal + 11 fascist
        assert len(game.discard_pile) == 0

        # Check role distribution for 5 players: 3 liberal, 1 fascist, 1 hitler
        roles = [p.role for p in game.players]
        assert roles.count(Role.LIBERAL) == 3
        assert roles.count(Role.FASCIST) == 1
        assert roles.count(Role.HITLER) == 1

    def test_create_new_game_8_players(self):
        players = [f"Player{i}" for i in range(8)]
        game = Game.create_new_game(players)

        # Check role distribution for 8 players: 5 liberal, 2 fascist, 1 hitler
        roles = [p.role for p in game.players]
        assert roles.count(Role.LIBERAL) == 5
        assert roles.count(Role.FASCIST) == 2
        assert roles.count(Role.HITLER) == 1

    def test_draw_policies(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        initial_deck_size = len(game.policy_deck)

        drawn = game.draw_policies(3)
        assert len(drawn) == 3
        assert len(game.policy_deck) == initial_deck_size - 3

    def test_draw_policies_reshuffle(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        # Simulate emptying the deck
        game.discard_pile = game.policy_deck.copy()
        game.policy_deck = []

        drawn = game.draw_policies(3)
        assert len(drawn) == 3
        assert len(game.policy_deck) == 17 - 3  # 17 cards reshuffled, 3 drawn
        assert len(game.discard_pile) == 0  # Discard pile emptied during reshuffle
        assert len(game.discard_pile) == 0

    def test_get_eligible_chancellors(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        president_id = game.players[0].id
        game.game_state.last_president_id = game.players[1].id
        game.game_state.last_chancellor_id = game.players[2].id

        eligible = game.get_eligible_chancellors(president_id)
        eligible_ids = {p.id for p in eligible}

        assert president_id not in eligible_ids
        assert game.players[1].id not in eligible_ids  # last president
        assert game.players[2].id not in eligible_ids  # last chancellor
        assert game.players[3].id in eligible_ids
        assert game.players[4].id in eligible_ids

    def test_process_votes_success(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        game.game_state.presidential_candidate_id = game.players[0].id
        game.game_state.chancellor_candidate_id = game.players[1].id
        game.game_state.votes = {
            game.players[0].id: True,
            game.players[1].id: True,
            game.players[2].id: True,
            game.players[3].id: False,
            game.players[4].id: False
        }

        success = game.process_votes()
        assert success is True
        assert len(game.game_state.government_history) == 1
        assert game.game_state.government_history[0] == (game.players[0].id, game.players[1].id)
        assert game.game_state.last_president_id == game.players[0].id
        assert game.game_state.last_chancellor_id == game.players[1].id
        assert game.game_state.votes == {}

    def test_process_votes_failure(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        game.game_state.votes = {
            game.players[0].id: False,
            game.players[1].id: False,
            game.players[2].id: False,
            game.players[3].id: True,
            game.players[4].id: True
        }

        success = game.process_votes()
        assert success is False
        assert game.game_state.election_tracker == 1
        assert game.game_state.votes == {}

    def test_advance_election_tracker_chaos(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        game.game_state.election_tracker = 2
        initial_liberal = game.game_state.liberal_policies
        initial_fascist = game.game_state.fascist_policies

        game.advance_election_tracker()

        # Should enact top policy and reset tracker
        assert game.game_state.election_tracker == 0
        enacted_policies = game.game_state.liberal_policies + game.game_state.fascist_policies
        initial_total = initial_liberal + initial_fascist
        assert enacted_policies == initial_total + 1

    def test_get_presidential_power_5_players(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])

        # 5 players: powers at 2, 3, 4+ fascist policies
        game.game_state.fascist_policies = 1
        assert game.get_presidential_power() == PresidentialPower.NONE

        game.game_state.fascist_policies = 2
        assert game.get_presidential_power() == PresidentialPower.INVESTIGATE_LOYALTY

        game.game_state.fascist_policies = 3
        assert game.get_presidential_power() == PresidentialPower.CALL_SPECIAL_ELECTION

        game.game_state.fascist_policies = 4
        assert game.get_presidential_power() == PresidentialPower.EXECUTION

    def test_get_presidential_power_9_players(self):
        players = [f"Player{i}" for i in range(9)]
        game = Game.create_new_game(players)

        # 9+ players: powers at 1, 2, 3, 4+ fascist policies
        game.game_state.fascist_policies = 1
        assert game.get_presidential_power() == PresidentialPower.INVESTIGATE_LOYALTY

        game.game_state.fascist_policies = 2
        assert game.get_presidential_power() == PresidentialPower.CALL_SPECIAL_ELECTION

        game.game_state.fascist_policies = 3
        assert game.get_presidential_power() == PresidentialPower.POLICY_PEEK

        game.game_state.fascist_policies = 4
        assert game.get_presidential_power() == PresidentialPower.EXECUTION

    def test_execute_investigate_loyalty(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        investigator = game.players[0]
        target = game.players[1]

        game.game_state.last_president_id = investigator.id
        game.game_state.pending_presidential_power = PresidentialPower.INVESTIGATE_LOYALTY
        game.game_state.power_target_id = target.id

        game.execute_presidential_power()

        assert target.id in game.game_state.investigated_players
        assert game.game_state.investigated_players[target.id] == target.party
        assert target.investigated_by == investigator.id
        assert game.game_state.pending_presidential_power is None
        assert game.game_state.power_target_id is None

    def test_execute_execution(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        target = game.players[1]

        game.game_state.pending_presidential_power = PresidentialPower.EXECUTION
        game.game_state.power_target_id = target.id

        game.execute_presidential_power()

        assert not target.is_alive
        assert game.game_state.pending_presidential_power is None
        assert game.game_state.power_target_id is None

    def test_eliminate_hitler(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        hitler = next(p for p in game.players if p.is_hitler())

        game.eliminate_player(hitler.id)

        assert not hitler.is_alive
        assert game.game_state.phase == GamePhase.GAME_OVER

    def test_check_win_condition_liberal_policies(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        game.game_state.liberal_policies = 5

        winner = game.check_win_condition()
        assert winner == Party.LIBERAL

    def test_check_win_condition_fascist_policies(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        game.game_state.fascist_policies = 6

        winner = game.check_win_condition()
        assert winner == Party.FASCIST

    def test_check_win_condition_hitler_executed(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        hitler = next(p for p in game.players if p.is_hitler())
        hitler.is_alive = False

        winner = game.check_win_condition()
        assert winner == Party.LIBERAL

    def test_check_win_condition_hitler_chancellor(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        hitler = next(p for p in game.players if p.is_hitler())
        game.game_state.fascist_policies = 3
        game.game_state.government_history = [("p1", hitler.id)]

        winner = game.check_win_condition()
        assert winner == Party.FASCIST

    def test_check_win_condition_no_winner(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])

        winner = game.check_win_condition()
        assert winner is None

    def test_game_json_serialization(self):
        game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
        data = game.model_dump()

        # Check that enums are serialized as strings
        assert isinstance(data["players"][0]["role"], str)
        assert isinstance(data["game_state"]["phase"], str)
        assert isinstance(data["policy_deck"][0], str)

        # Check that we can deserialize back
        restored_game = Game.model_validate(data)
        assert len(restored_game.players) == 5
        assert restored_game.game_state.phase == GamePhase.LOBBY