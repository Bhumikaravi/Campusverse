"""AI Scanning Booth Router.
Provides endpoints for:
- POST /api/scanning-booth/scan : Upload file, validate 150-page limit, extract text, run AI inspection, generate calibrated confidence score and 15-20 word summary.
- POST /api/scanning-booth/apply-corrections : Apply user-accepted corrections and generate a corrected file without overwriting original.
- POST /api/scanning-booth/approve-and-publish : Move scanned material into official study material library with auto-approval check.
- GET  /api/scanning-booth/benchmarks/latest : Retrieve latest empirical benchmark evaluation metrics.
- POST /api/scanning-booth/benchmarks/run : Execute benchmark evaluation across labeled dataset and store run.
- GET  /api/scanning-booth/settings : Get configurable settings (maxPages, confidence thresholds).
- POST /api/scanning-booth/settings : Update configurable settings.
"""

import os
import secrets
from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request, status
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_optional_user, get_current_user, require_role
from app.services.file_security import validate_and_scan_file, sanitize_filename, sha256_hash
from app.services.text_extract import extract_document_text, get_document_page_count
from app.services.scanning_booth import run_scanning_booth_analysis, apply_selected_corrections, deterministic_scan
from app.services.document_evaluation import (
    detect_document_title,
    generate_concise_summary,
    calculate_calibrated_confidence,
    run_benchmark_evaluation
)
from app.storage.factory import get_storage
from app.models.material import MATERIAL_STATUS

router = APIRouter(prefix="/api/scanning-booth", tags=["AI Scanning Booth"])

admin_guard = require_role("moderator", "admin")

class ApplyCorrectionsRequest(BaseModel):
    scanId: str
    acceptedIssues: List[dict]

class ApproveAndPublishRequest(BaseModel):
    scanId: str
    mainCategory: str = "Engineering"
    subcategory: Optional[str] = None
    topic: Optional[str] = None
    subject: str
    semester: int = 1
    category: str = "notes"
    description: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    maxPages: Optional[int] = Field(None, ge=1, le=500)
    confidenceHighThreshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    confidenceMediumThreshold: Optional[float] = Field(None, ge=0.1, le=1.0)

async def get_system_settings(db: AsyncIOMotorDatabase) -> dict:
    """Retrieves dynamic scanning booth settings from database with config.py fallbacks."""
    record = await db["system_settings"].find_one({"key": "scanning_booth"})
    if not record:
        return {
            "maxPages": settings.MAX_DOCUMENT_PAGES,
            "confidenceHighThreshold": settings.CONFIDENCE_HIGH_THRESHOLD,
            "confidenceMediumThreshold": settings.CONFIDENCE_MEDIUM_THRESHOLD
        }
    return {
        "maxPages": record.get("maxPages", settings.MAX_DOCUMENT_PAGES),
        "confidenceHighThreshold": record.get("confidenceHighThreshold", settings.CONFIDENCE_HIGH_THRESHOLD),
        "confidenceMediumThreshold": record.get("confidenceMediumThreshold", settings.CONFIDENCE_MEDIUM_THRESHOLD)
    }

@router.post("/scan")
async def scan_material(
    file: UploadFile = File(...),
    mainCategory: Optional[str] = Form("Engineering"),
    subcategory: Optional[str] = Form(None),
    subject: Optional[str] = Form(""),
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Please upload a study document to scan.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    orig_name = sanitize_filename(file.filename)
    ext, mime, kind = validate_and_scan_file(file_bytes, orig_name)

    # 1. ENFORCE STRICT 150-PAGE UPLOAD LIMIT BEFORE OCR OR AI PROCESSING
    current_cfg = await get_system_settings(db)
    max_allowed_pages = current_cfg.get("maxPages", settings.MAX_DOCUMENT_PAGES)
    
    try:
        page_count = get_document_page_count(file_bytes, ext)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document could not be read. Please upload a valid document."
        )

    if page_count > max_allowed_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload limit exceeded. Please upload a document containing no more than {max_allowed_pages} pages."
        )

    # 2. Extract text from supported formats or scanned images
    extracted_text = extract_document_text(file_bytes, ext)
    if not extracted_text.strip():
        extracted_text = f"Scanned file: {orig_name}. Visual diagrams or handwritten document content."

    # 3. Detect Title
    detected_title = detect_document_title(extracted_text, orig_name)

    # 4. Generate Strict 15-20 Word Academic Summary
    summary_data = generate_concise_summary(detected_title, extracted_text, mainCategory or "", subcategory or "")

    # 5. Run AI Scanning Booth Analysis
    report = await run_scanning_booth_analysis(extracted_text, mainCategory or "Engineering", subcategory)

    # 6. Compute Calibrated Confidence Score
    pred_info = report.get("predictedCategory", {})
    confidence_data = calculate_calibrated_confidence(
        text=extracted_text,
        selected_main=mainCategory or "",
        selected_sub=subcategory,
        predicted_main=pred_info.get("mainCategory", ""),
        predicted_sub=pred_info.get("subcategory", ""),
        category_score=4 if report.get("categoryMatch") else 1,
        detected_title=detected_title,
        issues_count=len(report.get("issues", [])),
        total_words=len(extracted_text.split()),
        high_threshold=current_cfg.get("confidenceHighThreshold", 0.80),
        medium_threshold=current_cfg.get("confidenceMediumThreshold", 0.50)
    )

    # Enrich report with new features
    report["pageCount"] = page_count
    report["maxAllowedPages"] = max_allowed_pages
    report["detectedTitle"] = detected_title
    report["conciseSummary"] = summary_data
    report["confidenceScore"] = confidence_data

    # Store file in storage
    storage = get_storage()
    uploader_id = current_user.get("id") if current_user else "booth-guest"
    storage_key = f"scanning-booth/{uploader_id}/{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}{ext}"
    await storage.upload(storage_key, file_bytes, mime)

    # Create scan record in DB
    scan_doc = {
        "fileName": orig_name,
        "extension": ext,
        "mimeType": mime,
        "size": len(file_bytes),
        "pageCount": page_count,
        "storageKey": storage_key,
        "extractedText": extracted_text[:15000],
        "detectedTitle": detected_title,
        "summary": summary_data["summary"],
        "userSelection": {
            "mainCategory": mainCategory,
            "subcategory": subcategory,
            "subject": subject
        },
        "report": report,
        "uploaderId": uploader_id,
        "createdAt": datetime.utcnow()
    }

    res = await db["scanning_booth_records"].insert_one(scan_doc)
    scan_id = str(res.inserted_id)

    return {
        "scanId": scan_id,
        "fileName": orig_name,
        "pageCount": page_count,
        "fileType": ext.upper().lstrip("."),
        "fileSize": f"{len(file_bytes)/1024:.1f} KB" if len(file_bytes) < 1024*1024 else f"{len(file_bytes)/(1024*1024):.1f} MB",
        "detectedTitle": detected_title,
        "conciseSummary": summary_data,
        "confidenceScore": confidence_data,
        "report": report
    }

@router.get("/settings")
async def get_booth_settings(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Public/student endpoint to view active upload limits and verification thresholds."""
    return await get_system_settings(db)

@router.post("/settings", dependencies=[Depends(admin_guard)])
async def update_booth_settings(
    payload: SettingsUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Admin endpoint to update max upload pages and confidence score thresholds."""
    update_data = {}
    if payload.maxPages is not None:
        update_data["maxPages"] = payload.maxPages
    if payload.confidenceHighThreshold is not None:
        update_data["confidenceHighThreshold"] = payload.confidenceHighThreshold
    if payload.confidenceMediumThreshold is not None:
        update_data["confidenceMediumThreshold"] = payload.confidenceMediumThreshold

    update_data["updatedAt"] = datetime.utcnow()

    await db["system_settings"].update_one(
        {"key": "scanning_booth"},
        {"$set": update_data},
        upsert=True
    )
    return {
        "message": "AI Scan Booth settings updated successfully.",
        "settings": await get_system_settings(db)
    }

@router.get("/benchmarks/latest")
async def get_latest_benchmark(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Retrieves latest empirical benchmark run, or executes initial baseline if none exists."""
    latest = await db["ai_benchmark_runs"].find_one(sort=[("timestamp", -1)])
    if not latest:
        # Run baseline suite automatically
        current_cfg = await get_system_settings(db)
        report = await run_benchmark_evaluation(
            run_scanning_booth_analysis,
            high_threshold=current_cfg["confidenceHighThreshold"],
            medium_threshold=current_cfg["confidenceMediumThreshold"],
            max_pages=current_cfg["maxPages"]
        )
        report["_id"] = str(ObjectId())
        await db["ai_benchmark_runs"].insert_one(report)
        return report

    latest["id"] = str(latest.get("_id", ""))
    latest.pop("_id", None)
    return latest

@router.post("/benchmarks/run", dependencies=[Depends(admin_guard)])
async def execute_benchmarks(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Admin-triggered benchmark evaluation across representative ground truth dataset."""
    current_cfg = await get_system_settings(db)
    report = await run_benchmark_evaluation(
        run_scanning_booth_analysis,
        high_threshold=current_cfg["confidenceHighThreshold"],
        medium_threshold=current_cfg["confidenceMediumThreshold"],
        max_pages=current_cfg["maxPages"]
    )
    ins = await db["ai_benchmark_runs"].insert_one(report)
    report["id"] = str(ins.inserted_id)
    report.pop("_id", None)
    return report

@router.get("/{scan_id}")
async def get_scan_report(scan_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(scan_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    record = await db["scanning_booth_records"].find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")

    return {
        "scanId": scan_id,
        "fileName": record.get("fileName"),
        "pageCount": record.get("pageCount", 1),
        "detectedTitle": record.get("detectedTitle"),
        "summary": record.get("summary"),
        "report": record.get("report"),
        "userSelection": record.get("userSelection")
    }

@router.post("/apply-corrections")
async def apply_corrections(
    payload: ApplyCorrectionsRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        oid = ObjectId(payload.scanId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    record = await db["scanning_booth_records"].find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")

    original_text = record.get("extractedText", "")
    corrected_text = apply_selected_corrections(original_text, payload.acceptedIssues)

    # Save corrected text file to storage
    storage = get_storage()
    corr_bytes = corrected_text.encode("utf-8")
    corr_key = f"corrected/{record.get('uploaderId', 'guest')}/{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}.txt"
    await storage.upload(corr_key, corr_bytes, "text/plain")

    await db["scanning_booth_records"].update_one(
        {"_id": oid},
        {"$set": {
            "correctedStorageKey": corr_key,
            "correctedText": corrected_text[:15000],
            "acceptedCorrectionsCount": len(payload.acceptedIssues),
            "updatedAt": datetime.utcnow()
        }}
    )

    return {
        "message": f"Successfully applied {len(payload.acceptedIssues)} corrections.",
        "correctedPreview": corrected_text[:2000],
        "correctionsApplied": len(payload.acceptedIssues)
    }

@router.post("/approve-and-publish")
async def approve_and_publish(
    payload: ApproveAndPublishRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        oid = ObjectId(payload.scanId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    record = await db["scanning_booth_records"].find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")

    report = record.get("report", {})
    quality_score = report.get("qualityScore", 70)
    has_critical_academic_issue = any(i.get("category") == "Academic Review" for i in report.get("issues", []))
    is_medical = (payload.mainCategory or "").lower() in ["general medicine", "medical", "medicine"] or report.get("isMedicalReviewRequired", False)
    
    # Confidence Score tier check
    conf_obj = report.get("confidenceScore", {})
    is_high_conf = (conf_obj.get("tier") == "HIGH")

    # Evaluate automated approval rules:
    # 1. Quality score >= 75 and High Confidence
    # 2. No critical factual contradiction
    # 3. Category match confirmed
    # 4. Mandatory Clinical Safety Rule: Medical materials must NEVER be auto-published without medical staff review
    is_auto_approved = (
        is_high_conf and
        quality_score >= 75 and
        not has_critical_academic_issue and
        report.get("categoryMatch", True) and
        not is_medical
    )

    initial_status = MATERIAL_STATUS.AI_APPROVED if is_auto_approved else MATERIAL_STATUS.NEEDS_REVIEW

    # Publish into materials collection
    file_bytes_size = record.get("size", 1024)
    file_hash = sha256_hash(record.get("extractedText", "").encode("utf-8"))

    # Strictly use 15-20 word summary
    detected_title = record.get("detectedTitle") or record.get("fileName").replace(record.get("extension", ""), "").replace("_", " ").title()
    summary_candidate = report.get("conciseSummary", {}).get("summary") or record.get("summary")
    if not summary_candidate or len(summary_candidate.split()) < 15 or len(summary_candidate.split()) > 20:
        summary_obj = generate_concise_summary(detected_title, record.get("extractedText", ""), payload.mainCategory, payload.subcategory or "")
        final_summary = summary_obj["summary"]
    else:
        final_summary = summary_candidate

    material_doc = {
        "title": detected_title,
        "description": final_summary,
        "summary": final_summary,
        "mainCategory": payload.mainCategory,
        "subcategory": payload.subcategory,
        "topic": payload.topic,
        "department": payload.subcategory or payload.mainCategory,
        "semester": payload.semester,
        "subject": payload.subject,
        "category": payload.category,
        "uploader": current_user["id"],
        "uploaderName": current_user.get("name", "Student"),
        "storageKey": record.get("storageKey"),
        "storageProvider": "local",
        "originalName": record.get("fileName"),
        "mimeType": record.get("mimeType"),
        "extension": record.get("extension"),
        "pageCount": record.get("pageCount", 1),
        "size": file_bytes_size,
        "fileHash": file_hash,
        "status": initial_status,
        "confidenceScore": conf_obj,
        "scanReport": report,
        "downloads": 0,
        "rating": 5.0,
        "ratingCount": 0,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }

    if record.get("correctedStorageKey"):
        material_doc["correctedStorageKey"] = record.get("correctedStorageKey")

    ins = await db["materials"].insert_one(material_doc)
    mat_id = str(ins.inserted_id)

    file_url = f"/api/materials/{mat_id}/file"
    await db["materials"].update_one({"_id": ins.inserted_id}, {"$set": {"fileUrl": file_url}})

    return {
        "materialId": mat_id,
        "status": initial_status,
        "isAutoApproved": is_auto_approved,
        "confidenceScore": conf_obj,
        "summary": final_summary,
        "message": "Material auto-approved and published live in study library!" if is_auto_approved else "Material submitted and queued for staff review."
    }

@router.get("/{scan_id}/download-original")
async def download_original(scan_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(scan_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    record = await db["scanning_booth_records"].find_one({"_id": oid})
    if not record or not record.get("storageKey"):
        raise HTTPException(status_code=404, detail="Original file not found")

    storage = get_storage()
    buffer = await storage.download(record["storageKey"])
    orig_name = record.get("fileName", "original_document")
    mime = record.get("mimeType", "application/octet-stream")

    return RawResponse(
        content=buffer,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{orig_name}"',
            "X-Content-Type-Options": "nosniff"
        }
    )

@router.get("/{scan_id}/download-corrected")
async def download_corrected(scan_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(scan_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan ID")

    record = await db["scanning_booth_records"].find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")

    corr_key = record.get("correctedStorageKey")
    storage = get_storage()

    if corr_key:
        buffer = await storage.download(corr_key)
    else:
        buffer = (record.get("extractedText") or "No text available").encode("utf-8")

    orig_name = record.get("fileName", "study_material")
    base_name = os.path.splitext(orig_name)[0]
    out_name = f"{base_name}_verified_corrected.txt"

    return RawResponse(
        content=buffer,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "X-Content-Type-Options": "nosniff"
        }
    )
