import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.middleware.auth import get_optional_user, is_staff
from app.services.embedding_service import search_semantic_chunks

logger = logging.getLogger("campusverse.search_router")
router = APIRouter(prefix="/api/search", tags=["Semantic Search"])

@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., min_length=2, description="Natural language question or search phrase"),
    limit: int = Query(10, ge=1, le=50),
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Semantic search over academic notes using natural language questions.
    Embeds query and retrieves matching document chunks using cosine similarity.
    Displays document title, page number, snippet, and score.
    Respects access permissions (only approved materials or owner's materials).
    """
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    user_id = current_user.get("id") if current_user else None
    user_is_staff = is_staff(current_user)

    results = await search_semantic_chunks(
        query_text=clean_q,
        user_id=user_id,
        is_admin=user_is_staff,
        limit=limit
    )

    return {
        "query": clean_q,
        "count": len(results),
        "results": results
    }
