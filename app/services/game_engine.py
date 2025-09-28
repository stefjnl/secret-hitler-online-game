"""
Game Logic Engine for Secret Hitler Online.

This module implements the complete game orchestration system that manages
Secret Hitler gameplay sessions with strict rule enforcement and state machine transitions.

The GameEngine class serves as the central coordinator for all game actions,
ensuring proper phase transitions, rule enforcement, and state consistency.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import StrEnum
import logging
import asyncio

from app.models.game_models import (
    Game, GameState, Player, PolicyType, GamePhase,
    PresidentialPower, Party, Role
)
from app.services.ai_players import AIDecisionManager, AIPersonality


# Custom Exceptions for Game Engine
class GameEngineError(Exception):
    """Base exception for game engine errors."""
    pass


class InvalidActionError(GameEngineError):
    """Raised when an action is invalid in the current context."""
    pass


class WrongPhaseError(GameEngineError):
    """Raised when action is attempted in wrong game phase."""
    pass


class NotPlayerTurnError(GameEngineError):
    """Raised when wrong player attempts an action."""
    pass


class InvalidTargetError(GameEngineError):
    """Raised when target player is invalid for the action."""
    pass


class GameOverError(GameEngineError):
    """Raised when action is attempted after game is over."""
    pass


# Event System Types
class EventType(StrEnum):
    """Types of game events for real-time updates."""
    GAME_STARTED = "game_started"
    PHASE_CHANGED = "phase_changed"
    CHANCELLOR_NOMINATED = "chancellor_nominated"
    VOTE_SUBMITTED = "vote_submitted"
    ELECTION_RESULT = "election_result"
    POLICY_DRAWN = "policy_drawn"
    POLICY_DISCARDED = "policy_discarded"
    POLICY_ENACTED = "policy_enacted"
    PRESIDENTIAL_POWER_TRIGGERED = "presidential_power_triggered"
    PRESIDENTIAL_POWER_EXECUTED = "presidential_power_executed"
    PLAYER_ELIMINATED = "player_eliminated"
    GAME_OVER = "game_over"


class GameEngine:
    """
    Main orchestrator for Secret Hitler gameplay sessions.

    This class manages the complete game flow, enforces all Secret Hitler rules,
    and provides a clean interface for game actions. It implements a finite state
    machine that ensures proper phase transitions and maintains game state consistency.

    Attributes:
        game: The Game instance being managed
        logger: Logger for game events and debugging
        event_history: List of game events for debugging
    """

    def __init__(self, game: Game) -> None:
        """
        Initialize the game engine with a game instance.

        Args:
            game: The Game instance to manage

        Raises:
            ValueError: If game is None or invalid
        """
        if not game:
            raise ValueError("Game instance is required")

        self.game = game
        self.logger = logging.getLogger(__name__)
        self.event_history: List[Dict] = []
        self.ai_manager = AIDecisionManager(self)

        # Validate initial game state
        if game.game_state.phase != GamePhase.LOBBY:
            raise ValueError("Game must start in LOBBY phase")

        self.logger.info(f"GameEngine initialized for game {game.game_id}")

    def register_ai_players(self):
        """Registers all non-human players with the AI Decision Manager."""
        for player in self.game.players:
            if not player.is_human:
                # Assign a random personality for now
                personality = random.choice(list(AIPersonality))
                self.ai_manager.register_ai_player(player, personality)

    def start_game(self) -> GameState:
        """
        Start the game by transitioning from lobby to role reveal phase.

        Returns:
            The updated game state after starting

        Raises:
            GameEngineError: If game cannot be started
        """
        if self.game.game_state.phase != GamePhase.LOBBY:
            raise InvalidActionError("Game has already started")

        if len([p for p in self.game.players if p.is_alive]) < 5:
            raise InvalidActionError("Need at least 5 players to start")

        # Transition to role reveal phase
        self._transition_to_phase(GamePhase.ROLE_REVEAL)

        # Generate game started event
        self._generate_event(EventType.GAME_STARTED, {
            "player_count": len(self.game.players),
            "roles_distributed": True
        })

        self.logger.info(f"Game {self.game.game_id} started")
        return self.game.game_state

    def get_current_phase(self) -> GamePhase:
        """Get the current game phase."""
        return self.game.game_state.phase

    def get_available_actions(self, player_id: str) -> List[str]:
        """
        Get list of available actions for a specific player.

        Args:
            player_id: ID of the player to check

        Returns:
            List of available action names
        """
        if not self._is_valid_player(player_id):
            return []

        actions = []
        phase = self.game.game_state.phase

        if phase == GamePhase.LOBBY:
            if self._can_start_game(player_id):
                actions.append("start_game")

        elif phase == GamePhase.ELECTION:
            if self._is_president(player_id):
                actions.append("nominate_chancellor")
            else:
                actions.append("submit_vote")

        elif phase == GamePhase.LEGISLATIVE_SESSION:
            if self._is_president(player_id):
                actions.extend(["draw_policies", "discard_policy"])
            elif self._is_chancellor(player_id):
                actions.extend(["enact_policy", "request_veto"])

        elif phase == GamePhase.PRESIDENTIAL_POWER:
            if self._is_president(player_id):
                power = self.game.game_state.pending_presidential_power
                if power == PresidentialPower.INVESTIGATE_LOYALTY:
                    actions.append("investigate_loyalty")
                elif power == PresidentialPower.CALL_SPECIAL_ELECTION:
                    actions.append("call_special_election")
                elif power == PresidentialPower.POLICY_PEEK:
                    actions.append("policy_peek")
                elif power == PresidentialPower.EXECUTION:
                    actions.append("execute_player")

        return actions

    def is_player_turn(self, player_id: str) -> bool:
        """Check if it's a specific player's turn to act."""
        if not self._is_valid_player(player_id):
            return False

        phase = self.game.game_state.phase

        if phase == GamePhase.ELECTION:
            return self._is_president(player_id) or player_id not in self.game.game_state.votes

        elif phase == GamePhase.LEGISLATIVE_SESSION:
            return self._is_president(player_id) or self._is_chancellor(player_id)

        elif phase == GamePhase.PRESIDENTIAL_POWER:
            return self._is_president(player_id)

        return False

    def is_game_over(self) -> bool:
        """Check if the game has ended."""
        return self.game.game_state.phase == GamePhase.GAME_OVER

    def get_winner(self) -> Optional[Party]:
        """Get the winning party if game is over."""
        if not self.is_game_over():
            return None
        return self.game.check_win_condition()

    def nominate_chancellor(self, president_id: str, chancellor_id: str) -> Dict:
        """
        Nominate a chancellor for the current election.

        Args:
            president_id: ID of the president making the nomination
            chancellor_id: ID of the proposed chancellor

        Returns:
            Dictionary with result and game state

        Raises:
            GameEngineError: If nomination is invalid
        """
        self._validate_action(president_id, GamePhase.ELECTION)
        if not self._is_president(president_id):
            raise NotPlayerTurnError("Only president can nominate chancellor")

        if not self._validate_chancellor_nomination(president_id, chancellor_id):
            raise InvalidTargetError("Invalid chancellor nomination")

        # Set the nomination
        self.game.game_state.presidential_candidate_id = president_id
        self.game.game_state.chancellor_candidate_id = chancellor_id
        self.game.game_state.votes = {}

        self._generate_event(EventType.CHANCELLOR_NOMINATED, {
            "president_id": president_id,
            "chancellor_id": chancellor_id
        })

        self.logger.info(f"Chancellor nominated: {chancellor_id} by president {president_id}")
        return self._create_result("nomination_successful")

    def submit_vote(self, player_id: str, vote: bool) -> Dict:
        """
        Submit a vote for the current election.

        Args:
            player_id: ID of the voting player
            vote: True for yes, False for no

        Returns:
            Dictionary with result and game state

        Raises:
            GameEngineError: If vote is invalid
        """
        self._validate_action(player_id, GamePhase.ELECTION)

        if player_id in self.game.game_state.votes:
            raise InvalidActionError("Player has already voted")

        if self._is_president(player_id) or self._is_chancellor(player_id):
            raise InvalidActionError("President and chancellor cannot vote")

        # Record the vote
        self.game.game_state.votes[player_id] = vote

        self._generate_event(EventType.VOTE_SUBMITTED, {
            "player_id": player_id,
            "vote": vote
        })

        # Check if all votes are in
        alive_players = [p for p in self.game.players if p.is_alive]
        if len(self.game.game_state.votes) >= len(alive_players) - 2:  # All except president/chancellor
            return self.process_election_results()

        return self._create_result("vote_recorded")

    def process_election_results(self) -> Dict:
        """
        Process the current election results.

        Returns:
            Dictionary with election result and updated game state
        """
        success = self.game.process_votes()

        if success:
            result = self._form_government()
            self._generate_event(EventType.ELECTION_RESULT, {
                "successful": True,
                "president_id": self.game.game_state.presidential_candidate_id,
                "chancellor_id": self.game.game_state.chancellor_candidate_id
            })
        else:
            result = self._handle_election_failure()
            self._generate_event(EventType.ELECTION_RESULT, {
                "successful": False,
                "election_tracker": self.game.game_state.election_tracker
            })

        return result

    def draw_policies_for_president(self) -> List[PolicyType]:
        """
        Draw 3 policies for the president to choose from.

        Returns:
            List of 3 policy cards

        Raises:
            GameEngineError: If not in legislative session or wrong player
        """
        self._validate_action(
            self.game.game_state.presidential_candidate_id,
            GamePhase.LEGISLATIVE_SESSION
        )

        policies = self.game.draw_policies(3)

        self._generate_event(EventType.POLICY_DRAWN, {
            "president_id": self.game.game_state.presidential_candidate_id,
            "policy_count": len(policies)
        })

        return policies

    def president_discard_policy(self, policy: PolicyType) -> Dict:
        """
        President discards a policy card.

        Args:
            policy: The policy type to discard

        Returns:
            Dictionary with result and game state
        """
        president_id = self.game.game_state.presidential_candidate_id
        self._validate_action(president_id, GamePhase.LEGISLATIVE_SESSION)

        # Add to discard pile
        self.game.discard_pile.append(policy)

        self._generate_event(EventType.POLICY_DISCARDED, {
            "president_id": president_id,
            "policy": policy.value
        })

        return self._create_result("policy_discarded")

    def chancellor_enact_policy(self, policy: PolicyType) -> Dict:
        """
        Chancellor enacts a policy card.

        Args:
            policy: The policy type to enact

        Returns:
            Dictionary with result and game state
        """
        chancellor_id = self.game.game_state.chancellor_candidate_id
        self._validate_action(chancellor_id, GamePhase.LEGISLATIVE_SESSION)

        result = self._enact_policy(policy)

        self._generate_event(EventType.POLICY_ENACTED, {
            "chancellor_id": chancellor_id,
            "policy": policy.value
        })

        return result

    def execute_investigate_loyalty(self, target_id: str) -> Dict:
        """
        Execute investigate loyalty presidential power.

        Args:
            target_id: ID of player to investigate

        Returns:
            Dictionary with investigation result
        """
        self._validate_presidential_power_action(PresidentialPower.INVESTIGATE_LOYALTY)

        if not self._is_valid_target(target_id):
            raise InvalidTargetError("Invalid investigation target")

        target = next(p for p in self.game.players if p.id == target_id)
        self.game.game_state.investigated_players[target_id] = target.party
        target.investigated_by = self.game.game_state.presidential_candidate_id

        self._generate_event(EventType.PRESIDENTIAL_POWER_EXECUTED, {
            "power": PresidentialPower.INVESTIGATE_LOYALTY.value,
            "target_id": target_id,
            "revealed_party": target.party.value
        })

        self._clear_presidential_power()
        return self._create_result("investigation_complete", {
            "target_party": target.party.value
        })

    def execute_call_special_election(self, target_id: str) -> Dict:
        """
        Execute call special election presidential power.

        Args:
            target_id: ID of player to become next president

        Returns:
            Dictionary with special election result
        """
        self._validate_presidential_power_action(PresidentialPower.CALL_SPECIAL_ELECTION)

        if not self._is_valid_target(target_id):
            raise InvalidTargetError("Invalid special election target")

        # Set the special election target
        self.game.game_state.power_target_id = target_id

        self._generate_event(EventType.PRESIDENTIAL_POWER_EXECUTED, {
            "power": PresidentialPower.CALL_SPECIAL_ELECTION.value,
            "target_id": target_id
        })

        self._clear_presidential_power()
        return self._create_result("special_election_called", {
            "next_president_id": target_id
        })

    def execute_policy_peek(self) -> List[PolicyType]:
        """
        Execute policy peek presidential power.

        Returns:
            List of top 3 policies from the deck
        """
        self._validate_presidential_power_action(PresidentialPower.POLICY_PEEK)

        policies = self.game.draw_policies(3)

        self._generate_event(EventType.PRESIDENTIAL_POWER_EXECUTED, {
            "power": PresidentialPower.POLICY_PEEK.value,
            "policies": [p.value for p in policies]
        })

        # Put policies back (they were just peeked)
        for policy in reversed(policies):
            self.game.policy_deck.insert(0, policy)

        self._clear_presidential_power()
        return policies

    def execute_execution(self, target_id: str) -> Dict:
        """
        Execute execution presidential power.

        Args:
            target_id: ID of player to execute

        Returns:
            Dictionary with execution result
        """
        self._validate_presidential_power_action(PresidentialPower.EXECUTION)

        if not self._is_valid_target(target_id):
            raise InvalidTargetError("Invalid execution target")

        target = next(p for p in self.game.players if p.id == target_id)
        was_hitler = target.is_hitler()

        self.game.eliminate_player(target_id)

        self._generate_event(EventType.PRESIDENTIAL_POWER_EXECUTED, {
            "power": PresidentialPower.EXECUTION.value,
            "target_id": target_id,
            "was_hitler": was_hitler
        })

        self._clear_presidential_power()

        result_data = {"eliminated_player_id": target_id}
        if was_hitler:
            result_data["hitler_eliminated"] = True

        return self._create_result("execution_complete", result_data)

    # Private Helper Methods

    def _validate_action(self, player_id: str, expected_phase: GamePhase) -> None:
        """Validate that an action can be performed."""
        if self.is_game_over():
            raise GameOverError("Game is already over")

        if self.game.game_state.phase != expected_phase:
            raise WrongPhaseError(f"Expected {expected_phase.value}, got {self.game.game_state.phase.value}")

        if not self._is_valid_player(player_id):
            raise InvalidTargetError("Invalid player")

    def _validate_presidential_power_action(self, expected_power: PresidentialPower) -> None:
        """Validate presidential power execution."""
        president_id = self.game.game_state.presidential_candidate_id
        self._validate_action(president_id, GamePhase.PRESIDENTIAL_POWER)

        if self.game.game_state.pending_presidential_power != expected_power:
            raise InvalidActionError(f"Expected {expected_power.value} power")

    def _is_valid_player(self, player_id: str) -> bool:
        """Check if player ID is valid and player is alive."""
        return any(p.id == player_id and p.is_alive for p in self.game.players)

    def _is_valid_target(self, target_id: str) -> bool:
        """Check if target player is valid for actions."""
        return (self._is_valid_player(target_id) and
                target_id != self.game.game_state.presidential_candidate_id)

    def _is_president(self, player_id: str) -> bool:
        """Check if player is the current president."""
        return self.game.game_state.presidential_candidate_id == player_id

    def _is_chancellor(self, player_id: str) -> bool:
        """Check if player is the current chancellor."""
        return self.game.game_state.chancellor_candidate_id == player_id

    def _can_start_game(self, player_id: str) -> bool:
        """Check if player can start the game."""
        # For now, any player can start (could be restricted to host later)
        return self._is_valid_player(player_id)

    def _validate_chancellor_nomination(self, president_id: str, chancellor_id: str) -> bool:
        """Validate chancellor nomination according to game rules."""
        if president_id == chancellor_id:
            return False

        eligible = self.game.get_eligible_chancellors(president_id)
        return any(p.id == chancellor_id for p in eligible)

    def _transition_to_phase(self, new_phase: GamePhase) -> None:
        """Transition to a new game phase."""
        old_phase = self.game.game_state.phase
        self.game.game_state.phase = new_phase

        self._generate_event(EventType.PHASE_CHANGED, {
            "from_phase": old_phase.value,
            "to_phase": new_phase.value
        })

        self.logger.info(f"Phase transition: {old_phase.value} -> {new_phase.value}")

        # If the new phase requires an AI decision, request it.
        if new_phase == GamePhase.ELECTION:
            president_id = self.game.game_state.presidential_candidate_id
            if president_id in self.ai_manager.ai_players:
                asyncio.create_task(self.handle_ai_nomination(president_id))

    def _form_government(self) -> Dict:
        """Form a new government after successful election."""
        self._transition_to_phase(GamePhase.LEGISLATIVE_SESSION)

        # Check if presidential power should be triggered
        if self.game.game_state.fascist_policies >= 3:
            power = self.game.get_presidential_power()
            if power != PresidentialPower.NONE:
                self.game.game_state.pending_presidential_power = power
                # Stay in legislative session until power is executed
                # The power will be executed after policy enactment

        return self._create_result("government_formed")

    def _handle_election_failure(self) -> Dict:
        """Handle failed election (advance tracker or chaos)."""
        # Note: advance_election_tracker is already called by process_votes
        # so we don't need to call it again here

        # Check for chaos scenario (3 failed elections)
        if self.game.game_state.election_tracker >= 3:
            self._transition_to_phase(GamePhase.LEGISLATIVE_SESSION)
            return self._create_result("chaos_scenario")

        # Normal election failure - next president
        self._transition_to_phase(GamePhase.ELECTION)
        return self._create_result("election_failed")

    def _enact_policy(self, policy: PolicyType) -> Dict:
        """Enact a policy and handle game state changes."""
        if policy == PolicyType.LIBERAL:
            self.game.game_state.liberal_policies += 1
        else:
            self.game.game_state.fascist_policies += 1

        # Check for win condition
        winner = self.game.check_win_condition()
        if winner:
            self.game.game_state.phase = GamePhase.GAME_OVER
            self._generate_event(EventType.GAME_OVER, {"winner": winner.value})
            return self._create_result("policy_enacted", {"winner": winner.value})

        # Check if presidential power should be triggered
        if self.game.game_state.fascist_policies >= 3:
            power = self.game.get_presidential_power()
            if power != PresidentialPower.NONE:
                self.game.game_state.pending_presidential_power = power
                self._transition_to_phase(GamePhase.PRESIDENTIAL_POWER)
                return self._create_result("policy_enacted_power_triggered")

        # Normal transition back to election
        self._transition_to_phase(GamePhase.ELECTION)
        return self._create_result("policy_enacted")

    def _clear_presidential_power(self) -> None:
        """Clear the current presidential power."""
        self.game.game_state.pending_presidential_power = None
        self.game.game_state.power_target_id = None

    def _generate_event(self, event_type: EventType, data: Dict) -> None:
        """Generate and store a game event."""
        event = {
            "event_type": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "game_id": self.game.game_id,
            "data": data,
            "game_state": self.game.model_dump()
        }
        self.event_history.append(event)

    def _create_result(self, status: str, data: Optional[Dict] = None) -> Dict:
        """Create a standardized result dictionary."""
        return {
            "status": status,
            "game_state": self.game.game_state.model_dump(),
            "available_actions": {},  # Will be populated by caller if needed
            "data": data or {}
        }

    async def handle_ai_nomination(self, president_id: str):
        """Handles the chancellor nomination process for an AI president."""
        eligible_players = self.game.get_eligible_chancellors(president_id)
        options = {"eligible_players": eligible_players}
        chancellor_id = await self.ai_manager.request_ai_decision(
            president_id, "nominate_chancellor", options
        )
        self.nominate_chancellor(president_id, chancellor_id)

        # After nomination, all other AIs should vote.
        for player in self.game.players:
            if player.id in self.ai_manager.ai_players and player.id != president_id:
                asyncio.create_task(self.handle_ai_vote(player.id))

    async def handle_ai_vote(self, player_id: str):
        """Handles the voting process for an AI player."""
        president = next(p for p in self.game.players if p.id == self.game.game_state.presidential_candidate_id)
        chancellor = next(p for p in self.game.players if p.id == self.game.game_state.chancellor_candidate_id)
        options = {"president": president, "chancellor": chancellor}
        vote = await self.ai_manager.request_ai_decision(player_id, "vote", options)
        self.submit_vote(player_id, vote)