# Secret Hitler Online - Game Engine Documentation

## Overview

The GameEngine class is the central orchestrator for Secret Hitler gameplay sessions. It manages the complete game flow, enforces all Secret Hitler rules, and provides a clean interface for game actions.

## Architecture

### Core Components

#### GameEngine Class
```python
from app.services.game_engine import GameEngine
from app.models.game_models import Game

# Initialize with a game instance
game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
engine = GameEngine(game)

# Start the game
engine.start_game()
```

#### Exception Handling
The engine uses specific exceptions for different error conditions:
- `InvalidActionError`: General invalid action
- `WrongPhaseError`: Action attempted in wrong phase
- `NotPlayerTurnError`: Wrong player attempting action
- `InvalidTargetError`: Invalid player target
- `GameOverError`: Action attempted after game end

## Game Flow

### Phase Transitions
The engine implements a finite state machine with the following phases:

1. **LOBBY**: Initial phase, players can start the game
2. **ROLE_REVEAL**: Roles are distributed to players
3. **ELECTION**: Presidential candidate nominates chancellor, voting occurs
4. **LEGISLATIVE_SESSION**: President draws policies, chancellor enacts one
5. **PRESIDENTIAL_POWER**: Execute unlocked presidential powers
6. **GAME_OVER**: Game ended, winner determined

### Example Game Flow

```python
from app.services.game_engine import GameEngine, EventType
from app.models.game_models import Game, GamePhase, PolicyType

# Create and start game
game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
engine = GameEngine(game)
engine.start_game()

# Election Phase
game.game_state.phase = GamePhase.ELECTION
game.game_state.presidential_candidate_id = "player_0"
game.game_state.chancellor_candidate_id = "player_1"

# President nominates chancellor
result = engine.nominate_chancellor("player_0", "player_1")
print(f"Nomination result: {result['status']}")

# Other players vote
engine.submit_vote("player_2", True)  # Yes vote
engine.submit_vote("player_3", True)  # Yes vote
engine.submit_vote("player_4", True)  # Yes vote

# Process election results
election_result = engine.process_election_results()
print(f"Election successful: {election_result['status']}")

# Legislative Session (if election successful)
if game.game_state.phase == GamePhase.LEGISLATIVE_SESSION:
    # President draws 3 policies
    policies = engine.draw_policies_for_president()
    print(f"President drew: {[p.value for p in policies]}")

    # President discards one policy
    engine.president_discard_policy(policies[0])

    # Chancellor enacts remaining policy
    remaining_policies = [p for p in policies if p != policies[0]]
    engine.chancellor_enact_policy(remaining_policies[0])

# Continue with next election...
```

## Presidential Powers

The engine handles all presidential powers with proper timing:

### Investigate Loyalty
```python
# Execute investigate loyalty power
result = engine.execute_investigate_loyalty("player_2")
print(f"Investigation result: {result['data']['target_party']}")
```

### Call Special Election
```python
# Call special election
result = engine.execute_call_special_election("player_3")
print(f"Next president: {result['data']['next_president_id']}")
```

### Policy Peek
```python
# Peek at top 3 policies
policies = engine.execute_policy_peek()
print(f"Top policies: {[p.value for p in policies]}")
```

### Execution
```python
# Execute a player
result = engine.execute_execution("player_4")
if result['data'].get('hitler_eliminated'):
    print("Hitler was executed!")
```

## Event System

The engine generates events for real-time updates:

```python
# Access event history
events = engine.event_history
for event in events:
    print(f"Event: {event['event_type']} at {event['timestamp']}")
    print(f"Data: {event['data']}")
```

### Event Types
- `GAME_STARTED`: Game initialization
- `PHASE_CHANGED`: Phase transitions
- `CHANCELLOR_NOMINATED`: Chancellor nomination
- `VOTE_SUBMITTED`: Vote cast
- `ELECTION_RESULT`: Election outcome
- `POLICY_ENACTED`: Policy enacted
- `PRESIDENTIAL_POWER_EXECUTED`: Power used
- `PLAYER_ELIMINATED`: Player removed
- `GAME_OVER`: Game ended

## Error Handling

```python
try:
    engine.nominate_chancellor("invalid_player", "player_1")
except NotPlayerTurnError as e:
    print(f"Error: {e}")

try:
    engine.chancellor_enact_policy(PolicyType.LIBERAL)
except WrongPhaseError as e:
    print(f"Wrong phase: {e}")
```

## Rule Enforcement

The engine automatically enforces all Secret Hitler rules:

- **Term Limits**: Same government can't serve consecutive terms
- **Eligibility**: Last president/chancellor can't be nominated
- **Hitler Chancellorship**: Blocked before 3 fascist policies, victory after
- **Veto Power**: Available only with 5+ fascist policies
- **Election Tracker**: Advances on failed elections, chaos at 3 failures
- **Win Conditions**: 5 liberal policies, 6 fascist policies, Hitler executed, Hitler chancellor

## Performance Characteristics

- **Action Processing**: < 100ms for simple actions
- **Phase Transitions**: < 200ms including validation
- **State Serialization**: < 50ms for full game state
- **Memory Management**: Efficient state updates, minimal copying

## Integration with Web API

The GameEngine integrates seamlessly with the web API for real-time gameplay:

```python
# In your FastAPI endpoint
@app.post("/game/{game_id}/nominate")
async def nominate_chancellor(game_id: str, nomination: NominationRequest):
    # Get game engine instance
    engine = get_game_engine(game_id)

    # Process action
    result = engine.nominate_chancellor(
        nomination.president_id,
        nomination.chancellor_id
    )

    # Broadcast result to all players via WebSocket
    await broadcast_game_event(game_id, result)

    return result
```

## Testing

The engine includes comprehensive tests covering:

- **Unit Tests**: Individual method functionality
- **Integration Tests**: Complete game scenarios
- **Edge Cases**: Error conditions and boundary states
- **Performance Tests**: Speed and memory benchmarks

```bash
# Run all game engine tests
pytest tests/test_game_engine.py -v

# Run specific test categories
pytest tests/test_game_engine.py::TestGameScenarios -v
pytest tests/test_game_engine.py::TestPerformance -v
```

## Best Practices

### Game State Management
- Always validate actions before execution
- Use the event system for state synchronization
- Handle errors gracefully with appropriate user feedback

### Performance Optimization
- Cache frequently accessed game state
- Minimize state serialization for real-time updates
- Use efficient data structures for player lookups

### Error Handling
- Catch specific exceptions rather than generic ones
- Provide meaningful error messages for users
- Log errors for debugging while maintaining user experience

This GameEngine provides a robust, reliable foundation for the complete Secret Hitler Online experience with proper rule enforcement and state management.