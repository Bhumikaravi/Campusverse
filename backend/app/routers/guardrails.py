import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.guardrails import (
    evaluate_input_guardrails,
    evaluate_output_guardrails,
    telemetry
)

logger = logging.getLogger("campusverse.guardrails_router")
router = APIRouter(prefix="/api/guardrails", tags=["AI Safety & Guardrails"])

class ValidateTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    context: Optional[str] = None

@router.get("/status")
async def get_guardrails_status():
    """Returns the live status, active policies, and evaluation metrics of AI Guardrails."""
    return telemetry.get_summary()

@router.post("/validate")
async def validate_text_guardrail(payload: ValidateTextRequest):
    """
    Evaluates a user prompt or text sample through the multi-layer Guardrail engine.
    Used by interactive test consoles and moderation hooks.
    """
    eval_result = evaluate_input_guardrails(payload.text, payload.context)
    return eval_result

@router.get("/policies")
async def list_guardrail_policies():
    """Returns detailed descriptions and enforcement modes for all active guardrails."""
    summary = telemetry.get_summary()
    return {"policies": summary.get("activePolicies", [])}
