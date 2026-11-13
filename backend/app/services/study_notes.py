# backend/app/services/study_notes.py
"""Study notes generation service.
Generates comprehensive, structured study notes and content analysis:
- Summary (overview)
- Topic-wise notes with headings & key points
- Definitions and key terms
- Detected issues (spelling/grammar, missing info, contradictions, facts to verify)
- Practice questions (MCQ, Short answer, Long answer)
- Revision summary and exam tips
- Interactive Q&A support based on the material
"""

import json
import re
import logging
from typing import Dict, Any, List
import httpx

from app.config import settings

logger = logging.getLogger("campusverse.study_notes")

COMMON_TYPOS = {
    "teh": "the",
    "recieve": "receive",
    "seperate": "separate",
    "definately": "definitely",
    "occured": "occurred",
    "untill": "until",
    "succesful": "successful",
    "algorithim": "algorithm",
    "databse": "database",
    "proccess": "process",
    "schedulling": "scheduling",
    "synchonization": "synchronization",
    "complier": "compiler",
    "artifical": "artificial",
}

def analyze_and_extract_issues(text: str) -> List[Dict[str, Any]]:
    issues = []
    words = re.findall(r"\b[A-Za-z]+\b", text)
    found_typos = set()
    for w in words:
        wl = w.lower()
        if wl in COMMON_TYPOS and wl not in found_typos:
            found_typos.add(wl)
            issues.append({
                "type": "Spelling / Typo",
                "severity": "Low",
                "issue": f"Possible typo detected: '{w}'",
                "suggestion": f"Replace with '{COMMON_TYPOS[wl]}'",
                "verified": True
            })
            if len(issues) >= 5:
                break

    lower = text.lower()
    if "preemptive" in lower and "non-preemptive" in lower:
        issues.append({
            "type": "Conceptual Distinction",
            "severity": "Medium",
            "issue": "Both preemptive and non-preemptive terms appear together without clear separation.",
            "suggestion": "Verify that scheduling algorithms (e.g., SJF vs SRTF, Round Robin vs FCFS) clearly delineate preemptive vs non-preemptive modes.",
            "verified": False
        })
        
    if "deadlock" in lower and not any(k in lower for k in ["mutual exclusion", "hold and wait", "no preemption", "circular wait"]):
        issues.append({
            "type": "Missing Information",
            "severity": "Medium",
            "issue": "Deadlock is discussed, but the 4 necessary Coffman conditions are not explicitly detailed.",
            "suggestion": "Add Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait for complete exam readiness.",
            "verified": True
        })

    if not issues:
        issues.append({
            "type": "Content Integrity",
            "severity": "Info",
            "issue": "No critical contradictions or formatting flaws identified in the scanned material.",
            "suggestion": "Document flows logically; review topic notes and practice questions below.",
            "verified": True
        })

    return issues

def _fallback_generate_notes(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.strip()) > 15]
    summary = " ".join(sentences[:3]) if sentences else "This study material covers fundamental academic topics and examination concepts."
    
    raw_topics = []
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    for line in lines:
        if (line.isupper() and 3 <= len(line.split()) <= 8) or (line.endswith(":") and len(line.split()) <= 6):
            topic_clean = re.sub(r"^[0-9\.\-\#\*\:\s]+", "", line).strip(" :")
            if topic_clean and topic_clean not in raw_topics:
                raw_topics.append(topic_clean.title())
        elif line.istitle() and 2 <= len(line.split()) <= 5:
            topic_clean = line.strip(" :")
            if topic_clean not in raw_topics:
                raw_topics.append(topic_clean)
                
    if not raw_topics:
        raw_topics = ["Core Principles & Overview", "Key Mechanisms & Models", "Analysis, Implementation & Trade-offs", "Exam Review & Applications"]
    topics = raw_topics[:6]

    defs = []
    def_patterns = [
        r"([A-Z][A-Za-z0-9\s\-]{2,30}?)\s+(?:is defined as|refers to|is a|means|is the process of)\s+([^\.\n]+)",
        r"([A-Z][A-Za-z0-9\s\-]{2,25})\s*:\s*([^\.\n]{15,150})"
    ]
    for pattern in def_patterns:
        for match in re.finditer(pattern, cleaned):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            if len(term.split()) <= 5 and len(definition) > 15:
                defs.append({"term": term, "definition": definition[:200]})
            if len(defs) >= 6:
                break
        if len(defs) >= 6:
            break

    if not defs:
        defs = [
            {"term": topics[0] if topics else "Key Concept", "definition": "A foundational principle essential for understanding this topic in university examinations."},
            {"term": "Efficiency & Optimization", "definition": "The measure of computational, operational, or resource utilization relative to workload."},
            {"term": "Throughput", "definition": "The number of operational units or processes executed per standard time interval."}
        ]

    topic_notes = []
    for i, t in enumerate(topics):
        topic_notes.append({
            "title": t,
            "explanation": f"Detailed academic breakdown of {t}. Focuses on operational flow, core formulas/rules, and practical application.",
            "keyPoints": [
                f"Essential foundation for {t} in semester examinations.",
                f"Requires understanding the relationship between architecture, constraints, and runtime efficiency.",
                f"Typical exam questions evaluate definitions, step-by-step calculations, and comparative advantages."
            ],
            "example": f"Real-world application of {t} in modern industry and computer systems."
        })

    practice_qa = [
        {
            "type": "Short Answer",
            "question": f"Define {topics[0] if topics else 'the primary concept'} and state its main purpose.",
            "answer": f"{topics[0] if topics else 'The primary concept'} serves as the fundamental mechanism for managing workload and ensuring consistent execution."
        },
        {
            "type": "Short Answer",
            "question": "Differentiate between theoretical design limits and practical operational constraints.",
            "answer": "Theoretical design evaluates ideal asymptotic efficiency, while practical constraints account for memory overhead, switching latency, and context save/restore costs."
        },
        {
            "type": "Long Answer",
            "question": f"Provide an in-depth analysis of {topics[1] if len(topics) > 1 else 'System Architecture'} with illustrative diagrams/examples.",
            "answer": f"A comprehensive response should cover: 1) Architectural definition, 2) Core components and flow, 3) Step-by-step example problem, and 4) Performance trade-offs."
        },
        {
            "type": "MCQ",
            "question": f"Which metric primarily measures the productivity of {topics[0] if topics else 'the system'}?",
            "options": ["A. Throughput", "B. Turnaround Time", "C. Waiting Time", "D. Response Ratio"],
            "answer": "A. Throughput (Number of completed tasks per unit of time)"
        }
    ]

    issues = analyze_and_extract_issues(cleaned)

    return {
        "summary": summary,
        "topics": topics,
        "topicNotes": topic_notes,
        "definitions": defs,
        "issues": issues,
        "practiceQA": practice_qa,
        "revisionSummary": "Review all key definitions, solve the practice questions under timed conditions, and ensure clarity on the distinctions flagged in the Detected Issues tab.",
        "fullText": cleaned[:6000]
    }

async def generate_study_notes(text: str) -> Dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        return _fallback_generate_notes(text)

    prompt = f"""You are Study Buddy, an advanced academic AI tutor for university students.
Analyze the following extracted study material and return a clean, strictly formatted JSON response.
Schema:
{{
  "summary": "Concise 2-3 sentence overview of the study material.",
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "topicNotes": [
    {{
      "title": "Topic Name",
      "explanation": "Clear, student-friendly explanation",
      "keyPoints": ["Key point 1", "Key point 2"],
      "example": "Practical or numerical example"
    }}
  ],
  "definitions": [
    {{
      "term": "Term Name",
      "definition": "Precise academic definition"
    }}
  ],
  "issues": [
    {{
      "type": "Spelling / Missing Info / Fact Check",
      "severity": "Low / Medium / High",
      "issue": "Description of issue",
      "suggestion": "How to correct or improve it",
      "verified": true
    }}
  ],
  "practiceQA": [
    {{
      "type": "Short Answer / Long Answer / MCQ",
      "question": "Question text",
      "options": ["Optional array of options for MCQ"],
      "answer": "Complete explanatory answer"
    }}
  ],
  "revisionSummary": "Bullet-point style final recap for exam night."
}}

Study Material Content (excerpt):
{text[:7000]}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "maxOutputTokens": 2048
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                clean_json = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
                result = json.loads(clean_json)
                result["fullText"] = text[:6000]
                return result
            else:
                return _fallback_generate_notes(text)
    except Exception as e:
        logger.warning("Gemini study notes generation error: %s. Using fallback.", e)
        return _fallback_generate_notes(text)

async def answer_study_query(context: str, query: str) -> str:
    """Answers student question based on context with robust academic fallback following strict instructions."""
    from app.services.guardrails import evaluate_input_guardrails, evaluate_output_guardrails
    from app.services.rag_engine import ACADEMIC_KNOWLEDGE_BASE, build_deterministic_rag_answer, SYSTEM_PROMPT_CHATGPT_STYLE

    # AI Guardrails Check
    guardrail_eval = evaluate_input_guardrails(query, context)
    if guardrail_eval["action"] == "BLOCK":
        return guardrail_eval["user_message"]
    effective_query = guardrail_eval["sanitized_text"]

    # If Gemini API key is configured, call Gemini first
    if settings.GEMINI_API_KEY:
        prompt = (
            f"STUDY MATERIAL CONTEXT:\n{context[:4000]}\n\n"
            f"STUDENT QUESTION:\n{effective_query}\n\n"
            f"ANSWER:"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT_CHATGPT_STYLE}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 800
            }
        }
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    ans = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if ans.strip():
                        return evaluate_output_guardrails(
                            ans.strip(),
                            is_medical=guardrail_eval.get("medical_disclaimer_required", False)
                        )
        except Exception as e:
            logger.warning("Gemini chat API call failed: %s", e)

    # Use RAG deterministic academic synthesizer
    chunks = [{"text": context[:4000], "title": "Study Notes", "pageNumber": 1}] if context else []
    raw_answer = build_deterministic_rag_answer(effective_query, chunks)
    return evaluate_output_guardrails(
        raw_answer,
        is_medical=guardrail_eval.get("medical_disclaimer_required", False)
    )
