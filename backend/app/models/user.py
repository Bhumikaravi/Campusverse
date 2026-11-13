from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

RoleType = Literal["student", "moderator", "admin"]

class UserRegister(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    confirm_password: Optional[str] = None
    confirmPassword: Optional[str] = None
    department: Optional[str] = Field(None, max_length=80)
    course: Optional[str] = Field("Computer Science and Engineering", max_length=120)
    academicYear: Optional[str] = Field("3rd Year", max_length=50)
    batch: Optional[str] = Field("Batch 2023-2027", max_length=50)
    semester: Optional[int] = Field(None, ge=1, le=12)

    @model_validator(mode="before")
    @classmethod
    def reconcile_name_and_passwords(cls, data: dict):
        if not isinstance(data, dict):
            return data
            
        # Reconcile name / full_name
        resolved_name = data.get("full_name") or data.get("name")
        if not resolved_name or len(resolved_name.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        data["full_name"] = resolved_name.strip()
        data["name"] = resolved_name.strip()

        # Normalize email
        if "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].strip().lower()

        # Check confirm password if provided
        pwd = data.get("password")
        confirm = data.get("confirm_password") or data.get("confirmPassword")
        if confirm and pwd != confirm:
            raise ValueError("Passwords do not match.")

        return data

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

class UserLogin(BaseModel):
    # Accepts email address or username
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_login_identifier(cls, v: str) -> str:
        clean = v.strip().lower()
        if not clean:
            raise ValueError("Email address or username is required.")
        return clean

class UserInDB(BaseModel):
    id: Optional[str] = None
    full_name: str
    name: str
    email: str
    hashed_password: str
    passwordHash: str
    department: Optional[str] = None
    course: Optional[str] = "Computer Science and Engineering"
    academicYear: Optional[str] = "3rd Year"
    batch: Optional[str] = "Batch 2023-2027"
    semester: Optional[int] = None
    role: RoleType = "student"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserOut(BaseModel):
    id: str
    full_name: str
    name: str
    email: str
    department: Optional[str] = None
    course: Optional[str] = "Computer Science and Engineering"
    academicYear: Optional[str] = "3rd Year"
    batch: Optional[str] = "Batch 2023-2027"
    semester: Optional[int] = None
    role: RoleType = "student"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True
