import logging
from bson import ObjectId
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.middleware.auth import require_role, get_current_user, is_staff
from app.services.embedding_service import check_document_similarity_and_plagiarism
from app.services.text_extract import extract_document_pages
from app.storage.factory import get_storage
from app.config import settings

logger = logging.getLogger("campusverse.similarity_router")
router = APIRouter(prefix="/api/similarity", tags=["Similarity & Plagiarism"])

admin_guard = require_role("moderator", "admin")

@router.get("/materials/{material_id}/report", dependencies=[Depends(admin_guard)])
async def get_similarity_report(
    material_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Fetches the similarity and potential plagiarism report for an uploaded document.
    Distinguishes exact duplicates, textual similarity, and semantic similarity.
    Provides admin review interface with page numbers and matching snippets.
    """
    mat_query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(mat_query)
    if not mat:
        raise HTTPException(status_code=404, detail="Study material not found.")

    if mat.get("similarityReport"):
        return {
            "materialId": str(mat["_id"]),
            "title": mat.get("title", ""),
            "report": mat["similarityReport"]
        }

    # Generate on demand if not present
    try:
        storage = get_storage()
        file_bytes = await storage.download(mat["storageKey"])
        ext = mat.get("extension", ".pdf")
        pages = extract_document_pages(file_bytes, ext, max_pages=settings.MAX_DOCUMENT_PAGES)
        
        report = await check_document_similarity_and_plagiarism(
            material_id=str(mat["_id"]),
            doc_pages_text=pages,
            current_file_hash=mat.get("fileHash", "")
        )

        await db["materials"].update_one(mat_query, {"$set": {"similarityReport": report}})

        return {
            "materialId": str(mat["_id"]),
            "title": mat.get("title", ""),
            "report": report
        }
    except Exception as e:
        logger.error("Error generating similarity report for %s: %s", material_id, e)
        raise HTTPException(status_code=500, detail=f"Similarity inspection failed: {str(e)}")

@router.post("/materials/{material_id}/check")
async def run_similarity_check(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Runs on-demand similarity check for a document."""
    mat_query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(mat_query)
    if not mat:
        raise HTTPException(status_code=404, detail="Study material not found.")

    is_owner = str(mat.get("uploader")) == str(current_user["id"])
    if not (is_owner or is_staff(current_user)):
        raise HTTPException(status_code=403, detail="Permission denied.")

    storage = get_storage()
    file_bytes = await storage.download(mat["storageKey"])
    ext = mat.get("extension", ".pdf")
    pages = extract_document_pages(file_bytes, ext, max_pages=settings.MAX_DOCUMENT_PAGES)

    report = await check_document_similarity_and_plagiarism(
        material_id=str(mat["_id"]),
        doc_pages_text=pages,
        current_file_hash=mat.get("fileHash", "")
    )

    await db["materials"].update_one(mat_query, {"$set": {"similarityReport": report}})

    return {
        "message": "Similarity check completed.",
        "report": report
    }
