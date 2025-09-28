"""
Core game models and data structures for Secret Hitler Online.

This module defines the fundamental data structures that represent all game states,
player roles, and game mechanics for the Secret Hitler board game.

Model Relationships:
- Game: Main container holding all game state
  - Contains: List[Player], GameState, policy_deck, discard_pile
  - Manages: Role assignment, policy deck, win conditions
- GameState: Current game phase and mutable state
  - Tracks: Election progress, policy counts, government history
  - Manages: Presidential powers, investigations, eliminations
- Player: Individual player data
  - Properties: Role (Liberal/Fascist/Hitler), Party (computed), status
  - Relationships: Investigated by other players, alive/dead status

All models support JSON serialization for real-time game updates.
"""

from enum import StrEnum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, computed_field


class Role(StrEnum):
    """Player roles in Secret Hitler."""
    LIBERAL = "liberal"
    FASCIST = "fascist"
    HITLER = "hitler"


class Party(StrEnum):
    """Political parties in Secret Hitler."""
    LIBERAL = "liberal"
    FASCIST = "fascist"


class PolicyType(StrEnum):
    """Types of policies in Secret Hitler."""
    LIBERAL = "liberal"
    FASCIST = "fascist"


class GamePhase(StrEnum):
    """Phases of the game."""
    LOBBY = "lobby"
    ROLE_REVEAL = "role_reveal"
    ELECTION = "election"
    LEGISLATIVE_SESSION = "legislative_session"
    PRESIDENTIAL_POWER = "presidential_power"
    GAME_OVER = "game_over"


class PresidentialPower(StrEnum):
    """Presidential powers unlocked by fascist policies."""
    NONE = "none"
    INVESTIGATE_LOYALTY = "investigate_loyalty"
    CALL_SPECIAL_ELECTION = "call_special_election"
    POLICY_PEEK = "policy_peek"
    EXECUTION = "execution"


class Player(BaseModel):
    """
    Represents a player in the Secret Hitler game.

    Attributes:
        id: Unique identifier for the player.
        name: Display name of the player.
        role: The player's secret role (Liberal, Fascist, or Hitler).
        is_human: Whether this is a human player or AI.
        is_alive: Whether the player is still alive in the game.
        investigated_by: ID of the player who investigated this player (if any).
    """
    id: str
    name: str
    role: Role
    is_human: bool
    is_alive: bool = True
    investigated_by: Optional[str] = None

    @computed_field
    @property
    def party(self) -> Party:
        """The player's political party (derived from role)."""
        if self.role == Role.LIBERAL:
            return Party.LIBERAL
        else:  # Role.FASCIST or Role.HITLER
            return Party.FASCIST

    def is_fascist(self) -> bool:
        """Check if the player is on the fascist team."""
        return self.party == Party.FASCIST

    def is_hitler(self) -> bool:
        """Check if the player is Hitler."""
        return self.role == Role.HITLER


class GameState(BaseModel):
    """
    Represents the current state of the game.

    Attributes:
        phase: Current phase of the game.
        election_tracker: Number of failed elections (0-3).
        liberal_policies: Number of enacted liberal policies (0-5).
        fascist_policies: Number of enacted fascist policies (0-6).
        votes: Current election votes (player_id -> vote).
        government_history: List of (president_id, chancellor_id) tuples.
        presidential_candidate_id: ID of the current presidential candidate.
        chancellor_candidate_id: ID of the current chancellor candidate.
        last_president_id: ID of the last president.
        last_chancellor_id: ID of the last chancellor.
        pending_presidential_power: Current presidential power to execute.
        power_target_id: Target player ID for the current power.
        investigated_players: Map of player_id -> revealed party.
    """
    phase: GamePhase = GamePhase.LOBBY
    election_tracker: int = 0
    liberal_policies: int = 0
    fascist_policies: int = 0
    votes: Dict[str, bool] = {}
    government_history: List[Tuple[str, str]] = []
    presidential_candidate_id: Optional[str] = None
    chancellor_candidate_id: Optional[str] = None
    last_president_id: Optional[str] = None
    last_chancellor_id: Optional[str] = None
    pending_presidential_power: Optional[PresidentialPower] = None
    power_target_id: Optional[str] = None
    investigated_players: Dict[str, Party] = {}


class Game(BaseModel):
    """
    Main game object containing all game state and logic.

    Attributes:
        game_id: Unique identifier for the game.
        players: List of all players in the game.
        game_state: Current game state.
        policy_deck: Current policy deck (shuffled).
        discard_pile: Discarded policies.
    """
    game_id: str
    players: List[Player]
    game_state: GameState
    policy_deck: List[PolicyType]
    discard_pile: List[PolicyType]

    @classmethod
    def create_new_game(cls, player_names: List[str]) -> 'Game':
        """
        Create a new game with the given player names.

        Args:
            player_names: List of player names (5-10 players).

        Returns:
            A new Game instance with roles assigned and deck shuffled.
        """
        if not 5 <= len(player_names) <= 10:
            raise ValueError("Secret Hitler requires 5-10 players")

        game_id = "game_" + str(hash("".join(player_names)))  # Simple ID generation

        # Create players with IDs
        players = [
            Player(id=f"player_{i}", name=name, role=Role.LIBERAL, is_human=True)
            for i, name in enumerate(player_names)
        ]

        # Assign roles
        cls._assign_roles(players)

        # Initialize game state
        game_state = GameState()

        # Create and shuffle policy deck
        policy_deck = cls._create_policy_deck()

        return cls(
            game_id=game_id,
            players=players,
            game_state=game_state,
            policy_deck=policy_deck,
            discard_pile=[]
        )

    @staticmethod
    def _assign_roles(players: List[Player]) -> None:
        """Assign roles to players based on player count."""
        num_players = len(players)
        roles = []

        if num_players == 5:
            roles = [Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.FASCIST, Role.HITLER]
        elif num_players == 6:
            roles = [Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.FASCIST, Role.HITLER]
        elif num_players == 7:
            roles = [Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.FASCIST, Role.FASCIST, Role.HITLER]
        elif num_players == 8:
            roles = [Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.FASCIST, Role.FASCIST, Role.HITLER]
        elif num_players == 9:
            roles = [Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.FASCIST, Role.FASCIST, Role.FASCIST, Role.HITLER]
        elif num_players == 10:
            roles = [Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.LIBERAL, Role.FASCIST, Role.FASCIST, Role.FASCIST, Role.HITLER]

        # Shuffle roles and assign
        import random
        random.shuffle(roles)
        for player, role in zip(players, roles):
            player.role = role

    @staticmethod
    def _create_policy_deck() -> List[PolicyType]:
        """Create and shuffle the initial policy deck."""
        deck = ([PolicyType.LIBERAL] * 6) + ([PolicyType.FASCIST] * 11)
        import random
        random.shuffle(deck)
        return deck

    def draw_policies(self, count: int) -> List[PolicyType]:
        """
        Draw policies from the deck.

        Args:
            count: Number of policies to draw.

        Returns:
            List of drawn policies.
        """
        drawn = []
        for _ in range(count):
            if not self.policy_deck:
                # Reshuffle discard pile
                self.policy_deck = self.discard_pile.copy()
                self.discard_pile = []
                import random
                random.shuffle(self.policy_deck)
            drawn.append(self.policy_deck.pop())
        return drawn

    def get_eligible_chancellors(self, president_id: str) -> List[Player]:
        """
        Get players eligible to be chancellor for the given president.

        Args:
            president_id: ID of the presidential candidate.

        Returns:
            List of eligible players.
        """
        return [
            player for player in self.players
            if player.is_alive and player.id != president_id and
            player.id != self.game_state.last_president_id and
            player.id != self.game_state.last_chancellor_id
        ]

    def process_votes(self) -> bool:
        """
        Process the current election votes.

        Returns:
            True if the government is formed, False if election fails.
        """
        yes_votes = sum(1 for vote in self.game_state.votes.values() if vote)
        total_votes = len(self.game_state.votes)

        if yes_votes > total_votes / 2:
            # Government formed
            self.game_state.government_history.append((
                self.game_state.presidential_candidate_id,
                self.game_state.chancellor_candidate_id
            ))
            self.game_state.last_president_id = self.game_state.presidential_candidate_id
            self.game_state.last_chancellor_id = self.game_state.chancellor_candidate_id
            self.game_state.votes = {}
            return True
        else:
            # Election failed
            self.advance_election_tracker()
            self.game_state.votes = {}
            return False

    def advance_election_tracker(self) -> None:
        """Advance the election tracker and handle chaos if it reaches 3."""
        self.game_state.election_tracker += 1
        if self.game_state.election_tracker >= 3:
            # Chaos: enact top policy
            if self.policy_deck:
                policy = self.policy_deck.pop()
                if policy == PolicyType.LIBERAL:
                    self.game_state.liberal_policies += 1
                else:
                    self.game_state.fascist_policies += 1
                self.discard_pile.append(policy)
            self.game_state.election_tracker = 0

    def get_presidential_power(self) -> Optional[PresidentialPower]:
        """
        Determine the presidential power based on fascist policies and player count.

        Returns:
            The presidential power to execute, or None.
        """
        fascist_policies = self.game_state.fascist_policies
        num_players = len([p for p in self.players if p.is_alive])

        if num_players >= 9:
            if fascist_policies == 1:
                return PresidentialPower.INVESTIGATE_LOYALTY
            elif fascist_policies == 2:
                return PresidentialPower.CALL_SPECIAL_ELECTION
            elif fascist_policies == 3:
                return PresidentialPower.POLICY_PEEK
            elif fascist_policies >= 4:
                return PresidentialPower.EXECUTION
        else:  # 5-8 players
            if fascist_policies == 1:
                return PresidentialPower.NONE
            elif fascist_policies == 2:
                return PresidentialPower.INVESTIGATE_LOYALTY
            elif fascist_policies == 3:
                return PresidentialPower.CALL_SPECIAL_ELECTION
            elif fascist_policies >= 4:
                return PresidentialPower.EXECUTION

        return PresidentialPower.NONE

    def execute_presidential_power(self) -> None:
        """Execute the pending presidential power."""
        power = self.game_state.pending_presidential_power
        target_id = self.game_state.power_target_id

        if power == PresidentialPower.INVESTIGATE_LOYALTY and target_id:
            target = next((p for p in self.players if p.id == target_id), None)
            if target:
                self.game_state.investigated_players[target_id] = target.party
                target.investigated_by = self.game_state.last_president_id
        elif power == PresidentialPower.EXECUTION and target_id:
            self.eliminate_player(target_id)

        self.game_state.pending_presidential_power = None
        self.game_state.power_target_id = None

    def eliminate_player(self, player_id: str) -> None:
        """
        Eliminate a player from the game.

        Args:
            player_id: ID of the player to eliminate.
        """
        player = next((p for p in self.players if p.id == player_id), None)
        if player:
            player.is_alive = False
            # Check for win condition (Hitler executed)
            if player.is_hitler():
                self.game_state.phase = GamePhase.GAME_OVER

    def check_win_condition(self) -> Optional[Party]:
        """
        Check if the game has ended and return the winning party.

        Returns:
            The winning party, or None if the game continues.
        """
        if self.game_state.liberal_policies >= 5:
            return Party.LIBERAL
        if self.game_state.fascist_policies >= 6:
            return Party.FASCIST
        if any(not p.is_alive for p in self.players if p.is_hitler()):
            return Party.LIBERAL
        # Check if Hitler is chancellor after 3 fascist policies
        if self.game_state.fascist_policies >= 3:
            last_gov = self.game_state.government_history[-1] if self.game_state.government_history else None
            if last_gov:
                chancellor = next((p for p in self.players if p.id == last_gov[1]), None)
                if chancellor and chancellor.is_hitler():
                    return Party.FASCIST
        return None