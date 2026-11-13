from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field("", max_length=1000)

class ReviewInDB(BaseModel):
    id: Optional[str] = None
    materialId: str
    userId: str
    userName: str
    rating: int
    comment: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class ReviewOut(BaseModel):
    id: str
    materialId: str
    userName: str
    rating: int
    comment: str
    createdAt: datetime
