"""
Pydantic models for Secret Hitler Online API contracts.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class GamePhase(str, Enum):
    LOBBY = "lobby"
    ROLE_REVEAL = "role_reveal"
    ELECTION = "election"
    LEGISLATIVE_SESSION = "legislative_session"
    PRESIDENTIAL_POWER = "presidential_power"
    GAME_OVER = "game_over"


class PolicyType(str, Enum):
    LIBERAL = "liberal"
    FASCIST = "fascist"


class PlayerRole(str, Enum):
    LIBERAL = "liberal"
    FASCIST = "fascist"
    HITLER = "hitler"


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# Request Models
class CreateGameRequest(BaseModel):
    creator_name: str = Field(..., min_length=1, max_length=50, description="Name of the player creating the game")


class JoinGameRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=50, description="Name of the joining player")


class NominateChancellorRequest(BaseModel):
    chancellor_id: str = Field(..., description="ID of the nominated chancellor")


class VoteRequest(BaseModel):
    vote: bool = Field(..., description="True for Ja, False for Nein")


class DiscardPolicyRequest(BaseModel):
    policy: PolicyType = Field(..., description="Policy to discard")


class EnactPolicyRequest(BaseModel):
    policy: PolicyType = Field(..., description="Policy to enact")


class PresidentialPowerRequest(BaseModel):
    target_player_id: Optional[str] = Field(None, description="Target player ID for powers that require one")


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Chat message content")


# Response Models
class PlayerResponse(BaseModel):
    id: str
    name: str
    is_alive: bool
    role: Optional[PlayerRole] = None  # Only revealed when appropriate
    is_president: bool = False
    is_chancellor: bool = False
    is_connected: bool = True


class BoardStateResponse(BaseModel):
    liberal_policies: int
    fascist_policies: int
    election_tracker: int
    failed_elections: int
    veto_power_available: bool


class GameStateResponse(BaseModel):
    id: str
    status: GameStatus
    phase: GamePhase
    players: List[PlayerResponse]
    board: BoardStateResponse
    current_president: Optional[str] = None
    current_chancellor: Optional[str] = None
    winner: Optional[str] = None  # "liberals" or "fascists"


class GameHistoryEntry(BaseModel):
    timestamp: str
    event_type: str
    description: str
    data: Optional[Dict[str, Any]] = None


class AvailableActionsResponse(BaseModel):
    can_nominate_chancellor: bool = False
    can_vote: bool = False
    can_discard_policy: bool = False
    can_enact_policy: bool = False
    can_use_power: bool = False
    can_veto: bool = False
    eligible_chancellors: List[str] = []
    available_policies: List[PolicyType] = []
    presidential_power: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    player_id: str
    player_name: str
    message: str
    timestamp: str
    is_ai: bool = False


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None


# WebSocket Message Models
class WebSocketMessage(BaseModel):
    type: str
    game_id: str
    data: Dict[str, Any]
    timestamp: str


class GameUpdateMessage(WebSocketMessage):
    type: str = "game_update"
    game_state: GameStateResponse


class PlayerActionMessage(WebSocketMessage):
    type: str = "player_action"
    player_id: str
    action_type: str
    action_data: Dict[str, Any]


class ChatMessage(WebSocketMessage):
    type: str = "chat_message"
    chat_message: ChatMessageResponse


class ConnectionStatusMessage(WebSocketMessage):
    type: str = "connection_status"
    status: str  # "connected", "disconnected", "reconnecting"
    player_id: str