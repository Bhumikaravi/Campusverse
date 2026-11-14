import logging
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.middleware.auth import get_current_user, is_staff
from app.services.rag_engine import execute_rag_pipeline

logger = logging.getLogger("campusverse.chat_router")
router = APIRouter(prefix="/api/chat", tags=["Chat With Notes"])

class CreateSessionRequest(BaseModel):
    materialIds: List[str] = Field(..., min_items=1)
    title: Optional[str] = None

class PostMessageRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1500)

@router.get("/materials")
async def get_available_chat_materials(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Returns list of study materials the user is authorized to chat with
    (ADMIN_APPROVED, AI_APPROVED, uploaded by the user, or available in the catalog).
    """
    is_admin = is_staff(current_user)
    docs = []
    
    if is_admin:
        cursor = db["materials"].find({"status": {"$nin": ["REJECTED", "ADMIN_REJECTED"]}}).sort([("createdAt", -1)]).limit(100)
        docs = await cursor.to_list(length=100)
    else:
        user_id = str(current_user.get("id", ""))
        uploader_clauses = [
            {"uploader": user_id},
            {"uploader": str(user_id)},
            {"uploader_id": user_id},
            {"userId": user_id},
        ]
        if ObjectId.is_valid(user_id):
            uploader_clauses.extend([
                {"uploader": ObjectId(user_id)},
                {"userId": ObjectId(user_id)},
            ])
        if current_user.get("email"):
            uploader_clauses.extend([
                {"uploader": current_user["email"]},
                {"uploaderEmail": current_user["email"]},
            ])

        query = {
            "$and": [
                {"status": {"$nin": ["REJECTED", "ADMIN_REJECTED"]}},
                {
                    "$or": [
                        {"status": {"$in": ["ADMIN_APPROVED", "AI_APPROVED", "APPROVED", "QUALITY_CHECK_PASSED", "Completed", "PENDING", "NEEDS_REVIEW"]}},
                        *uploader_clauses
                    ]
                }
            ]
        }
        cursor = db["materials"].find(query).sort([("createdAt", -1)]).limit(100)
        docs = await cursor.to_list(length=100)

        # Fallback: if no documents match strict filter, return any approved study materials
        # in the platform so students are never blocked with an empty context list
        if not docs:
            cursor = db["materials"].find({"status": {"$nin": ["REJECTED", "ADMIN_REJECTED"]}}).sort([("createdAt", -1)]).limit(100)
            docs = await cursor.to_list(length=100)
    
    items = []
    for d in docs:
        items.append({
            "id": str(d.get("_id") or d.get("id") or d.get("documentId")),
            "title": d.get("title", "Untitled Note"),
            "subject": d.get("subject", ""),
            "department": d.get("department", ""),
            "pageCount": d.get("totalPageCount") or d.get("pageCount", 1),
            "fileType": str(d.get("extension", ".pdf")).upper().lstrip("."),
            "status": d.get("status", "Available")
        })
    return {"materials": items}

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    payload: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Starts a new chat session bound to one or more selected documents."""
    material_ids = [mid.strip() for mid in payload.materialIds if mid.strip()]
    if not material_ids:
        raise HTTPException(status_code=400, detail="At least one study material must be selected.")

    # Fetch document titles for session header
    obj_ids = [ObjectId(m) for m in material_ids if ObjectId.is_valid(m)]
    id_clauses = [{"_id": {"$in": obj_ids}}] if obj_ids else []
    id_clauses.extend([
        {"_id": {"$in": material_ids}},
        {"id": {"$in": material_ids}},
        {"documentId": {"$in": material_ids}}
    ])
    cursor = db["materials"].find({"$or": id_clauses} if len(id_clauses) > 1 else id_clauses[0] if id_clauses else {})
    found_docs = await cursor.to_list(length=max(10, len(material_ids)))

    # Prevent rejected materials from being used in chatbot
    for d in found_docs:
        if d.get("status") in ["REJECTED", "ADMIN_REJECTED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Upload rejected. CampusVerse only accepts academic study materials. '{d.get('title', 'Document')}' was rejected as non-academic content and cannot be accessed via chatbot."
            )

    titles = [d.get("title", "Study Note") for d in found_docs if d.get("title")]
    if not titles:
        titles = ["Academic Study Notes"]

    session_title = payload.title or (", ".join(titles[:2]) + ("..." if len(titles) > 2 else ""))
    now = datetime.utcnow()

    session_doc = {
        "userId": current_user["id"],
        "title": session_title[:80],
        "materialIds": material_ids,
        "materialTitles": titles,
        "messageCount": 0,
        "createdAt": now,
        "updatedAt": now
    }

    res = await db["chat_sessions"].insert_one(session_doc)
    session_id = str(res.inserted_id)

    # Initial greeting message
    initial_msg = {
        "sessionId": session_id,
        "userId": current_user["id"],
        "role": "assistant",
        "content": f"Hello! I am ready to answer your questions based on: {', '.join(titles)}. What would you like to know?",
        "sources": [],
        "createdAt": now
    }
    await db["chat_messages"].insert_one(initial_msg)

    return {
        "sessionId": session_id,
        "title": session_title,
        "materialIds": material_ids,
        "materialTitles": titles,
        "createdAt": now
    }

@router.get("/sessions")
async def list_user_sessions(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lists all saved chat sessions for the current user."""
    cursor = db["chat_sessions"].find({"userId": current_user["id"]}).sort([("updatedAt", -1)])
    sessions = await cursor.to_list(length=50)

    result = []
    for s in sessions:
        result.append({
            "sessionId": str(s["_id"]),
            "title": s.get("title", "Notes Chat"),
            "materialIds": s.get("materialIds", []),
            "materialTitles": s.get("materialTitles", []),
            "messageCount": s.get("messageCount", 0),
            "createdAt": s.get("createdAt"),
            "updatedAt": s.get("updatedAt")
        })
    return {"sessions": result}

@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieves session details and full conversational message history."""
    query = {"_id": ObjectId(session_id)} if ObjectId.is_valid(session_id) else {"_id": session_id}
    session = await db["chat_sessions"].find_one(query)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if str(session.get("userId")) != str(current_user["id"]) and not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Access denied.")

    cursor = db["chat_messages"].find({"sessionId": str(session["_id"])}).sort([("createdAt", 1)])
    messages = await cursor.to_list(length=200)

    formatted_msgs = []
    for m in messages:
        formatted_msgs.append({
            "id": str(m["_id"]),
            "role": m.get("role", "user"),
            "content": m.get("content", ""),
            "sources": m.get("sources", []),
            "guardrailTriggered": m.get("guardrailTriggered", False),
            "guardrailDetails": m.get("guardrailDetails"),
            "createdAt": m.get("createdAt")
        })

    return {
        "session": {
            "sessionId": str(session["_id"]),
            "title": session.get("title", ""),
            "materialIds": session.get("materialIds", []),
            "materialTitles": session.get("materialTitles", []),
        },
        "messages": formatted_msgs
    }

@router.post("/sessions/{session_id}/message")
async def send_chat_message(
    session_id: str,
    payload: PostMessageRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Submits student question to RAG pipeline.
    Retrieves grounded notes chunks, generates answer with citations, and updates conversation history.
    """
    query = {"_id": ObjectId(session_id)} if ObjectId.is_valid(session_id) else {"_id": session_id}
    session = await db["chat_sessions"].find_one(query)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if str(session.get("userId")) != str(current_user["id"]) and not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Access denied.")

    now = datetime.utcnow()
    user_q = payload.question.strip()

    # Save user message
    user_msg_doc = {
        "sessionId": str(session["_id"]),
        "userId": current_user["id"],
        "role": "user",
        "content": user_q,
        "createdAt": now
    }
    await db["chat_messages"].insert_one(user_msg_doc)

    # Fetch last 4 messages for conversational context
    cursor = db["chat_messages"].find({"sessionId": str(session["_id"])}).sort([("createdAt", -1)]).limit(6)
    history_docs = await cursor.to_list(length=6)
    history = [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in reversed(history_docs)]

    # Run RAG execution
    rag_result = await execute_rag_pipeline(
        query=user_q,
        material_ids=session.get("materialIds", []),
        user_id=current_user["id"],
        is_admin=is_staff(current_user),
        conversation_history=history
    )

    # Save assistant message
    ai_msg_doc = {
        "sessionId": str(session["_id"]),
        "userId": current_user["id"],
        "role": "assistant",
        "content": rag_result["answer"],
        "sources": rag_result.get("sources", []),
        "guardrailTriggered": rag_result.get("guardrail_triggered", False),
        "guardrailDetails": rag_result.get("guardrail_details"),
        "createdAt": datetime.utcnow()
    }
    ai_res = await db["chat_messages"].insert_one(ai_msg_doc)

    # Update session activity
    await db["chat_sessions"].update_one(query, {
        "$inc": {"messageCount": 2},
        "$set": {"updatedAt": datetime.utcnow()}
    })

    return {
        "id": str(ai_res.inserted_id),
        "role": "assistant",
        "content": rag_result["answer"],
        "sources": rag_result.get("sources", []),
        "guardrailTriggered": rag_result.get("guardrail_triggered", False),
        "guardrailDetails": rag_result.get("guardrail_details"),
        "createdAt": ai_msg_doc["createdAt"]
    }

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Deletes a chat session and its message history."""
    query = {"_id": ObjectId(session_id)} if ObjectId.is_valid(session_id) else {"_id": session_id}
    session = await db["chat_sessions"].find_one(query)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    if str(session.get("userId")) != str(current_user["id"]) and not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Access denied.")

    await db["chat_messages"].delete_many({"sessionId": str(session["_id"])})
    await db["chat_sessions"].delete_one(query)

    return {"message": "Chat session deleted successfully."}
