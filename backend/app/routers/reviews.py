from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/materials", tags=["Ratings"])

class RatingPayload(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="1 to 5 star rating")

@router.get("/{material_id}/rating/me")
async def get_my_rating(
    material_id: str,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieves the authenticated user's current 1-5 star rating for this material, if any."""
    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(query)
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found.")

    user_rating = 0
    if current_user:
        existing = await db["reviews"].find_one({
            "materialId": material_id,
            "userId": current_user["id"]
        })
        if existing:
            user_rating = existing.get("rating", 0)

    return {
        "materialId": material_id,
        "userRating": user_rating,
        "averageRating": round(float(mat.get("rating", 5.0)), 1),
        "totalRatings": int(mat.get("ratingCount", 0))
    }

@router.post("/{material_id}/rating", status_code=status.HTTP_200_OK)
@router.post("/{material_id}/reviews", status_code=status.HTTP_200_OK)
async def submit_or_update_rating(
    material_id: str,
    payload: RatingPayload,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Submits or updates a 1-5 star rating for an academic material.
    Guarantees strictly one rating per user per document.
    Automatically recalculates dynamic average rating and count.
    """
    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(query)
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found.")

    now = datetime.utcnow()
    user_id = str(current_user["id"])
    user_name = current_user.get("full_name") or current_user.get("name") or "Student"

    # Upsert single rating per user
    filter_query = {"materialId": material_id, "userId": user_id}
    update_data = {
        "$set": {
            "rating": payload.rating,
            "userName": user_name,
            "updatedAt": now
        },
        "$setOnInsert": {
            "materialId": material_id,
            "userId": user_id,
            "createdAt": now
        }
    }

    await db["reviews"].update_one(filter_query, update_data, upsert=True)

    # Recalculate accurate aggregate rating
    cursor = db["reviews"].aggregate([
        {"$match": {"materialId": material_id}},
        {"$group": {"_id": None, "avgRating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ])
    rating_data = await cursor.to_list(length=1)

    avg_rating = round(rating_data[0]["avgRating"], 1) if rating_data else float(payload.rating)
    total_count = rating_data[0]["count"] if rating_data else 1

    await db["materials"].update_one(
        query,
        {"$set": {"rating": avg_rating, "ratingCount": total_count, "updatedAt": now}}
    )

    return {
        "message": "Rating recorded successfully.",
        "userRating": payload.rating,
        "averageRating": avg_rating,
        "totalRatings": total_count
    }

@router.get("/{material_id}/reviews")
async def get_material_ratings_summary(
    material_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Returns rating summary for the material."""
    query = {"_id": ObjectId(material_id)} if ObjectId.is_valid(material_id) else {"_id": material_id}
    mat = await db["materials"].find_one(query)
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found.")

    avg = round(float(mat.get("rating", 5.0)), 1)
    cnt = int(mat.get("ratingCount", 0))

    return {
        "materialId": material_id,
        "averageRating": avg,
        "totalRatings": cnt,
        "reviews": []
    }
