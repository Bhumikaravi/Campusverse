import logging
from bson import ObjectId
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.middleware.auth import require_role
from app.services.quality_analyzer import analyze_document_quality
from app.services.text_extract import extract_document_complete
from app.storage.factory import get_storage
from app.config import settings

logger = logging.getLogger("campusverse.quality_router")
router = APIRouter(prefix="/api/admin/materials", tags=["Quality Analysis"])

admin_guard = require_role("moderator", "admin")

@router.get("/{material_id}/quality-report", dependencies=[Depends(admin_guard)])
async def get_document_quality_report(
    material_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Returns the comprehensive pre-approval quality report for admin review:
    - PDF readability & corruption
    - Blank page count and page numbers
    - Duplicate page count and page numbers
    - Subject relevance & confidence score
    - Completeness warnings
    - Overall quality status
    """
    mat_query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(mat_query)
    if not mat:
        raise HTTPException(status_code=404, detail="Study material not found.")

    if mat.get("qualityReport"):
        return {
            "materialId": str(mat["_id"]),
            "title": mat.get("title", ""),
            "qualityReport": mat["qualityReport"]
        }

    # Generate on demand if not yet computed
    try:
        storage = get_storage()
        file_bytes = await storage.download(mat["storageKey"])
        ext = mat.get("extension", ".pdf")
        extraction_res = extract_document_complete(
            buffer=file_bytes,
            ext=ext,
            max_pages=settings.MAX_DOCUMENT_PAGES,
            document_id=str(mat["_id"])
        )

        quality_report = analyze_document_quality(
            extraction_res=extraction_res,
            selected_subject=mat.get("subject", ""),
            selected_branch=mat.get("department", ""),
            predicted_subject=mat.get("classification", {}).get("subject", "") if mat.get("classification") else "",
            file_bytes=file_bytes,
            ext=ext
        )

        await db["materials"].update_one(mat_query, {"$set": {"qualityReport": quality_report}})

        return {
            "materialId": str(mat["_id"]),
            "title": mat.get("title", ""),
            "qualityReport": quality_report
        }
    except Exception as e:
        logger.error("Failed to generate quality report for %s: %s", material_id, e)
        raise HTTPException(status_code=500, detail=f"Quality analysis failed: {str(e)}")
