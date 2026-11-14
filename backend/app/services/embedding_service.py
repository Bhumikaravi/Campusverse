import re
import math
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import httpx
from bson import ObjectId

from app.config import settings
from app.database import get_db

logger = logging.getLogger("campusverse.embedding_service")

DENSE_VECTOR_DIM = 128

def _hash_token_to_dense_vector(token: str, dim: int = DENSE_VECTOR_DIM) -> np.ndarray:
    """Deterministic hash projection of a word/n-gram token into a dense vector space."""
    v = np.zeros(dim, dtype=np.float32)
    # Generate 3 distinct hash positions per token to simulate random projection
    for seed in range(3):
        h = int(hashlib.md5(f"{token}_{seed}".encode("utf-8")).hexdigest(), 16)
        pos = h % dim
        sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
        v[pos] += sign
    return v

def generate_local_embedding(text: str, dim: int = DENSE_VECTOR_DIM) -> List[float]:
    """
    Pure-numpy dense semantic vectorizer based on weighted token hashing and subword projections.
    Provides fast, offline cosine similarity without external network dependencies.
    """
    clean_text = text.lower()
    words = re.findall(r"\b[a-zA-Z]{3,}\b", clean_text)
    if not words:
        return [0.0] * dim

    vec = np.zeros(dim, dtype=np.float32)
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    total_words = len(words)
    for word, count in freq.items():
        # TF weighting with length dampening
        tf = (count / total_words) * (1.0 + math.log(1.0 + len(word)))
        t_vec = _hash_token_to_dense_vector(word, dim)
        vec += t_vec * tf

    # Also capture character trigrams for typo-tolerance and morphological similarity
    for i in range(len(clean_text) - 3):
        trigram = clean_text[i:i+3]
        if trigram.strip() and not trigram.isspace():
            h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest()[:8], 16)
            pos = h % dim
            sign = 0.2 if (h >> 4) % 2 == 0 else -0.2
            vec[pos] += sign

    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm

    return [round(float(x), 5) for x in vec]

async def call_gemini_embedding(text: str) -> Optional[List[float]]:
    """Calls Google Gemini text embedding API if API key is provided."""
    if not settings.GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text[:3000]}]}
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                vals = data.get("embedding", {}).get("values", [])
                if vals:
                    return vals
    except Exception as e:
        logger.debug("Gemini embedding notice: %s. Using local dense vectorizer.", e)

    return None

async def get_text_embedding(text: str) -> List[float]:
    """Retrieves embedding: Gemini API if key exists, otherwise deterministic local vectorizer."""
    if settings.GEMINI_API_KEY and len(text.strip().split()) >= 4:
        gem_vec = await call_gemini_embedding(text)
        if gem_vec:
            return gem_vec

    return generate_local_embedding(text)

def chunk_document_by_pages(pages_text: List[str], target_words: int = 150, overlap_words: int = 30) -> List[Dict[str, Any]]:
    """
    Partitions document text into coherent chunks, tracking exact page numbers.
    """
    chunks = []
    chunk_index = 0

    for page_idx, page_str in enumerate(pages_text):
        p_num = page_idx + 1
        clean_page = page_str.strip()
        words = clean_page.split()
        if not words:
            continue

        if len(words) <= target_words:
            chunks.append({
                "chunkIndex": chunk_index,
                "pageNumber": p_num,
                "text": clean_page,
                "wordCount": len(words)
            })
            chunk_index += 1
        else:
            # Subdivide long page
            step = max(20, target_words - overlap_words)
            for i in range(0, len(words), step):
                chunk_slice = words[i : i + target_words]
                if len(chunk_slice) >= 15:
                    chunks.append({
                        "chunkIndex": chunk_index,
                        "pageNumber": p_num,
                        "text": " ".join(chunk_slice),
                        "wordCount": len(chunk_slice)
                    })
                    chunk_index += 1

    return chunks

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

async def index_document_chunks(
    material_id: str,
    title: str,
    pages_text: List[str],
    uploader_id: str,
    status: str = "ADMIN_APPROVED"
) -> int:
    """
    Extracts chunks, computes embeddings, and stores them in the document_chunks collection.
    Avoids duplicate indexing.
    """
    db = get_db()
    if db is None:
        return 0

    # Remove existing chunks for this material before re-indexing
    await db["document_chunks"].delete_many({"materialId": str(material_id)})

    chunks = chunk_document_by_pages(pages_text)
    if not chunks:
        return 0

    now = datetime.utcnow()
    chunk_docs = []
    
    # Compute embeddings concurrently across chunks in sub-second time
    emb_tasks = [get_text_embedding(c["text"]) for c in chunks]
    embeddings = await asyncio.gather(*emb_tasks, return_exceptions=True)

    for c, emb in zip(chunks, embeddings):
        if isinstance(emb, Exception) or not emb:
            emb = generate_local_embedding(c["text"])
        chunk_docs.append({
            "materialId": str(material_id),
            "title": title,
            "pageNumber": c["pageNumber"],
            "chunkIndex": c["chunkIndex"],
            "text": c["text"],
            "wordCount": c["wordCount"],
            "embedding": emb,
            "uploader": str(uploader_id),
            "status": status,
            "createdAt": now
        })

    if chunk_docs:
        await db["document_chunks"].insert_many(chunk_docs)

    return len(chunk_docs)

async def remove_document_chunks(material_id: str):
    """Deletes stored embeddings when a document is deleted."""
    db = get_db()
    if db is not None:
        await db["document_chunks"].delete_many({"materialId": str(material_id)})

async def search_semantic_chunks(
    query_text: str,
    user_id: Optional[str] = None,
    is_admin: bool = False,
    limit: int = 8
) -> List[Dict[str, Any]]:
    """
    Converts query into embedding, performs cosine similarity search over stored chunks,
    and returns matching document references with snippet and page number.
    Restricts results to approved documents or documents uploaded by the user.
    """
    clean_q = query_text.strip()
    if not clean_q:
        return []

    db = get_db()
    if db is None:
        return []

    q_embedding = await get_text_embedding(clean_q)

    # Permission filter: ADMIN_APPROVED, AI_APPROVED, or user's own materials
    perm_filter: Dict[str, Any] = {}
    if not is_admin:
        clauses: List[Dict[str, Any]] = [
            {"status": {"$in": ["ADMIN_APPROVED", "AI_APPROVED"]}}
        ]
        if user_id:
            clauses.append({"uploader": str(user_id)})
        perm_filter = {"$or": clauses}

    cursor = db["document_chunks"].find(perm_filter)
    candidates = await cursor.to_list(length=1200)
    if not candidates:
        return []

    scored_results = []
    q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", clean_q.lower()))

    for cand in candidates:
        cand_emb = cand.get("embedding")
        if not cand_emb:
            continue
        sim = cosine_similarity(q_embedding, cand_emb)
        
        # Keyword bonus for exact search terms
        text_lower = cand.get("text", "").lower()
        keyword_hits = sum(1 for w in q_words if w in text_lower)
        bonus = min(0.15, keyword_hits * 0.05)
        combined_score = min(0.99, sim + bonus)

        if combined_score >= 0.20:
            scored_results.append({
                "materialId": cand["materialId"],
                "title": cand["title"],
                "pageNumber": cand["pageNumber"],
                "snippet": cand["text"][:300] + ("..." if len(cand["text"]) > 300 else ""),
                "fullText": cand["text"],
                "score": round(combined_score, 3)
            })

    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results[:limit]

async def check_document_similarity_and_plagiarism(
    material_id: str,
    doc_pages_text: List[str],
    current_file_hash: str = ""
) -> Dict[str, Any]:
    """
    Compares uploaded document against all existing authorized materials in the database.
    Distinguishes:
    1. Exact duplicates (file hash or exact text match)
    2. Textual similarity (shared paragraphs / exact sentence overlap)
    3. Semantic similarity (high embedding similarity across topical chunks)
    Generates structured similarity report for admin review.
    """
    db = get_db()
    if db is None:
        return {
            "isDuplicate": False,
            "overallSimilarityScore": 0.0,
            "similarityType": "None",
            "matches": [],
            "checkedAgainstCount": 0,
            "explanation": "No existing documents available for comparison."
        }

    # 1. Exact SHA-256 duplicate check
    if current_file_hash:
        exact_dup = await db["materials"].find_one({
            "_id": {"$ne": ObjectId(material_id) if ObjectId.is_valid(material_id) else material_id},
            "fileHash": current_file_hash,
            "status": {"$nin": ["REJECTED", "ADMIN_REJECTED"]}
        })
        if exact_dup:
            return {
                "isDuplicate": True,
                "overallSimilarityScore": 1.0,
                "similarityType": "Exact File Duplicate",
                "matches": [{
                    "targetMaterialId": str(exact_dup["_id"]),
                    "targetTitle": exact_dup.get("title", "Existing Note"),
                    "similarityScore": 1.0,
                    "similarityType": "Exact SHA-256 Duplicate",
                    "matchingPassages": [{"page": 1, "text": "Entire file content is binary identical."}]
                }],
                "checkedAgainstCount": 1,
                "explanation": "Exact identical file detected using SHA-256 cryptographic fingerprint."
            }

    # 2. Chunk-based semantic & textual overlap check
    incoming_chunks = chunk_document_by_pages(doc_pages_text)
    if not incoming_chunks:
        return {
            "isDuplicate": False,
            "overallSimilarityScore": 0.0,
            "similarityType": "None",
            "matches": [],
            "checkedAgainstCount": 0,
            "explanation": "Uploaded document has insufficient text for similarity analysis."
        }

    # Query all chunks from other materials
    other_chunks_cursor = db["document_chunks"].find({
        "materialId": {"$ne": str(material_id)},
        "status": {"$in": ["ADMIN_APPROVED", "AI_APPROVED"]}
    })
    target_chunks = await other_chunks_cursor.to_list(length=3000)

    if not target_chunks:
        return {
            "isDuplicate": False,
            "overallSimilarityScore": 0.0,
            "similarityType": "None",
            "matches": [],
            "checkedAgainstCount": 0,
            "explanation": "Document verified against authorized dataset. No existing approved documents found to compare."
        }

    # Compare incoming chunks against target chunks
    material_match_map: Dict[str, Dict[str, Any]] = {}
    distinct_target_materials = set()

    for in_c in incoming_chunks[:25]:  # compare first 25 chunks for speed
        in_emb = await get_text_embedding(in_c["text"])
        in_norm_text = in_c["text"].lower().strip()

        for t_c in target_chunks:
            target_mat_id = t_c["materialId"]
            distinct_target_materials.add(target_mat_id)
            target_emb = t_c.get("embedding")
            if not target_emb:
                continue

            sim = cosine_similarity(in_emb, target_emb)
            target_norm_text = t_c.get("text", "").lower().strip()

            # Check if exact passage match
            is_exact_passage = in_norm_text == target_norm_text
            # Check text word overlap
            in_words = set(in_norm_text.split())
            t_words = set(target_norm_text.split())
            jaccard = len(in_words.intersection(t_words)) / max(1, len(in_words.union(t_words)))

            passage_type = "Semantic Similarity"
            if is_exact_passage or jaccard > 0.85:
                passage_type = "Exact Text Match"
            elif jaccard > 0.50:
                passage_type = "High Textual Similarity"

            if sim >= 0.70 or jaccard >= 0.50:
                if target_mat_id not in material_match_map:
                    material_match_map[target_mat_id] = {
                        "targetMaterialId": target_mat_id,
                        "targetTitle": t_c.get("title", "Study Material"),
                        "maxScore": 0.0,
                        "highSimChunks": 0,
                        "passages": []
                    }
                
                entry = material_match_map[target_mat_id]
                effective_score = max(sim, jaccard)
                if effective_score > entry["maxScore"]:
                    entry["maxScore"] = effective_score
                entry["highSimChunks"] += 1
                
                if len(entry["passages"]) < 4:
                    entry["passages"].append({
                        "sourcePage": in_c["pageNumber"],
                        "targetPage": t_c["pageNumber"],
                        "sourceSnippet": in_c["text"][:180],
                        "targetSnippet": t_c["text"][:180],
                        "similarityScore": round(float(effective_score), 2),
                        "passageType": passage_type
                    })

    # Compile match results
    matches = []
    overall_max_score = 0.0
    overall_type = "Unique Content"

    for mat_id, data in material_match_map.items():
        score = round(data["maxScore"], 2)
        if score > overall_max_score:
            overall_max_score = score
        
        # Classification of similarity
        if any(p["passageType"] == "Exact Text Match" for p in data["passages"]):
            t = "Textual Match"
        elif score >= 0.85:
            t = "High Semantic Similarity"
        else:
            t = "Moderate Semantic Overlap"

        matches.append({
            "targetMaterialId": mat_id,
            "targetTitle": data["targetTitle"],
            "similarityScore": score,
            "similarityType": t,
            "matchingPassages": data["passages"]
        })

    matches.sort(key=lambda x: x["similarityScore"], reverse=True)

    if overall_max_score >= 0.90:
        overall_type = "Potential Exact Duplicate / Re-upload"
        explanation = "High proportion of passages or file structures strongly match an existing note in the repository. Staff inspection recommended."
    elif overall_max_score >= 0.75:
        overall_type = "High Semantic / Textual Overlap"
        explanation = "Document shares notable theoretical content and phrasing with existing authorized notes. May represent overlapping syllabus coverage."
    elif overall_max_score >= 0.50:
        overall_type = "Moderate Topical Commonality"
        explanation = "Notes discuss related curriculum topics with low overlap in specific formulations."
    else:
        overall_type = "Unique Document"
        explanation = "No significant similarity found against authorized study materials."

    return {
        "isDuplicate": overall_max_score >= 0.90,
        "overallSimilarityScore": round(overall_max_score, 2),
        "similarityPercentage": f"{int(overall_max_score * 100)}%",
        "similarityType": overall_type,
        "matches": matches[:5],
        "checkedAgainstCount": len(distinct_target_materials),
        "explanation": explanation
    }
