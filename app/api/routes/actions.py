"""
Player action routes for Secret Hitler Online.
Handles all game actions like nominations, votes, policy play, etc.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any
import logging

from ..models import (
    NominateChancellorRequest, VoteRequest, DiscardPolicyRequest,
    EnactPolicyRequest, PresidentialPowerRequest, ChatMessageRequest,
    APIResponse, ErrorResponse
)
from ...services.game_manager import GameManager
from ...services.ai_integration import AIIntegrationService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/{game_id}/nominate", response_model=APIResponse)
async def nominate_chancellor(
    game_id: str,
    request: NominateChancellorRequest,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Nominate a chancellor during election phase.

    - **game_id**: ID of the game
    - **chancellor_id**: ID of the nominated chancellor
    - **player_id**: ID of the nominating president (from auth)
    """
    try:
        result = await game_manager.nominate_chancellor(
            game_id, player_id, request.chancellor_id
        )

        # Process AI turns if needed
        await ai_integration.process_ai_turns(game_id)

        logger.info(f"Player {player_id} nominated {request.chancellor_id} in game {game_id}")

        return APIResponse(
            success=True,
            message="Chancellor nominated successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Invalid nomination",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to nominate chancellor in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to nominate chancellor",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/vote", response_model=APIResponse)
async def submit_vote(
    game_id: str,
    request: VoteRequest,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Submit a vote during election phase.

    - **game_id**: ID of the game
    - **vote**: True for Ja, False for Nein
    - **player_id**: ID of the voting player (from auth)
    """
    try:
        result = await game_manager.submit_vote(game_id, player_id, request.vote)

        # Process AI turns if needed
        await ai_integration.process_ai_turns(game_id)

        logger.info(f"Player {player_id} voted {'Ja' if request.vote else 'Nein'} in game {game_id}")

        return APIResponse(
            success=True,
            message="Vote submitted successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Invalid vote",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to submit vote in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to submit vote",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/discard", response_model=APIResponse)
async def discard_policy(
    game_id: str,
    request: DiscardPolicyRequest,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Discard a policy as president during legislative session.

    - **game_id**: ID of the game
    - **policy**: Policy to discard (liberal/fascist)
    - **player_id**: ID of the discarding president (from auth)
    """
    try:
        result = await game_manager.discard_policy(game_id, player_id, request.policy)

        # Process AI turns if needed
        await ai_integration.process_ai_turns(game_id)

        logger.info(f"President {player_id} discarded {request.policy.value} in game {game_id}")

        return APIResponse(
            success=True,
            message="Policy discarded successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Invalid discard",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to discard policy in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to discard policy",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/enact", response_model=APIResponse)
async def enact_policy(
    game_id: str,
    request: EnactPolicyRequest,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Enact a policy as chancellor during legislative session.

    - **game_id**: ID of the game
    - **policy**: Policy to enact (liberal/fascist)
    - **player_id**: ID of the enacting chancellor (from auth)
    """
    try:
        result = await game_manager.enact_policy(game_id, player_id, request.policy)

        # Process AI turns if needed
        await ai_integration.process_ai_turns(game_id)

        logger.info(f"Chancellor {player_id} enacted {request.policy.value} in game {game_id}")

        return APIResponse(
            success=True,
            message="Policy enacted successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Invalid enactment",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to enact policy in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to enact policy",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/power", response_model=APIResponse)
async def use_presidential_power(
    game_id: str,
    request: PresidentialPowerRequest,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Use a presidential power when available.

    - **game_id**: ID of the game
    - **target_player_id**: Target player for powers that require one
    - **player_id**: ID of the president using power (from auth)
    """
    try:
        result = await game_manager.use_presidential_power(
            game_id, player_id, request.target_player_id
        )

        # Process AI turns if needed
        await ai_integration.process_ai_turns(game_id)

        logger.info(f"President {player_id} used presidential power in game {game_id}")

        return APIResponse(
            success=True,
            message="Presidential power used successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Invalid presidential power",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to use presidential power in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to use presidential power",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/chat", response_model=APIResponse)
async def send_chat_message(
    game_id: str,
    request: ChatMessageRequest,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Send a chat message in the game.

    - **game_id**: ID of the game
    - **message**: Chat message content
    - **player_id**: ID of the sending player (from auth)
    """
    try:
        result = await game_manager.send_chat_message(game_id, player_id, request.message)

        # Process AI chat responses if needed
        await ai_integration.handle_ai_chat(game_id)

        logger.info(f"Player {player_id} sent chat message in game {game_id}")

        return APIResponse(
            success=True,
            message="Chat message sent successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Invalid chat message",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to send chat message in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to send chat message",
                details={"message": str(e)}
            ).model_dump()
        )