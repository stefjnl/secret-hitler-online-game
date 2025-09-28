#!/usr/bin/env python3
"""
Example usage of the Secret Hitler GameEngine.

This script demonstrates how to use the GameEngine to orchestrate
a complete Secret Hitler game session.
"""

from app.models.game_models import Game, GamePhase, PolicyType
from app.services.game_engine import GameEngine


def main():
    """Demonstrate complete game flow."""
    print("Secret Hitler Online - Game Engine Demo")
    print("=" * 50)

    # Create a new game with 5 players
    player_names = ["Alice", "Bob", "Charlie", "Dave", "Eve"]
    print(f"Creating game with players: {', '.join(player_names)}")

    game = Game.create_new_game(player_names)
    engine = GameEngine(game)

    # Start the game
    print("\nStarting game...")
    result = engine.start_game()
    print(f"Game started! Current phase: {result.phase}")

    # Simulate a complete game (alternating liberal and fascist policies)
    print("\nSimulating complete game...")

    for round_num in range(1, 12):  # More rounds than needed to trigger win condition
        print(f"\n--- Round {round_num} ---")

        # Set up election
        game.game_state.phase = GamePhase.ELECTION
        game.game_state.presidential_candidate_id = f"player_{(round_num-1) % 5}"
        game.game_state.chancellor_candidate_id = f"player_{round_num % 5}"

        # Simulate votes (assume successful election)
        for i in range(5):
            if i not in [(round_num-1) % 5, round_num % 5]:  # Not president/chancellor
                game.game_state.votes[f"player_{i}"] = True

        # Process election
        election_result = engine.process_election_results()
        print(f"Election result: {election_result['status']}")

        if game.game_state.phase == GamePhase.LEGISLATIVE_SESSION:
            # Draw and enact policy
            policies = engine.draw_policies_for_president()
            print(f"Policies drawn: {[p.value for p in policies]}")

            # President discards one policy
            engine.president_discard_policy(policies[0])

            # Chancellor enacts the remaining policy
            remaining_policy = policies[1] if policies[1] != policies[0] else policies[2]
            policy_result = engine.chancellor_enact_policy(remaining_policy)
            print(f"Policy enacted: {remaining_policy.value}")

            # Check if game is over
            if engine.is_game_over():
                winner = engine.get_winner()
                print(f"GAME OVER! Winner: {winner.value}")
                break

        # Check for presidential powers
        if game.game_state.pending_presidential_power:
            print(f"Presidential power available: {game.game_state.pending_presidential_power.value}")

            # For demo, skip power execution to focus on policy enactment
            # In real game, would execute appropriate power here
            game.game_state.pending_presidential_power = None

    print("\nFinal Game State:")
    print(f"Policies enacted - Liberal: {game.game_state.liberal_policies}, Fascist: {game.game_state.fascist_policies}")
    print(f"Election tracker: {game.game_state.election_tracker}")
    print(f"Government history: {len(game.game_state.government_history)} governments formed")

    print("\nDemo completed!")


def demonstrate_error_handling():
    """Demonstrate error handling."""
    print("\nError Handling Demo")
    print("=" * 30)

    game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
    engine = GameEngine(game)

    try:
        # Try to nominate chancellor before game starts
        engine.nominate_chancellor("player_0", "player_1")
    except Exception as e:
        print(f"Expected error: {type(e).__name__}: {e}")

    try:
        # Try to start game with invalid player
        engine.start_game()
        engine.nominate_chancellor("invalid_player", "player_1")
    except Exception as e:
        print(f"Expected error: {type(e).__name__}: {e}")


def demonstrate_events():
    """Demonstrate event system."""
    print("\nEvent System Demo")
    print("=" * 25)

    game = Game.create_new_game(["Alice", "Bob", "Charlie", "Dave", "Eve"])
    engine = GameEngine(game)
    engine.start_game()

    print(f"Events generated: {len(engine.event_history)}")
    for event in engine.event_history:
        print(f"  - {event['event_type']}: {event['data']}")


if __name__ == "__main__":
    main()
    demonstrate_error_handling()
    demonstrate_events()