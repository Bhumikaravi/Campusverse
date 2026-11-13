from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_db
from app.models.material import MATERIAL_STATUS
from app.middleware.auth import require_role
from app.services.category_data import INITIAL_CATEGORIES_DATA

router = APIRouter(prefix="/api/categories", tags=["Academic Categories"])

class SubcategoryModel(BaseModel):
    id: str
    name: str
    subtopics: List[str] = []

class CategoryCreateModel(BaseModel):
    id: str
    name: str
    icon: Optional[str] = "BookOpen"
    description: Optional[str] = ""
    subcategories: List[SubcategoryModel] = []

async def sync_categories_seeded(db: AsyncIOMotorDatabase, force: bool = False):
    """Seed or synchronize categories into database so every category has its unique structure."""
    count = await db["academic_categories"].count_documents({})
    if count == 0 or force:
        if force:
            await db["academic_categories"].delete_many({})
        for cat in INITIAL_CATEGORIES_DATA:
            await db["academic_categories"].update_one(
                {"id": cat["id"]},
                {"$set": dict(cat)},
                upsert=True
            )

@router.post("/seed")
async def seed_categories_endpoint(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Reset and seed the dynamic academic category tree."""
    await sync_categories_seeded(db, force=True)
    return {"message": "Categories successfully synchronized and seeded."}

@router.get("")
async def get_categories_hierarchy(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Returns dynamic main categories, subcategories, subtopics, and document counts."""
    await sync_categories_seeded(db, force=False)

    # Calculate material counts per main category, subcategory, and subtopic
    pipeline = [
        {"$match": {"status": {"$in": [MATERIAL_STATUS.ADMIN_APPROVED, MATERIAL_STATUS.AI_APPROVED]}}},
        {"$group": {
            "_id": {
                "mainCategory": "$mainCategory",
                "subcategory": "$subcategory",
                "department": "$department",
                "subject": "$subject"
            },
            "count": {"$sum": 1}
        }}
    ]
    cursor = db["materials"].aggregate(pipeline)
    materials_agg = await cursor.to_list(length=1000)

    # Fetch dynamic categories from DB
    cats_cursor = db["academic_categories"].find({})
    raw_cats = await cats_cursor.to_list(length=100)

    result_categories = []
    for cat in raw_cats:
        c_id = cat.get("id")
        c_name = cat.get("name", "")
        cat_total = 0

        subcategories = []
        for sub in cat.get("subcategories", []):
            s_name = sub.get("name", "")
            s_subtopics = sub.get("subtopics", [])
            sub_count = 0

            # Count materials matching this category and subcategory
            for agg in materials_agg:
                ident = agg.get("_id", {})
                m_main = (ident.get("mainCategory") or "").lower()
                m_sub = (ident.get("subcategory") or "").lower()
                m_dept = (ident.get("department") or "").lower()

                main_matches = not m_main or m_main == c_name.lower() or m_main == c_id.lower()
                sub_matches = m_sub == s_name.lower() or m_dept == s_name.lower() or (s_name.lower() in m_dept)

                if main_matches and sub_matches:
                    sub_count += agg.get("count", 0)

            cat_total += sub_count
            subcategories.append({
                "id": sub.get("id"),
                "name": s_name,
                "subtopics": s_subtopics,
                "count": sub_count
            })

        result_categories.append({
            "id": c_id,
            "name": c_name,
            "icon": cat.get("icon", "BookOpen"),
            "description": cat.get("description", ""),
            "count": cat_total,
            "subcategories": subcategories
        })

    return {"categories": result_categories}

@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
async def create_category(payload: CategoryCreateModel, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Allows administrators to dynamically create new categories."""
    existing = await db["academic_categories"].find_one({"id": payload.id})
    if existing:
        raise HTTPException(status_code=400, detail="Category ID already exists.")
    
    doc = payload.dict()
    await db["academic_categories"].insert_one(doc)
    return {"message": "Category created successfully", "category": doc}

@router.delete("/{category_id}", dependencies=[Depends(require_role("admin"))])
async def delete_category(category_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Allows administrators to delete a dynamic category."""
    res = await db["academic_categories"].delete_one({"id": category_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
    return {"message": "Category deleted successfully"}
