from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class MATERIAL_STATUS:
    PENDING = "PENDING"
    AI_APPROVED = "AI_APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"
    ADMIN_APPROVED = "ADMIN_APPROVED"
    ADMIN_REJECTED = "ADMIN_REJECTED"
    QUALITY_CHECK_PASSED = "QUALITY_CHECK_PASSED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"

StatusType = Literal[
    "PENDING",
    "AI_APPROVED",
    "NEEDS_REVIEW",
    "REJECTED",
    "ADMIN_APPROVED",
    "ADMIN_REJECTED",
    "QUALITY_CHECK_PASSED",
    "NEEDS_CORRECTION",
]

class AIReviewResult(BaseModel):
    provider: str = "rules"  # "gemini" | "rules"
    model: str = "keyword-heuristics-v1"
    usedFallback: bool = True
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str = Field("", max_length=500)
    flags: List[str] = Field(default_factory=list)
    reviewedAt: datetime = Field(default_factory=datetime.utcnow)

class ModerationRecord(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: Optional[str] = Field(None, max_length=500)
    reviewedBy: Optional[str] = None
    moderatorName: Optional[str] = None
    reviewedAt: datetime = Field(default_factory=datetime.utcnow)

class MaterialCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    summary: Optional[str] = None
    summaryWordCount: Optional[int] = 0
    processingStatus: Optional[str] = "Summary ready"
    academicCategory: Optional[str] = Field("Engineering", max_length=100)
    mainCategory: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=150)
    department: Optional[str] = Field(None, max_length=80)
    course: Optional[str] = Field("Computer Science and Engineering", max_length=120)
    academicYear: Optional[str] = Field("3rd Year", max_length=50)
    batch: Optional[str] = Field("Batch 2023-2027", max_length=50)
    semester: Optional[int] = Field(None, ge=1, le=12)
    subject: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field("notes", max_length=50)

    @field_validator("description", "summary", mode="before")
    @classmethod
    def validate_summary_word_count(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip()
        if not clean:
            return clean
        words = clean.split()
        if len(words) > 500:
            raise ValueError(f"Summary must not exceed 500 words. Currently {len(words)} words.")
        return clean

class MaterialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    summary: Optional[str] = None
    academicCategory: Optional[str] = None
    mainCategory: Optional[str] = None
    department: Optional[str] = Field(None, min_length=2, max_length=80)
    course: Optional[str] = Field(None, max_length=120)
    academicYear: Optional[str] = Field(None, max_length=50)
    batch: Optional[str] = Field(None, max_length=50)
    semester: Optional[int] = Field(None, ge=1, le=12)
    subject: Optional[str] = Field(None, min_length=2, max_length=100)
    topic: Optional[str] = None
    category: Optional[str] = None

    @field_validator("description", "summary", mode="before")
    @classmethod
    def validate_summary_word_count(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip()
        if not clean:
            return clean
        words = clean.split()
        if len(words) > 500:
            raise ValueError(f"Summary must not exceed 500 words. Currently {len(words)} words.")
        return clean

class ClassificationCorrection(BaseModel):
    branch: str = Field(..., min_length=2, max_length=100)
    subject: str = Field(..., min_length=2, max_length=100)
    topic: Optional[str] = None
    reason: Optional[str] = None

class MaterialInDB(BaseModel):
    id: Optional[str] = None
    documentId: Optional[str] = None
    title: str
    description: str
    summary: Optional[str] = None
    summaryWordCount: Optional[int] = 0
    maxSummaryWords: int = 500
    processingStatus: Optional[str] = "Completed"
    extractionStatus: Optional[str] = "Completed"
    pageCount: Optional[int] = 1
    totalPageCount: Optional[int] = 1
    processedPageCount: Optional[int] = 1
    pagesExtracted: List[int] = Field(default_factory=list)
    pagesOcr: List[int] = Field(default_factory=list)
    pagesFailed: List[int] = Field(default_factory=list)
    uploader: str  # User ID
    uploaderName: Optional[str] = None
    department: Optional[str] = "Engineering"
    course: Optional[str] = "Computer Science and Engineering"
    academicYear: Optional[str] = "3rd Year"
    batch: Optional[str] = "Batch 2023-2027"
    semester: Optional[int] = 1
    subject: Optional[str] = "Engineering"
    academicCategory: Optional[str] = "Engineering"
    mainCategory: Optional[str] = "Engineering"
    subcategory: Optional[str] = None
    topic: Optional[str] = None
    category: str = "notes"

    fileUrl: str
    storageKey: str
    storageProvider: str
    originalName: str
    mimeType: str
    extension: str
    size: int
    fileHash: str
    textHash: Optional[str] = None

    status: StatusType = MATERIAL_STATUS.PENDING
    aiReview: Optional[AIReviewResult] = None
    classification: Optional[dict] = None
    qualityReport: Optional[dict] = None
    similarityReport: Optional[dict] = None
    hasChapterSummaries: Optional[bool] = False
    moderation: Optional[ModerationRecord] = None
    duplicateOf: Optional[str] = None  # ID of existing material if duplicate detected
    downloads: int = 0
    rating: float = 5.0
    ratingCount: int = 0
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class MaterialOut(BaseModel):
    id: str
    documentId: Optional[str] = None
    title: str
    description: str
    summary: Optional[str] = None
    summaryWordCount: Optional[int] = 0
    maxSummaryWords: int = 500
    processingStatus: Optional[str] = "Completed"
    extractionStatus: Optional[str] = "Completed"
    pageCount: Optional[int] = 1
    totalPageCount: Optional[int] = 1
    processedPageCount: Optional[int] = 1
    pagesExtracted: List[int] = Field(default_factory=list)
    pagesOcr: List[int] = Field(default_factory=list)
    pagesFailed: List[int] = Field(default_factory=list)
    uploader: Optional[str] = None
    uploaderName: Optional[str] = "Student"
    academicCategory: Optional[str] = "Engineering"
    mainCategory: Optional[str] = "Engineering"
    subcategory: Optional[str] = None
    topic: Optional[str] = None
    department: Optional[str] = "Engineering"
    course: Optional[str] = "Computer Science and Engineering"
    academicYear: Optional[str] = "3rd Year"
    batch: Optional[str] = "Batch 2023-2027"
    semester: Optional[int] = 1
    subject: Optional[str] = "Engineering"
    category: Optional[str] = "notes"
    fileUrl: str
    correctedFileUrl: Optional[str] = None
    fileType: str  # e.g. "PDF", "DOCX", "PPTX", "PNG"
    fileSize: str  # formatted e.g. "2.4 MB"
    originalName: str
    mimeType: str
    extension: str
    downloads: int = 0
    rating: float = 5.0
    ratingCount: int = 0
    status: StatusType
    bookmarked: bool = False
    aiReview: Optional[AIReviewResult] = None
    classification: Optional[dict] = None
    qualityReport: Optional[dict] = None
    similarityReport: Optional[dict] = None
    hasChapterSummaries: Optional[bool] = False
    scanReport: Optional[dict] = None
    moderation: Optional[ModerationRecord] = None
    duplicateOf: Optional[str] = None
    createdAt: datetime
    uploadedAt: Optional[datetime] = None

    class Config:
        from_attributes = True
