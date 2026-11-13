# backend/app/routers/study_buddy.py
"""Study Buddy API router.
Provides:
- POST /api/study-buddy/scan : uploads file or text, extracts text, generates study notes, issues, Q&A, definitions.
- GET  /api/study-buddy/:id/notes : returns generated notes.
- POST /api/study-buddy/:id/chat : conversational AI Q&A over the analyzed material.
- POST /api/study-buddy/demo : instantly loads and processes one of the pre-bundled demo files.
"""

import os
import secrets
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_optional_user
from app.services.file_security import validate_and_scan_file, sanitize_filename
from app.services.text_extract import extract_document_text
from app.services.study_notes import generate_study_notes, answer_study_query
from app.storage.factory import get_storage

router = APIRouter(prefix="/api/study-buddy", tags=["Study Buddy"])

@router.post("/scan", status_code=status.HTTP_200_OK)
async def scan_and_analyze(
    title: Optional[str] = Form(None),
    text_content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    extracted_text = ""
    file_name = "pasted_text.txt"
    file_type = "TEXT"
    file_size_str = "0 KB"

    if file and file.filename:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
        
        orig_name = sanitize_filename(file.filename)
        file_name = orig_name
        ext, mime, kind = validate_and_scan_file(file_bytes, orig_name)
        file_type = ext.upper().lstrip(".")
        size_kb = len(file_bytes) / 1024
        file_size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"

        extracted_text = extract_document_text(file_bytes, ext)
        if not extracted_text.strip():
            extracted_text = f"Scanned file: {orig_name}. Contains visual diagram or handwritten format."
    elif text_content and text_content.strip():
        extracted_text = text_content.strip()
        file_name = title or "Custom Text Notes"
        file_size_str = f"{len(extracted_text.encode('utf-8'))/1024:.1f} KB"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a study material file (PDF, DOCX, TXT, PPTX) or paste study notes."
        )

    # Generate Notes, Issues, and Practice Questions
    notes_data = await generate_study_notes(extracted_text)

    # Persist session in study_buddy collection for interactive chat
    session_doc = {
        "title": title or file_name,
        "fileName": file_name,
        "fileType": file_type,
        "fileSize": file_size_str,
        "extractedText": extracted_text[:10000],
        "notes": notes_data,
        "userId": current_user.get("id") if current_user else "guest",
        "createdAt": datetime.utcnow()
    }
    res = await db["study_buddy_sessions"].insert_one(session_doc)
    session_id = str(res.inserted_id)

    return {
        "sessionId": session_id,
        "fileName": file_name,
        "fileType": file_type,
        "fileSize": file_size_str,
        "notes": notes_data,
        "charCount": len(extracted_text)
    }

@router.post("/demo/{demo_key}")
async def load_demo_material(demo_key: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Loads a pre-bundled realistic sample file from sample_files folder and runs Study Buddy analysis."""
    sample_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public", "sample_files")
    
    mapping = {
        "os": "01_os_cpu_scheduling.pdf",
        "dbms": "02_dbms_sql_normalization.docx",
        "ml": "03_machine_learning_lab_manual.pdf",
        "cn": "04_computer_networks_cheatsheet.png",
        "dsa": "05_data_structures_past_paper.pdf",
        "embedded": "06_embedded_systems_slides.pptx",
        "notes": "study_plan_guide.md"
    }

    filename = mapping.get(demo_key.lower(), "01_os_cpu_scheduling.pdf")
    filepath = os.path.join(sample_dir, filename)

    if not os.path.exists(filepath):
        # Fallback to local sample_files
        alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sample_files", filename)
        if os.path.exists(alt_path):
            filepath = alt_path
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Demo file '{filename}' not found.")

    with open(filepath, "rb") as f:
        file_bytes = f.read()

    _, ext = os.path.splitext(filename)
    extracted_text = extract_document_text(file_bytes, ext)
    if not extracted_text.strip():
        extracted_text = f"Sample handwritten / visual lecture notes for {filename}."

    notes_data = await generate_study_notes(extracted_text)

    size_kb = len(file_bytes) / 1024
    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"

    session_doc = {
        "title": f"Demo: {filename}",
        "fileName": filename,
        "fileType": ext.upper().lstrip("."),
        "fileSize": size_str,
        "extractedText": extracted_text[:10000],
        "notes": notes_data,
        "userId": "demo-reviewer",
        "createdAt": datetime.utcnow()
    }
    res = await db["study_buddy_sessions"].insert_one(session_doc)
    session_id = str(res.inserted_id)

    return {
        "sessionId": session_id,
        "fileName": filename,
        "fileType": ext.upper().lstrip("."),
        "fileSize": size_str,
        "notes": notes_data,
        "charCount": len(extracted_text)
    }

@router.get("/{session_id}/notes")
async def get_session_notes(session_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(session_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session identifier")
    
    session = await db["study_buddy_sessions"].find_one({"_id": oid})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found")

    return {
        "sessionId": session_id,
        "title": session.get("title"),
        "fileName": session.get("fileName"),
        "notes": session.get("notes")
    }

from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: Optional[str] = None

@router.post("/{session_id}/chat")
async def chat_with_study_buddy(
    session_id: str,
    request: Request,
    query: Optional[str] = Form(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # Retrieve query either from form or json body
    actual_query = query
    if not actual_query:
        try:
            body = await request.json()
            if isinstance(body, dict):
                actual_query = body.get("query")
        except Exception:
            pass

    if not actual_query:
        try:
            form = await request.form()
            actual_query = form.get("query")
        except Exception:
            pass

    if not actual_query or not str(actual_query).strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query parameter is required")
    try:
        oid = ObjectId(session_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session identifier")

    session = await db["study_buddy_sessions"].find_one({"_id": oid})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found")

    context = session.get("extractedText") or session.get("notes", {}).get("fullText", "")
    answer = await answer_study_query(context, str(actual_query))

    return {
        "query": str(actual_query),
        "answer": answer,
        "timestamp": datetime.utcnow().isoformat()
    }
