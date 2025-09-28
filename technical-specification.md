# US-003 Technical Specification: Game Logic Engine

## Class Architecture

### GameEngine Class
```python
class GameEngine:
    """Main orchestrator for Secret Hitler gameplay sessions."""

    def __init__(self, game: Game) -> None
    def start_game(self) -> GameState
    def get_current_phase(self) -> GamePhase
    def get_available_actions(self, player_id: str) -> List[str]
    def is_player_turn(self, player_id: str) -> bool
    def is_game_over(self) -> bool
    def get_winner(self) -> Optional[Party]
```

### Exception Classes
```python
class GameEngineError(Exception):
    """Base exception for game engine errors."""

class InvalidActionError(GameEngineError):
    """Raised when an action is invalid."""

class WrongPhaseError(GameEngineError):
    """Raised when action is attempted in wrong phase."""

class NotPlayerTurnError(GameEngineError):
    """Raised when wrong player attempts action."""

class InvalidTargetError(GameEngineError):
    """Raised when target player is invalid."""
```

## Method Specifications

### Phase Management Methods
```python
def _validate_phase_transition(self, from_phase: GamePhase, to_phase: GamePhase) -> bool
def _transition_to_phase(self, new_phase: GamePhase) -> Dict
def _check_phase_requirements(self, phase: GamePhase) -> bool
```

### Election Phase Methods
```python
def nominate_chancellor(self, president_id: str, chancellor_id: str) -> Dict
def submit_vote(self, player_id: str, vote: bool) -> Dict
def process_election_results(self) -> Dict
def _handle_election_failure(self) -> Dict
def _form_government(self) -> Dict
```

### Legislative Session Methods
```python
def draw_policies_for_president(self) -> List[PolicyType]
def president_discard_policy(self, policy: PolicyType) -> Dict
def chancellor_enact_policy(self, policy: PolicyType) -> Dict
def handle_veto_attempt(self, veto_requested: bool) -> Dict
def _enact_policy(self, policy: PolicyType) -> Dict
```

### Presidential Power Methods
```python
def execute_investigate_loyalty(self, target_id: str) -> Dict
def execute_call_special_election(self, target_id: str) -> Dict
def execute_policy_peek(self) -> List[PolicyType]
def execute_execution(self, target_id: str) -> Dict
def _trigger_presidential_power(self) -> Dict
```

## State Machine Implementation

### Phase Transition Rules
| From Phase | To Phase | Condition |
|------------|----------|-----------|
| Lobby | RoleReveal | Game starts |
| RoleReveal | Election | All roles revealed |
| Election | LegislativeSession | Government formed |
| Election | Election | Election failed |
| LegislativeSession | PresidentialPower | Fascist policy triggers power |
| LegislativeSession | Election | Session complete |
| PresidentialPower | Election | Power executed |
| Any Phase | GameOver | Win condition met |

### Turn Order Management
```python
def _get_next_president(self) -> Optional[Player]
def _get_player_order(self) -> List[Player]
def _skip_eliminated_players(self, players: List[Player]) -> List[Player]
```

## Event System Design

### Event Types
```python
EVENT_TYPES = {
    "game_started",
    "phase_changed",
    "chancellor_nominated",
    "vote_submitted",
    "election_result",
    "policy_drawn",
    "policy_discarded",
    "policy_enacted",
    "presidential_power_triggered",
    "presidential_power_executed",
    "player_eliminated",
    "game_over"
}
```

### Event Structure
```python
{
    "event_type": "phase_changed",
    "timestamp": "2024-01-01T12:00:00Z",
    "game_id": "game_123",
    "data": {
        "from_phase": "election",
        "to_phase": "legislative_session",
        "president_id": "player_1",
        "chancellor_id": "player_3"
    },
    "game_state": {...}  # Full game state snapshot
}
```

## Rule Enforcement Details

### Eligibility Validation
```python
def _validate_chancellor_nomination(self, president_id: str, chancellor_id: str) -> bool
def _check_term_limits(self, president_id: str, chancellor_id: str) -> bool
def _validate_hitler_chancellorship(self, chancellor_id: str) -> bool
```

### Veto Power Logic
```python
def _can_use_veto_power(self) -> bool
def _process_veto_attempt(self, president_veto: bool, chancellor_veto: bool) -> Dict
```

## Integration Points

### Model Integration
- **Game Class**: Use existing methods for state management
- **GameState**: Direct manipulation for phase and data updates
- **Player**: Status updates and role checking
- **Enums**: Full integration with existing type system

### External Integration
- **Event System**: Simple event generation for US-005
- **Logging**: Comprehensive game action logging
- **Error Handling**: Clear error messages for debugging

## Performance Considerations

### Optimization Targets
- Action processing: < 100ms
- Phase transitions: < 200ms
- State serialization: < 50ms
- Memory usage: Efficient state updates

### Implementation Strategies
- Immutable operations where possible
- Minimal state copying
- Efficient player lookups
- Cached eligibility calculations

This specification provides the foundation for implementing a robust, performant game engine that enforces all Secret Hitler rules while maintaining clean, testable code architecture.