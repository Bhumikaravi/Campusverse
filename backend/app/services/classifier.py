import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

from app.config import settings
from app.services.category_data import INITIAL_CATEGORIES_DATA

logger = logging.getLogger("campusverse.classifier")

# Precompile taxonomy profiles from category_data
_TAXONOMY_PROFILES = []

def _init_taxonomy():
    global _TAXONOMY_PROFILES
    if _TAXONOMY_PROFILES:
        return _TAXONOMY_PROFILES
    
    profiles = []
    for cat in INITIAL_CATEGORIES_DATA:
        branch_name = cat.get("name", "")
        branch_id = cat.get("id", "")
        subcats = cat.get("subcategories", [])
        
        for sub in subcats:
            sub_name = sub.get("name", "")
            sub_desc = sub.get("description", "")
            subtopics = sub.get("subtopics", [])
            
            # Extract key terms for this branch + subject
            kw_set = set()
            for text_chunk in [branch_name, sub_name, sub_desc] + subtopics:
                words = re.findall(r"\b[a-zA-Z]{3,}\b", text_chunk.lower())
                for w in words:
                    if w not in {"and", "the", "for", "with", "from", "that", "this", "study", "notes", "material", "systems", "engineering"}:
                        kw_set.add(w)
            
            profiles.append({
                "branch": branch_name,
                "branch_id": branch_id,
                "subject": sub_name,
                "subtopics": subtopics,
                "keywords": kw_set,
                "raw_desc": f"{branch_name} {sub_name} {sub_desc} {' '.join(subtopics)}".lower()
            })
    _TAXONOMY_PROFILES = profiles
    return _TAXONOMY_PROFILES

def classify_text_rule_based(text: str, title: str = "", filename: str = "") -> Dict[str, Any]:
    """
    Analyzes document text and title against the academic taxonomy.
    Calculates weighted overlap and returns the best matching branch and subject.
    """
    clean_text = text.strip()
    words = clean_text.split()
    if len(words) < 20:
        return {
            "branch": "Unable to classify",
            "subject": "Unable to classify",
            "topics": [],
            "confidence": 0.0,
            "method": "rule_based_taxonomy",
            "explanation": "The document does not contain sufficient text to reliably identify an academic branch or subject."
        }

    profiles = _init_taxonomy()
    combined_input = f"{title} {filename} {clean_text[:12000]}".lower()
    input_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", combined_input))

    best_profile = None
    best_score = 0.0
    matched_topics = []

    for prof in profiles:
        overlap = prof["keywords"].intersection(input_tokens)
        score = len(overlap) * 1.5
        
        # Subtopic exact/partial matches get extra weight
        sub_matches = []
        for topic in prof["subtopics"]:
            t_clean = topic.lower()
            if t_clean in combined_input:
                score += 5.0
                sub_matches.append(topic)
            else:
                t_words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", t_clean) if len(w) > 3]
                if t_words and all(w in input_tokens for w in t_words):
                    score += 3.0
                    sub_matches.append(topic)
        
        # Subject title exact mention
        if prof["subject"].lower() in combined_input:
            score += 8.0
        
        # Branch title exact mention
        if prof["branch"].lower() in combined_input:
            score += 3.0

        if score > best_score:
            best_score = score
            best_profile = prof
            matched_topics = sub_matches

    if not best_profile or best_score < 4.0:
        return {
            "branch": "Unable to classify",
            "subject": "Unable to classify",
            "topics": [],
            "confidence": 0.0,
            "method": "rule_based_taxonomy",
            "explanation": "No distinct academic branch or subject keywords matched the document content."
        }

    # Normalize confidence between 0.40 and 0.95
    confidence = min(0.95, round(0.35 + (best_score / (best_score + 15.0)) * 0.60, 2))

    topics = list(dict.fromkeys(matched_topics))[:4]
    if not topics and best_profile["subtopics"]:
        topics = best_profile["subtopics"][:3]

    return {
        "branch": best_profile["branch"],
        "subject": best_profile["subject"],
        "topics": topics,
        "confidence": confidence,
        "method": "rule_based_taxonomy",
        "explanation": f"Classified under {best_profile['branch']} -> {best_profile['subject']} based on technical terminology and keyword matches."
    }

async def call_gemini_classification(text: str, title: str = "", filename: str = "") -> Optional[Dict[str, Any]]:
    """Calls Gemini API for zero-shot / few-shot academic classification."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    sample_text = text[:8000]

    system_instruction = (
        "You are an academic classifier for college and university notes. "
        "Analyze the provided document title, filename, and excerpt. "
        "Classify the document into its most likely academic Branch (Department), Subject, and key Topics. "
        "CRITICAL: If the document lacks sufficient academic content, gibberish, or is too short to determine, "
        "set branch to 'Unable to classify', subject to 'Unable to classify', confidence to 0.0, and topics to empty list. "
        "Do NOT invent or guess a subject if the text does not substantiate it. "
        "Return strictly valid JSON with keys: branch (string), subject (string), topics (list of strings), confidence (float between 0.0 and 1.0), explanation (string)."
    )

    user_prompt = f"Document Title: {title}\nFilename: {filename}\nContent:\n{sample_text}"

    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "maxOutputTokens": 400,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                clean_json = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
                parsed["method"] = "gemini_ai"
                if "confidence" in parsed:
                    parsed["confidence"] = round(float(parsed["confidence"]), 2)
                return parsed
    except Exception as e:
        logger.warning("Gemini classification failed or timed out: %s", e)
    
    return None

async def classify_document_content(text: str, title: str = "", filename: str = "") -> Dict[str, Any]:
    """
    Main classification function.
    Tries Gemini AI if available; falls back to rule-based taxonomy classifier.
    """
    if settings.GEMINI_API_KEY and len(text.strip().split()) >= 15:
        gemini_res = await call_gemini_classification(text, title, filename)
        if gemini_res and gemini_res.get("branch"):
            return gemini_res

    return classify_text_rule_based(text, title, filename)
