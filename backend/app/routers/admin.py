from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.material import MATERIAL_STATUS
from app.middleware.auth import require_role, get_current_user
from app.routers.materials import serialize_material
from app.config import settings
from app.services.document_evaluation import run_benchmark_evaluation
from app.services.scanning_booth import run_scanning_booth_analysis

router = APIRouter(prefix="/api/admin", tags=["Admin & Moderation"])

# Guard all admin routes to moderator or admin
admin_guard = require_role("moderator", "admin")

@router.get("/materials/pending", dependencies=[Depends(admin_guard)])
async def get_pending_materials(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    query = {"status": {"$in": [MATERIAL_STATUS.PENDING, MATERIAL_STATUS.AI_APPROVED, MATERIAL_STATUS.NEEDS_REVIEW]}}
    cursor = db["materials"].find(query).sort([("createdAt", 1)]).skip((page - 1) * limit).limit(limit)
    items = await cursor.to_list(length=limit)
    total = await db["materials"].count_documents(query)
    
    serialized = [serialize_material(m) for m in items]
    return {
        "items": serialized,
        "materials": serialized,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/materials/flagged", dependencies=[Depends(admin_guard)])
async def get_flagged_materials(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    query = {
        "status": {"$nin": [MATERIAL_STATUS.ADMIN_APPROVED, MATERIAL_STATUS.ADMIN_REJECTED]},
        "$or": [
            {"status": {"$in": [MATERIAL_STATUS.NEEDS_REVIEW, MATERIAL_STATUS.REJECTED]}},
            {"aiReview.flags.0": {"$exists": True}},
            {"duplicateOf": {"$ne": None}}
        ]
    }
    cursor = db["materials"].find(query).sort([("createdAt", -1)]).skip((page - 1) * limit).limit(limit)
    items = await cursor.to_list(length=limit)
    total = await db["materials"].count_documents(query)

    serialized = [serialize_material(m) for m in items]
    return {
        "items": serialized,
        "materials": serialized,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/materials", dependencies=[Depends(admin_guard)])
async def get_all_materials(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    filters = []
    if status:
        filters.append({"status": status.strip()})
    if department:
        filters.append({"department": {"$regex": f"^{department.strip()}$", "$options": "i"}})
    if semester:
        filters.append({"semester": semester})
    if subject:
        filters.append({"subject": {"$regex": f"^{subject.strip()}$", "$options": "i"}})
    if q:
        re_q = {"$regex": q.strip(), "$options": "i"}
        filters.append({"$or": [{"title": re_q}, {"description": re_q}, {"subject": re_q}]})

    query = {"$and": filters} if filters else {}
    cursor = db["materials"].find(query).sort([("createdAt", -1)]).skip((page - 1) * limit).limit(limit)
    items = await cursor.to_list(length=limit)
    total = await db["materials"].count_documents(query)

    serialized = [serialize_material(m) for m in items]
    return {
        "items": serialized,
        "materials": serialized,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/materials/{material_id}", dependencies=[Depends(admin_guard)])
async def get_admin_material_detail(
    material_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(query)
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found.")
    return {"material": serialize_material(mat)}

@router.patch("/materials/{material_id}/approve")
async def approve_material(
    material_id: str,
    request: Request,
    current_user: dict = Depends(admin_guard),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    note = body.get("note", "Approved by moderator.")
    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}

    update = {
        "status": MATERIAL_STATUS.ADMIN_APPROVED,
        "moderation": {
            "decision": "APPROVED",
            "reason": note,
            "reviewedBy": current_user["id"],
            "moderatorName": current_user.get("name", "Staff"),
            "reviewedAt": datetime.utcnow()
        },
        "updatedAt": datetime.utcnow()
    }

    result = await db["materials"].find_one_and_update(query, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Material not found.")

    return {
        "message": "Material approved and published live.",
        "material": serialize_material(result)
    }

@router.patch("/materials/{material_id}/reject")
async def reject_material(
    material_id: str,
    request: Request,
    current_user: dict = Depends(admin_guard),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    body = await request.json()
    reason = body.get("reason", "").strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rejection reason is mandatory."
        )

    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    update = {
        "status": MATERIAL_STATUS.ADMIN_REJECTED,
        "moderation": {
            "decision": "REJECTED",
            "reason": reason,
            "reviewedBy": current_user["id"],
            "moderatorName": current_user.get("name", "Staff"),
            "reviewedAt": datetime.utcnow()
        },
        "updatedAt": datetime.utcnow()
    }

    result = await db["materials"].find_one_and_update(query, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Material not found.")

    return {
        "message": "Material has been rejected.",
        "material": serialize_material(result)
    }

@router.get("/stats", dependencies=[Depends(admin_guard)])
async def get_admin_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    total_materials = await db["materials"].count_documents({})
    ai_approved = await db["materials"].count_documents({"status": MATERIAL_STATUS.AI_APPROVED})
    needs_review = await db["materials"].count_documents({"status": MATERIAL_STATUS.NEEDS_REVIEW})
    rejected = await db["materials"].count_documents({"status": {"$in": [MATERIAL_STATUS.REJECTED, MATERIAL_STATUS.ADMIN_REJECTED]}})
    admin_approved = await db["materials"].count_documents({"status": MATERIAL_STATUS.ADMIN_APPROVED})
    pending = await db["materials"].count_documents({
        "status": {"$in": [MATERIAL_STATUS.PENDING, MATERIAL_STATUS.NEEDS_REVIEW]}
    })
    total_users = await db["users"].count_documents({})
    
    # Sum downloads
    cursor = db["materials"].aggregate([
        {"$group": {"_id": None, "totalDownloads": {"$sum": "$downloads"}}}
    ])
    download_agg = await cursor.to_list(length=1)
    total_downloads = download_agg[0]["totalDownloads"] if download_agg else 0

    return {
        "totalMaterials": total_materials,
        "pendingApprovals": pending,
        "aiApproved": ai_approved,
        "adminApproved": admin_approved,
        "needsReview": needs_review,
        "rejected": rejected,
        "totalUsers": total_users,
        "totalDownloads": total_downloads,
        "autoPublishActive": settings.AUTO_PUBLISH_AI_APPROVED
    }

@router.get("/users", dependencies=[Depends(admin_guard)])
async def get_admin_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    cursor = db["users"].find({}).sort([("createdAt", -1)]).skip((page - 1) * limit).limit(limit)
    users = await cursor.to_list(length=limit)
    user_list = []
    for u in users:
        user_list.append({
            "id": str(u["_id"]),
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "department": u.get("department", "General"),
            "role": u.get("role", "student"),
            "createdAt": u.get("createdAt")
        })
    return {"users": user_list}

@router.get("/benchmarks", dependencies=[Depends(admin_guard)])
async def get_admin_benchmarks(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Fetches latest benchmark evaluation metrics for admin dashboard."""
    latest = await db["ai_benchmark_runs"].find_one(sort=[("timestamp", -1)])
    cfg = await db["system_settings"].find_one({"key": "scanning_booth"}) or {}
    max_pages = cfg.get("maxPages", settings.MAX_DOCUMENT_PAGES)
    high_thresh = cfg.get("confidenceHighThreshold", settings.CONFIDENCE_HIGH_THRESHOLD)
    med_thresh = cfg.get("confidenceMediumThreshold", settings.CONFIDENCE_MEDIUM_THRESHOLD)

    if not latest:
        report = await run_benchmark_evaluation(
            run_scanning_booth_analysis,
            high_threshold=high_thresh,
            medium_threshold=med_thresh,
            max_pages=max_pages
        )
        report["_id"] = str(ObjectId())
        await db["ai_benchmark_runs"].insert_one(report)
        return {
            "latest": report,
            "settings": {
                "maxPages": max_pages,
                "confidenceHighThreshold": high_thresh,
                "confidenceMediumThreshold": med_thresh
            }
        }

    latest["id"] = str(latest.get("_id", ""))
    latest.pop("_id", None)
    return {
        "latest": latest,
        "settings": {
            "maxPages": max_pages,
            "confidenceHighThreshold": high_thresh,
            "confidenceMediumThreshold": med_thresh
        }
    }

@router.post("/benchmarks/run", dependencies=[Depends(admin_guard)])
async def run_admin_benchmarks(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Executes benchmark test suite across labeled ground-truth dataset on demand."""
    cfg = await db["system_settings"].find_one({"key": "scanning_booth"}) or {}
    max_pages = cfg.get("maxPages", settings.MAX_DOCUMENT_PAGES)
    high_thresh = cfg.get("confidenceHighThreshold", settings.CONFIDENCE_HIGH_THRESHOLD)
    med_thresh = cfg.get("confidenceMediumThreshold", settings.CONFIDENCE_MEDIUM_THRESHOLD)

    report = await run_benchmark_evaluation(
        run_scanning_booth_analysis,
        high_threshold=high_thresh,
        medium_threshold=med_thresh,
        max_pages=max_pages
    )
    ins = await db["ai_benchmark_runs"].insert_one(report)
    report["id"] = str(ins.inserted_id)
    report.pop("_id", None)
    return {
        "message": "AI Benchmark Suite completed successfully.",
        "benchmark": report,
        "settings": {
            "maxPages": max_pages,
            "confidenceHighThreshold": high_thresh,
            "confidenceMediumThreshold": med_thresh
        }
    }

@router.post("/settings", dependencies=[Depends(admin_guard)])
async def update_admin_settings(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Updates configurable upload limit and confidence thresholds."""
    data = await request.json()
    update_data = {}
    if "maxPages" in data:
        update_data["maxPages"] = int(data["maxPages"])
    if "confidenceHighThreshold" in data:
        update_data["confidenceHighThreshold"] = float(data["confidenceHighThreshold"])
    if "confidenceMediumThreshold" in data:
        update_data["confidenceMediumThreshold"] = float(data["confidenceMediumThreshold"])

    update_data["updatedAt"] = datetime.utcnow()
    await db["system_settings"].update_one(
        {"key": "scanning_booth"},
        {"$set": update_data},
        upsert=True
    )

    cfg = await db["system_settings"].find_one({"key": "scanning_booth"}) or {}
    return {
        "message": "Configuration updated successfully.",
        "settings": {
            "maxPages": cfg.get("maxPages", settings.MAX_DOCUMENT_PAGES),
            "confidenceHighThreshold": cfg.get("confidenceHighThreshold", settings.CONFIDENCE_HIGH_THRESHOLD),
            "confidenceMediumThreshold": cfg.get("confidenceMediumThreshold", settings.CONFIDENCE_MEDIUM_THRESHOLD)
        }
    }


# ========================================================
# STRICT ACADEMIC DOCUMENT VALIDATION (ADMIN CONTROL)
# ========================================================

from app.services.academic_validator import (
    DEFAULT_ADMIN_RULES,
    DEFAULT_ALLOWED_TYPES,
    DEFAULT_RESTRICTED_TYPES,
    DOCUMENT_TYPE_LABELS,
    AcademicDocType
)

@router.get("/validation/rules", dependencies=[Depends(admin_guard)])
async def get_validation_rules(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Retrieves current admin-defined academic validation configuration."""
    cfg = await db["system_settings"].find_one({"key": "academic_validation"}) or {}
    rules = {**DEFAULT_ADMIN_RULES, **cfg.get("rules", {})}
    return {
        "rules": rules,
        "availableDocumentTypes": [
            {"type": k, "label": v, "isAllowedDefault": k in DEFAULT_ALLOWED_TYPES}
            for k, v in DOCUMENT_TYPE_LABELS.items()
        ]
    }

@router.patch("/validation/rules", dependencies=[Depends(admin_guard)])
async def update_validation_rules(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Updates admin academic validation rules, thresholds, and allowed categories."""
    data = await request.json()
    cfg = await db["system_settings"].find_one({"key": "academic_validation"}) or {}
    current_rules = {**DEFAULT_ADMIN_RULES, **cfg.get("rules", {})}

    if "strictValidationEnabled" in data:
        current_rules["strictValidationEnabled"] = bool(data["strictValidationEnabled"])
    if "minRelevanceThreshold" in data:
        current_rules["minRelevanceThreshold"] = max(0.0, min(1.0, float(data["minRelevanceThreshold"])))
    if "minConfidenceThreshold" in data:
        current_rules["minConfidenceThreshold"] = max(0.0, min(1.0, float(data["minConfidenceThreshold"])))
    if "requireSubjectMatch" in data:
        current_rules["requireSubjectMatch"] = bool(data["requireSubjectMatch"])
    if "allowedCategories" in data and isinstance(data["allowedCategories"], list):
        current_rules["allowedCategories"] = [str(c) for c in data["allowedCategories"]]
    if "restrictedCategories" in data and isinstance(data["restrictedCategories"], list):
        current_rules["restrictedCategories"] = [str(c) for c in data["restrictedCategories"]]

    audit_entry = {
        "updatedBy": current_user.get("id"),
        "adminName": current_user.get("name", "Admin"),
        "updatedAt": datetime.utcnow()
    }

    await db["system_settings"].update_one(
        {"key": "academic_validation"},
        {"$set": {"rules": current_rules, "lastUpdated": datetime.utcnow(), "lastAudit": audit_entry}},
        upsert=True
    )
    return {
        "message": "Academic validation rules updated successfully.",
        "rules": current_rules
    }

@router.get("/validation/stats", dependencies=[Depends(admin_guard)])
async def get_validation_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Computes stats across all documents: approved, rejected, needs review, and rejection reason breakdown."""
    total_docs = await db["materials"].count_documents({})
    approved_docs = await db["materials"].count_documents({
        "status": {"$in": ["ADMIN_APPROVED", "AI_APPROVED", "APPROVED", "QUALITY_CHECK_PASSED"]}
    })
    rejected_docs = await db["materials"].count_documents({"status": "REJECTED"})
    needs_review_docs = await db["materials"].count_documents({
        "status": {"$in": ["NEEDS_REVIEW", "PENDING", "Quality Check Failed", "CLASSIFICATION_CORRECTION_REQUESTED"]}
    })

    # Group rejections by document_type / reason
    pipeline = [
        {"$match": {"status": "REJECTED"}},
        {"$group": {"_id": "$validationDetails.document_type", "count": {"$sum": 1}}}
    ]
    rejection_breakdown = {}
    async for entry in db["materials"].aggregate(pipeline):
        t = entry.get("_id") or "OTHER"
        rejection_breakdown[t] = entry.get("count", 0)

    return {
        "totalUploaded": total_docs,
        "approved": approved_docs,
        "rejected": rejected_docs,
        "needsReview": needs_review_docs,
        "rejectionBreakdown": rejection_breakdown
    }

@router.get("/validation/documents", dependencies=[Depends(admin_guard)])
async def get_validation_documents(
    status: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Returns paginated list of validated documents with status, uploader, scores, and rejection reasons."""
    query = {}
    if status and status.upper() != "ALL":
        if status.upper() == "APPROVED":
            query["status"] = {"$in": ["ADMIN_APPROVED", "AI_APPROVED", "APPROVED"]}
        elif status.upper() == "NEEDS_REVIEW":
            query["status"] = {"$in": ["NEEDS_REVIEW", "PENDING", "Quality Check Failed"]}
        else:
            query["status"] = status.upper()

    if subject and subject.strip():
        query["$or"] = [
            {"subject": {"$regex": re.escape(subject.strip()), "$options": "i"}},
            {"department": {"$regex": re.escape(subject.strip()), "$options": "i"}}
        ]
    if batch and batch.strip():
        query["batch"] = {"$regex": re.escape(batch.strip()), "$options": "i"}

    skip = (page - 1) * limit
    cursor = db["materials"].find(query).sort([("createdAt", -1)]).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    total = await db["materials"].count_documents(query)

    items = []
    for d in docs:
        v = d.get("validationDetails", {})
        uploader_name = d.get("uploaderName") or d.get("uploader_name") or d.get("uploaderEmail") or "Student"
        items.append({
            "id": str(d.get("_id") or d.get("id")),
            "title": d.get("title", "Untitled Note"),
            "subject": d.get("subject", ""),
            "department": d.get("department", ""),
            "batch": d.get("batch", ""),
            "status": d.get("status", "PENDING"),
            "uploader": uploader_name,
            "documentType": v.get("document_type") or d.get("documentType") or "LECTURE_NOTES",
            "documentTypeLabel": v.get("document_type_label") or DOCUMENT_TYPE_LABELS.get(v.get("document_type"), "Study Notes"),
            "confidence": v.get("confidence") or d.get("confidenceScore", 0.9),
            "subjectRelevance": v.get("subject_relevance_score", 0.9),
            "rejectionReason": v.get("rejection_reason") or d.get("rejectionReason"),
            "studentMessage": v.get("student_message"),
            "verifiedAt": v.get("verified_at") or d.get("createdAt"),
            "overriddenBy": d.get("overrideDetails"),
            "createdAt": d.get("createdAt")
        })

    return {
        "documents": items,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit
    }

@router.post("/validation/{material_id}/override", dependencies=[Depends(admin_guard)])
async def override_validation_decision(
    material_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Allows admin to override a rejection or approval with audit logging."""
    data = await request.json()
    new_action = data.get("action")  # "APPROVE" or "REJECT"
    reason = data.get("reason", "").strip()

    if not reason:
        raise HTTPException(status_code=400, detail="Admin override reason is required.")
    if new_action not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Action must be APPROVE or REJECT.")

    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(query)
    if not mat:
        raise HTTPException(status_code=404, detail="Document not found.")

    new_status = "ADMIN_APPROVED" if new_action == "APPROVE" else "REJECTED"
    override_audit = {
        "adminId": str(current_user.get("id")),
        "adminName": current_user.get("name", "Administrator"),
        "adminEmail": current_user.get("email"),
        "previousStatus": mat.get("status"),
        "newStatus": new_status,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }

    update_fields = {
        "status": new_status,
        "overrideDetails": override_audit,
        "updatedAt": datetime.utcnow()
    }
    if new_action == "REJECT":
        update_fields["rejectionReason"] = f"Admin override: {reason}"

    await db["materials"].update_one(query, {"$set": update_fields})

    # Also log to audit collection
    await db["admin_audit_logs"].insert_one({
        "entity": "materials",
        "entityId": str(mat.get("_id")),
        "action": f"VALIDATION_OVERRIDE_{new_action}",
        "adminId": str(current_user.get("id")),
        "adminName": current_user.get("name", "Administrator"),
        "reason": reason,
        "timestamp": datetime.utcnow()
    })

    return {
        "message": f"Document status successfully overridden to {new_status}.",
        "newStatus": new_status,
        "override": override_audit
    }

