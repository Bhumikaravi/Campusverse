from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.middleware.auth import get_current_user
from app.routers.materials import serialize_material

router = APIRouter(prefix="/api", tags=["Bookmarks & History"])

@router.get("/bookmarks")
async def get_user_bookmarks(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    cursor = db["bookmarks"].find({"userId": current_user["id"]}).sort([("createdAt", -1)])
    bookmarks = await cursor.to_list(length=100)
    mat_ids = [ObjectId(b["materialId"]) for b in bookmarks if ObjectId.is_valid(b["materialId"])]
    
    materials_cursor = db["materials"].find({"_id": {"$in": mat_ids}})
    materials = await materials_cursor.to_list(length=len(mat_ids))
    
    serialized = []
    for m in materials:
        item = serialize_material(m, current_user)
        item["bookmarked"] = True
        serialized.append(item)
    return {"materials": serialized, "items": serialized}

@router.post("/bookmarks/{material_id}")
async def toggle_bookmark(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    existing = await db["bookmarks"].find_one({
        "userId": current_user["id"],
        "materialId": material_id
    })

    if existing:
        await db["bookmarks"].delete_one({"_id": existing["_id"]})
        return {"bookmarked": False, "message": "Bookmark removed."}
    else:
        await db["bookmarks"].insert_one({
            "userId": current_user["id"],
            "materialId": material_id,
            "createdAt": datetime.utcnow()
        })
        return {"bookmarked": True, "message": "Bookmarked successfully."}

@router.get("/downloads/history")
async def get_download_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    cursor = db["downloads"].find({"userId": current_user["id"]}).sort([("downloadedAt", -1)]).limit(50)
    history = await cursor.to_list(length=50)
    out = []
    for h in history:
        out.append({
            "id": str(h["_id"]),
            "materialId": h.get("materialId"),
            "title": h.get("title", "Notes"),
            "subject": h.get("subject", "General"),
            "fileSize": h.get("fileSize", "PDF"),
            "downloadedAt": h.get("downloadedAt", datetime.utcnow())
        })
    return {"history": out}
