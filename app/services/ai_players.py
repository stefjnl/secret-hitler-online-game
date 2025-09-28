"""
AI player system for Secret Hitler Online.

This module contains the core classes and logic for AI players, including their
decision-making processes, memory, and personalities.
"""

import random
from enum import StrEnum
from typing import Any, Dict, List, Optional

from app.models.game_models import Game, Player, PolicyType, Party, Role


class AIPersonality(StrEnum):
    """Defines the behavioral traits of an AI player."""
    CAUTIOUS_CONSERVATIVE = "cautious_conservative"
    BOLD_AGGRESSOR = "bold_aggressor"


class AIDifficulty(StrEnum):
    """Defines the difficulty level of an AI player."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class AIMemory:
    """Stores the AI's knowledge about the game."""
    def __init__(self):
        self.voting_history: Dict[str, List[bool]] = {}
        self.policy_claims: Dict[str, List[PolicyType]] = {}
        self.investigation_results: Dict[str, Party] = {}
        self.suspicious_behaviors: Dict[str, List[str]] = {}
        self.confirmed_roles: Dict[str, Role] = {}


class GameAnalysis:
    """Provides a comprehensive analysis of the game state."""
    def __init__(self, game: Game, player_perspective: Player):
        self.game = game
        self.player_perspective = player_perspective

    def calculate_suspicion_levels(self) -> Dict[str, float]:
        """Calculates suspicion levels for all players."""
        # Placeholder implementation
        return {player.id: 0.5 for player in self.game.players}

    def identify_likely_fascists(self) -> List[str]:
        """Identifies players who are likely to be fascists."""
        if self.player_perspective.party == Party.FASCIST:
            return [
                p.id for p in self.game.players
                if p.party == Party.FASCIST and p.id != self.player_perspective.id
            ]
        return []

    def assess_win_probability(self) -> Dict[Party, float]:
        """Assesses the win probability for each party."""
        # Placeholder implementation
        return {Party.LIBERAL: 0.5, Party.FASCIST: 0.5}

    def evaluate_policy_implications(self, policy: PolicyType) -> Dict:
        """Evaluates the implications of enacting a policy."""
        # Placeholder implementation
        return {}

    def analyze_voting_patterns(self) -> Dict[str, Dict]:
        """Analyzes the voting patterns of all players."""
        # Placeholder implementation
        return {}


class AIPlayer:
    """Base class for all AI players."""
    def __init__(self, player_id: str, personality: AIPersonality, difficulty: AIDifficulty = AIDifficulty.INTERMEDIATE):
        self.player_id = player_id
        self.personality = personality
        self.difficulty = difficulty
        self.memory = AIMemory()
        self.game: Optional[Game] = None
        self.player_perspective: Optional[Player] = None

    def analyze_game_state(self, game: Game) -> GameAnalysis:
        """Analyzes the current game state from the AI's perspective."""
        self.game = game
        self.player_perspective = next((p for p in game.players if p.id == self.player_id), None)
        if not self.player_perspective:
            raise ValueError(f"Player with id {self.player_id} not found in game.")
        return GameAnalysis(game, self.player_perspective)

    def make_decision(self, action_type: str, options: Dict) -> Any:
        """Makes a strategic decision based on the action type and options."""
        if self.difficulty == AIDifficulty.BEGINNER and random.random() < 0.2: # 20% chance of a random decision
            if action_type == "nominate_chancellor":
                return random.choice(options["eligible_players"]).id
            elif action_type == "vote":
                return random.choice([True, False])
            elif action_type == "discard_policy":
                return random.choice(options["policies"])
            elif action_type == "enact_policy":
                return random.choice(options["policies"])
            elif action_type in ["investigate_loyalty", "execute_player", "call_special_election"]:
                return random.choice(options["eligible_players"]).id

        if action_type == "nominate_chancellor":
            return self.decide_chancellor_nomination(options["eligible_players"])
        elif action_type == "vote":
            return self.decide_vote(options["president"], options["chancellor"])
        elif action_type == "discard_policy":
            return self.choose_policy_to_discard(options["policies"])
        elif action_type == "enact_policy":
            return self.choose_policy_to_enact(options["policies"])
        elif action_type == "investigate_loyalty":
            return self.choose_investigation_target(options["eligible_players"])
        elif action_type == "execute_player":
            return self.choose_execution_target(options["eligible_players"])
        elif action_type == "call_special_election":
            return self.choose_special_election_nominee(options["eligible_players"])
        # Add other action types here
        return None

    def decide_chancellor_nomination(self, eligible_players: List[Player]) -> str:
        """Decides who to nominate as chancellor."""
        analysis = self.analyze_game_state(self.game)
        my_role = self.player_perspective.role

        if my_role == Role.LIBERAL:
            # Liberal AI: Choose the player with the lowest suspicion level.
            suspicion_levels = analysis.calculate_suspicion_levels()
            return min(eligible_players, key=lambda p: suspicion_levels.get(p.id, 1.0)).id
        elif my_role == Role.FASCIST:
            # Fascist AI: Try to nominate another fascist, but not Hitler if it's too early.
            fellow_fascists = analysis.identify_likely_fascists()
            eligible_fascists = [p for p in eligible_players if p.id in fellow_fascists and not p.is_hitler()]
            if eligible_fascists:
                return random.choice(eligible_fascists).id
            # If no other fascists are eligible, nominate a liberal with high suspicion.
            suspicion_levels = analysis.calculate_suspicion_levels()
            return max(eligible_players, key=lambda p: suspicion_levels.get(p.id, 0.0)).id
        elif my_role == Role.HITLER:
            # Hitler AI: Act like a liberal. Nominate the least suspicious player.
            suspicion_levels = analysis.calculate_suspicion_levels()
            return min(eligible_players, key=lambda p: suspicion_levels.get(p.id, 1.0)).id

        # Default to random choice if logic fails
        return random.choice(eligible_players).id

    def decide_vote(self, president: Player, chancellor: Player) -> bool:
        """Decides whether to vote 'ja' or 'nein' on a government."""
        analysis = self.analyze_game_state(self.game)
        my_role = self.player_perspective.role
        suspicion_levels = analysis.calculate_suspicion_levels()

        # Basic suspicion check
        president_suspicion = suspicion_levels.get(president.id, 0.5)
        chancellor_suspicion = suspicion_levels.get(chancellor.id, 0.5)
        government_suspicion = (president_suspicion + chancellor_suspicion) / 2

        if my_role == Role.LIBERAL:
            # Liberals vote against suspicious governments.
            return government_suspicion < 0.6
        elif my_role == Role.FASCIST:
            # Fascists vote for their own, unless it exposes Hitler.
            fellow_fascists = analysis.identify_likely_fascists()
            if president.id in fellow_fascists or chancellor.id in fellow_fascists:
                if chancellor.is_hitler() and self.game.game_state.fascist_policies < 3:
                    return False  # Don't elect Hitler as chancellor too early
                return True
            return government_suspicion > 0.4 # Vote for suspicious governments
        elif my_role == Role.HITLER:
            # Hitler votes like a liberal to maintain cover.
            return government_suspicion < 0.6

        # Default to random vote if logic fails
        return random.choice([True, False])

    def choose_policy_to_discard(self, policies: List[PolicyType]) -> PolicyType:
        """Decides which policy to discard as president."""
        my_role = self.player_perspective.role
        if my_role == Role.LIBERAL:
            # Liberals always discard a fascist policy if they can.
            if PolicyType.FASCIST in policies:
                return PolicyType.FASCIST
        elif my_role in [Role.FASCIST, Role.HITLER]:
            # Fascists discard a liberal policy to advance their agenda.
            if PolicyType.LIBERAL in policies:
                return PolicyType.LIBERAL
        # Default to discarding the first policy.
        return policies[0]

    def choose_policy_to_enact(self, policies: List[PolicyType]) -> PolicyType:
        """Decides which policy to enact as chancellor."""
        # For now, enact the first policy given.
        # More complex logic will be added later (e.g., veto).
        return policies[0]

    def choose_investigation_target(self, eligible_players: List[Player]) -> str:
        """Decides which player to investigate."""
        analysis = self.analyze_game_state(self.game)
        my_role = self.player_perspective.role
        suspicion_levels = analysis.calculate_suspicion_levels()

        uninvestigated = [p for p in eligible_players if p.id not in self.game.game_state.investigated_players]
        if not uninvestigated:
            uninvestigated = eligible_players

        if my_role == Role.LIBERAL:
            # Investigate the most suspicious player.
            return max(uninvestigated, key=lambda p: suspicion_levels.get(p.id, 0.0)).id
        elif my_role in [Role.FASCIST, Role.HITLER]:
            # Investigate a known liberal to appear trustworthy.
            liberals = [p for p in uninvestigated if p.party == Party.LIBERAL]
            if liberals:
                return min(liberals, key=lambda p: suspicion_levels.get(p.id, 1.0)).id
        
        return random.choice(eligible_players).id

    def choose_execution_target(self, eligible_players: List[Player]) -> str:
        """Decides which player to execute."""
        analysis = self.analyze_game_state(self.game)
        my_role = self.player_perspective.role
        suspicion_levels = analysis.calculate_suspicion_levels()

        if my_role == Role.LIBERAL:
            # Execute the most suspicious player.
            return max(eligible_players, key=lambda p: suspicion_levels.get(p.id, 0.0)).id
        elif my_role in [Role.FASCIST, Role.HITLER]:
            # Execute a known liberal to remove a threat.
            liberals = [p for p in eligible_players if p.party == Party.LIBERAL]
            if liberals:
                return max(liberals, key=lambda p: suspicion_levels.get(p.id, 0.0)).id

        return random.choice(eligible_players).id

    def choose_special_election_nominee(self, eligible_players: List[Player]) -> str:
        """Decides who to nominate as president in a special election."""
        analysis = self.analyze_game_state(self.game)
        my_role = self.player_perspective.role
        suspicion_levels = analysis.calculate_suspicion_levels()

        if my_role == Role.LIBERAL:
            # Nominate the least suspicious player.
            return min(eligible_players, key=lambda p: suspicion_levels.get(p.id, 1.0)).id
        elif my_role in [Role.FASCIST, Role.HITLER]:
            # Nominate another fascist if possible.
            fascists = [p for p in eligible_players if p.party == Party.FASCIST]
            if fascists:
                return random.choice(fascists).id
        
        return random.choice(eligible_players).id

    def generate_chat_message(self, context: str) -> Optional[str]:
        """Generates a natural language chat message."""
        responses = {
            AIPersonality.CAUTIOUS_CONSERVATIVE: {
                "nomination_concern": "I'm not sure about this government...",
                "policy_suspicion": "That's a lot of fascist policies lately.",
                "investigation_request": "We should investigate {player}.",
            },
            AIPersonality.BOLD_AGGRESSOR: {
                "accusation": "{player} is definitely a fascist!",
                "demand_action": "We need to execute {player} NOW!",
                "confidence": "Trust me on this one.",
            },
        }

        if context in responses[self.personality]:
            return responses[self.personality][context]
        return None

    def update_memory(self, event: Dict) -> None:
        """Updates the AI's memory based on a game event."""
        # Placeholder implementation
        pass


class AIDecisionManager:
    """Manages all AI players and their interactions with the GameEngine."""
    def __init__(self, game_engine: Any):
        self.game_engine = game_engine
        self.ai_players: Dict[str, AIPlayer] = {}

    def register_ai_player(self, player: Player, personality: AIPersonality):
        """Creates and registers a new AI player."""
        self.ai_players[player.id] = AIPlayer(player.id, personality)

    async def request_ai_decision(self, player_id: str, action_type: str, options: Dict) -> Any:
        """Requests a decision from an AI player."""
        ai_player = self.ai_players.get(player_id)
        if not ai_player:
            return None

        # Simulate human-like response times
        import asyncio
        delay = random.uniform(2, 5)
        await asyncio.sleep(delay)

        return ai_player.make_decision(action_type, options)