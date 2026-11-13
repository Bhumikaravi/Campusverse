import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.models.user import UserRegister, UserLogin, UserOut
from app.middleware.auth import (
    hash_password,
    verify_password,
    create_access_token,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user,
)
from app.middleware.rate_limit import check_auth_rate_limit

logger = logging.getLogger("campusverse.auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    response: Response,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    await check_auth_rate_limit(request)
    
    normalized_email = user_data.email.strip().lower()
    full_name = user_data.full_name or user_data.name or "Student"
    
    # 1. Check if email already exists
    existing = await db["users"].find_one({"email": normalized_email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in instead."
        )

    # 2. Hash password with pwdlib (Argon2)
    hashed_pwd = hash_password(user_data.password)
    now = datetime.utcnow()

    user_doc = {
        "full_name": full_name,
        "name": full_name,
        "email": normalized_email,
        "hashed_password": hashed_pwd,
        "passwordHash": hashed_pwd,
        "department": user_data.department.strip() if user_data.department else None,
        "course": getattr(user_data, "course", None) or "Computer Science and Engineering",
        "academicYear": getattr(user_data, "academicYear", None) or "3rd Year",
        "batch": getattr(user_data, "batch", None) or "Batch 2023-2027",
        "semester": user_data.semester,
        "role": "student",
        "created_at": now,
        "updated_at": now,
        "createdAt": now,
    }

    try:
        result = await db["users"].insert_one(user_doc)
        user_id = str(result.inserted_id)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )
    except Exception as e:
        logger.error("User registration error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save new account to the database. Please try again."
        )

    # 3. Create persistent JWT & Set HTTP-only Cookie
    token = create_access_token(user_id=user_id, role="student")
    set_auth_cookie(response, token)

    user_out = UserOut(
        id=user_id,
        full_name=full_name,
        name=full_name,
        email=normalized_email,
        department=user_doc["department"],
        course=user_doc.get("course", "Computer Science and Engineering"),
        academicYear=user_doc.get("academicYear", "3rd Year"),
        batch=user_doc.get("batch", "Batch 2023-2027"),
        semester=user_doc["semester"],
        role="student",
        created_at=now,
        updated_at=now,
        createdAt=now
    )

    logger.info("User registered successfully: %s (%s)", normalized_email, user_id)

    return {
        "message": "Account created successfully.",
        "token": token,
        "user": user_out.model_dump()
    }

@router.post("/login")
async def login(
    credentials: UserLogin,
    response: Response,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    await check_auth_rate_limit(request)

    identifier = credentials.email.strip()
    norm_identifier = identifier.lower()

    # Search by normalized email or case-insensitive name
    user = await db["users"].find_one({
        "$or": [
            {"email": norm_identifier},
            {"name": {"$regex": f"^{identifier}$", "$options": "i"}},
            {"full_name": {"$regex": f"^{identifier}$", "$options": "i"}}
        ]
    })

    stored_hash = user.get("hashed_password") or user.get("passwordHash") if user else None

    if not user or not stored_hash or not verify_password(credentials.password, stored_hash):
        logger.warning("Failed login attempt for identifier: %s", identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials and try again."
        )

    user_id = str(user["_id"])
    role = user.get("role", "student")
    token = create_access_token(user_id=user_id, role=role)
    set_auth_cookie(response, token)

    full_name = user.get("full_name") or user.get("name") or "Student"

    user_out = UserOut(
        id=user_id,
        full_name=full_name,
        name=full_name,
        email=user.get("email", ""),
        department=user.get("department"),
        course=user.get("course", "Computer Science and Engineering"),
        academicYear=user.get("academicYear", "3rd Year"),
        batch=user.get("batch", "Batch 2023-2027"),
        semester=user.get("semester"),
        role=role,
        created_at=user.get("created_at") or user.get("createdAt"),
        updated_at=user.get("updated_at"),
        createdAt=user.get("createdAt") or user.get("created_at")
    )

    logger.info("User logged in successfully: %s (%s)", user.get("email"), user_id)

    return {
        "message": "Login successful.",
        "token": token,
        "user": user_out.model_dump()
    }

@router.post("/admin-login")
async def admin_login(
    credentials: UserLogin,
    response: Response,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    await check_auth_rate_limit(request)

    identifier = credentials.email.strip()
    norm_identifier = identifier.lower()

    user = await db["users"].find_one({
        "$or": [
            {"email": norm_identifier},
            {"name": {"$regex": f"^{identifier}$", "$options": "i"}},
            {"full_name": {"$regex": f"^{identifier}$", "$options": "i"}}
        ]
    })

    stored_hash = user.get("hashed_password") or user.get("passwordHash") if user else None

    if not user or not stored_hash or not verify_password(credentials.password, stored_hash):
        logger.warning("Failed admin login attempt for identifier: %s", identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials. Please check your email and password."
        )

    role = user.get("role", "student")
    if role not in ["admin", "moderator"]:
        logger.warning("Unauthorized access to admin portal by user: %s (role: %s)", identifier, role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Your account does not have administrator privileges."
        )

    user_id = str(user["_id"])
    token = create_access_token(user_id=user_id, role=role)
    set_auth_cookie(response, token)

    full_name = user.get("full_name") or user.get("name") or "Administrator"
    user_out = UserOut(
        id=user_id,
        full_name=full_name,
        name=full_name,
        email=user.get("email", ""),
        department=user.get("department"),
        course=user.get("course", "Computer Science and Engineering"),
        academicYear=user.get("academicYear", "3rd Year"),
        batch=user.get("batch", "Batch 2023-2027"),
        semester=user.get("semester"),
        role=role,
        created_at=user.get("created_at") or user.get("createdAt"),
        updated_at=user.get("updated_at"),
        createdAt=user.get("createdAt") or user.get("created_at")
    )

    logger.info("Administrator logged in successfully: %s (%s)", user.get("email"), user_id)

    return {
        "message": "Administrator login successful.",
        "token": token,
        "user": user_out.model_dump()
    }

@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully."}

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}
