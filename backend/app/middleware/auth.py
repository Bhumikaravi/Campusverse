import datetime
from typing import Optional, List
import jwt
from bson import ObjectId
from fastapi import Request, Response, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.config import settings
from app.database import get_db

# Password utilities using pwdlib with Argon2 (primary) + Bcrypt (compat)
pwd_context = PasswordHash((Argon2Hasher(), BcryptHasher()))

def hash_password(password: str) -> str:
    """Hashes password using Argon2."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against Argon2 or Bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

# JWT utilities
def create_access_token(user_id: str, role: str, expires_days: Optional[int] = None) -> str:
    days = expires_days or settings.JWT_EXPIRES_DAYS
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def set_auth_cookie(response: Response, token: str):
    max_age = settings.JWT_EXPIRES_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/"
    )

def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/"
    )

# Current User dependencies
async def get_optional_user(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Optional[dict]:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        token = request.query_params.get("token")
            
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        # Look up by ObjectId or string ID
        query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
        user = await db["users"].find_one(query)
        if not user:
            return None
            
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        # Strip all sensitive fields
        user.pop("hashed_password", None)
        user.pop("passwordHash", None)
        # Ensure both full_name and name exist
        name_val = user.get("full_name") or user.get("name") or "Student"
        user["full_name"] = name_val
        user["name"] = name_val
        user["course"] = user.get("course") or "Computer Science and Engineering"
        user["academicYear"] = user.get("academicYear") or "3rd Year"
        user["batch"] = user.get("batch") or "Batch 2023-2027"
        return user
    except Exception:
        return None

async def get_current_user(
    user: Optional[dict] = Depends(get_optional_user)
) -> dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_role(*allowed_roles: str):
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return user
    return role_checker

def is_staff(user: Optional[dict]) -> bool:
    if not user:
        return False
    return user.get("role") in ["moderator", "admin"]
