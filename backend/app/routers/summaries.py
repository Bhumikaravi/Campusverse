import logging
from typing import Optional
from bson import ObjectId
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.middleware.auth import get_optional_user, get_current_user, is_staff
from app.services.chapter_summarizer import generate_document_chapter_summaries
from app.services.text_extract import extract_document_pages
from app.storage.factory import get_storage
from app.config import settings

logger = logging.getLogger("campusverse.summaries_router")
router = APIRouter(prefix="/api/materials", tags=["Chapter Summaries"])

@router.get("/{material_id}/chapter-summaries")
async def get_chapter_summaries(
    material_id: str,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves chapter-wise summaries, key concepts, definitions, and formulas for a document.
    Generates and saves to the database if not already present.
    """
    mat_query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(mat_query)
    if not mat:
        raise HTTPException(status_code=404, detail="Study material not found.")

    is_owner = current_user and str(mat.get("uploader")) == str(current_user["id"])
    is_approved = mat.get("status") in ["ADMIN_APPROVED", "AI_APPROVED", "QUALITY_CHECK_PASSED"]
    if not (is_approved or is_owner or is_staff(current_user)):
        raise HTTPException(status_code=403, detail="Chapter summaries are only available for approved materials.")

    # 1. Check existing summary record in chapter_summaries collection
    existing = await db["chapter_summaries"].find_one({"materialId": str(mat["_id"])})
    if existing:
        existing["id"] = str(existing["_id"])
        existing.pop("_id", None)
        return existing

    # 2. If not generated yet, extract pages and generate now
    try:
        storage = get_storage()
        file_bytes = await storage.download(mat["storageKey"])
        ext = mat.get("extension", ".pdf")
        pages_text = extract_document_pages(file_bytes, ext, max_pages=settings.MAX_DOCUMENT_PAGES)
        
        summary_result = await generate_document_chapter_summaries(
            document_id=str(mat["_id"]),
            title=mat.get("title", "Study Material"),
            pages_text=pages_text,
            subject=mat.get("subject", "")
        )

        doc_to_save = {
            "materialId": str(mat["_id"]),
            "title": mat.get("title", ""),
            "subject": mat.get("subject", ""),
            "totalChapters": summary_result["totalChapters"],
            "chapters": summary_result["chapters"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }

        ins = await db["chapter_summaries"].insert_one(doc_to_save)
        doc_to_save["id"] = str(ins.inserted_id)
        doc_to_save.pop("_id", None)

        await db["materials"].update_one(mat_query, {"$set": {"hasChapterSummaries": True}})

        return doc_to_save
    except Exception as e:
        logger.error("Could not generate chapter summaries for %s: %s", material_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to generate chapter summaries: {str(e)}")

@router.post("/{material_id}/chapter-summaries/regenerate")
async def regenerate_chapter_summaries(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Forces regeneration of chapter-wise summaries, key concepts, and formulas.
    Allowed for material owner or admin.
    """
    mat_query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(mat_query)
    if not mat:
        raise HTTPException(status_code=404, detail="Study material not found.")

    is_owner = str(mat.get("uploader")) == str(current_user["id"])
    if not (is_owner or is_staff(current_user)):
        raise HTTPException(status_code=403, detail="You do not have permission to regenerate summaries for this document.")

    storage = get_storage()
    file_bytes = await storage.download(mat["storageKey"])
    ext = mat.get("extension", ".pdf")
    pages_text = extract_document_pages(file_bytes, ext, max_pages=settings.MAX_DOCUMENT_PAGES)

    summary_result = await generate_document_chapter_summaries(
        document_id=str(mat["_id"]),
        title=mat.get("title", "Study Material"),
        pages_text=pages_text,
        subject=mat.get("subject", "")
    )

    update_fields = {
        "title": mat.get("title", ""),
        "subject": mat.get("subject", ""),
        "totalChapters": summary_result["totalChapters"],
        "chapters": summary_result["chapters"],
        "updatedAt": datetime.utcnow()
    }

    await db["chapter_summaries"].update_one(
        {"materialId": str(mat["_id"])},
        {"$set": update_fields},
        upsert=True
    )
    await db["materials"].update_one(mat_query, {"$set": {"hasChapterSummaries": True}})

    return {
        "message": "Chapter-wise summaries regenerated successfully.",
        "chapterSummaries": summary_result
    }
