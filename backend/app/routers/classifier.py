import logging
import secrets
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.material import ClassificationCorrection
from app.middleware.auth import get_current_user, is_staff
from app.services.classifier import classify_document_content
from app.services.file_security import validate_and_scan_file, sanitize_filename
from app.services.text_extract import extract_document_complete
from app.config import settings

logger = logging.getLogger("campusverse.classifier_router")
router = APIRouter(prefix="/api/classifier", tags=["Classification"])

@router.post("/predict")
async def predict_classification(
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None)
):
    """
    Extracts text and predicts academic branch, subject, and topics.
    Displays confidence score and explanation.
    Returns 'Unable to classify' if insufficient information.
    """
    doc_text = ""
    filename = ""

    if file and file.filename:
        filename = sanitize_filename(file.filename)
        content_bytes = await file.read()
        if content_bytes:
            ext, _, _ = validate_and_scan_file(content_bytes, filename)
            res = extract_document_complete(content_bytes, ext, max_pages=settings.MAX_DOCUMENT_PAGES)
            doc_text = "\n\n".join(res.pages_text).strip()

    if not doc_text and text:
        doc_text = text.strip()

    if not doc_text:
        return {
            "branch": "Unable to classify",
            "subject": "Unable to classify",
            "topics": [],
            "confidence": 0.0,
            "method": "rule_based_taxonomy",
            "explanation": "No readable content provided to classify."
        }

    prediction = await classify_document_content(doc_text, title=title or "", filename=filename)
    return prediction

@router.patch("/materials/{material_id}/classification")
async def correct_material_classification(
    material_id: str,
    correction: ClassificationCorrection,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Allows the student who uploaded the notes, or an authorized admin,
    to correct the classification (branch, subject, topic).
    Saves the corrected classification into the existing database.
    """
    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(query)
    if not mat:
        raise HTTPException(status_code=404, detail="Study material not found.")

    is_owner = str(mat.get("uploader")) == str(current_user["id"])
    if not (is_owner or is_staff(current_user)):
        raise HTTPException(status_code=403, detail="You do not have permission to modify this document's classification.")

    updated_classification = mat.get("classification") or {}
    updated_classification.update({
        "branch": correction.branch.strip(),
        "subject": correction.subject.strip(),
        "corrected": True,
        "correctedBy": current_user["id"],
        "correctionReason": correction.reason or "Corrected by user",
        "confidence": 1.0,
        "method": "manual_correction"
    })

    if correction.topic:
        updated_classification["topics"] = [correction.topic.strip()]

    update_doc = {
        "department": correction.branch.strip(),
        "subject": correction.subject.strip(),
        "academicCategory": correction.branch.strip(),
        "mainCategory": correction.branch.strip(),
        "classification": updated_classification
    }
    if correction.topic:
        update_doc["topic"] = correction.topic.strip()

    await db["materials"].update_one(query, {"$set": update_doc})

    return {
        "message": "Classification updated successfully.",
        "classification": updated_classification
    }
