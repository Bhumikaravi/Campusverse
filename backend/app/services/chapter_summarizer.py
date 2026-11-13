import re
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings
from app.services.document_summarizer import extract_key_statements, split_into_semantic_units

logger = logging.getLogger("campusverse.chapter_summarizer")

def detect_chapter_boundaries(pages_text: List[str]) -> List[Dict[str, Any]]:
    """
    Scans pages in order to detect chapter/unit/module headings.
    If none are found, splits the document into logical sections.
    """
    chapter_markers = []
    
    # Heading regex patterns
    ch_regex = re.compile(
        r"^(?:(?:chapter|unit|module|section|part)\s+([0-9ivxlcdm]+)[:.\s\-–—]*([^\n]*)|([0-9]{1,2}\.[0-9]{0,2}\s+[A-Z][^\n]{3,60}))",
        re.IGNORECASE | re.MULTILINE
    )

    for p_idx, page_content in enumerate(pages_text):
        p_num = p_idx + 1
        lines = page_content.splitlines()
        for l_idx, line in enumerate(lines[:12]):  # Top of page is most likely for headings
            cleaned_line = line.strip()
            if not cleaned_line:
                continue
            
            # Check for Chapter/Unit/Module
            m = ch_regex.match(cleaned_line)
            if m:
                num = m.group(1) or ""
                title_part = (m.group(2) or m.group(3) or "").strip()
                if not title_part and l_idx + 1 < len(lines):
                    next_line = lines[l_idx + 1].strip()
                    if next_line and len(next_line.split()) <= 10:
                        title_part = next_line
                
                ch_title = f"Chapter {num}: {title_part}" if num else title_part
                chapter_markers.append({
                    "title": ch_title.strip(": -–—"),
                    "startPage": p_num,
                    "line": cleaned_line
                })
                break  # Max one chapter start per page

    # If no chapters or only 1 detected for multi-page, partition into logical sections
    total_pages = len(pages_text)
    if len(chapter_markers) <= 1 and total_pages > 1:
        chapter_markers = []
        pages_per_section = max(2, min(5, total_pages // 3 or 1))
        sec_num = 1
        for start in range(0, total_pages, pages_per_section):
            end = min(total_pages, start + pages_per_section)
            # Find a representative title from the first page of this section
            first_page = pages_text[start]
            lines = [l.strip() for l in first_page.splitlines() if len(l.strip().split()) in range(2, 9) and not l.strip().isdigit()]
            candidate_title = lines[0] if lines else f"Core Topics (Pages {start+1}-{end})"
            candidate_title = re.sub(r"^[#\*\-\d\.\)]+\s*", "", candidate_title).strip()
            
            chapter_markers.append({
                "title": f"Section {sec_num}: {candidate_title[:50]}",
                "startPage": start + 1,
            })
            sec_num += 1

    if not chapter_markers:
        chapter_markers = [{
            "title": "Comprehensive Notes",
            "startPage": 1
        }]

    # Assign page ranges and slices
    chapters = []
    for idx, mark in enumerate(chapter_markers):
        start_p = mark["startPage"]
        end_p = chapter_markers[idx + 1]["startPage"] - 1 if idx + 1 < len(chapter_markers) else total_pages
        end_p = max(start_p, end_p)
        
        # Collect text of these pages
        ch_text_pages = pages_text[start_p - 1 : end_p]
        ch_text = "\n\n".join(ch_text_pages).strip()
        
        chapters.append({
            "chapterNumber": idx + 1,
            "title": mark["title"],
            "startPage": start_p,
            "endPage": end_p,
            "text": ch_text
        })

    return chapters

def extract_chapter_formulas(text: str) -> List[str]:
    """Extracts explicit mathematical formulas, equations, and complexity bounds."""
    formulas = []
    lines = text.splitlines()
    formula_regex = re.compile(r"([A-Za-z0-9_'\(\)]+\s*=\s*[^,\n;]+(?:[+\-*/^√∑∫π\w\s\(\)]+))")
    complexity_regex = re.compile(r"\bO\([n1klog\s\+\*\^]+\)")

    for line in lines:
        s = line.strip()
        if not s or len(s.split()) > 30:
            continue
        # Math symbols or equation signs
        if any(sym in s for sym in [" = ", " == ", " ≈ ", " <= ", " >= ", "∑", "∫", " -> ", " \times "]):
            if len(s) < 120 and s not in formulas:
                formulas.append(s)
        elif complexity_regex.search(s):
            if s not in formulas and len(s) < 100:
                formulas.append(s)

    return formulas[:8]

def extract_chapter_definitions(text: str) -> List[Dict[str, str]]:
    """Extracts precise term-definition pairs from academic content."""
    definitions = []
    units = split_into_semantic_units(text)
    
    # Pattern 1: "Term is defined as..." or "Term refers to..."
    def_regex = re.compile(r"\b([A-Z][a-zA-Z\s]{1,30})\s+(?:is defined as|refers to|is known as|is the process of|consists of)\s+([^\n.]+)", re.IGNORECASE)
    # Pattern 2: "Term: Explanation..."
    colon_regex = re.compile(r"^([A-Z][a-zA-Z\s]{2,25}):\s+([A-Z][^\n.]+)")

    for u in units:
        m = def_regex.search(u)
        if m:
            term = m.group(1).strip()
            meaning = (u[m.start():].strip()).rstrip(".") + "."
            if len(term.split()) <= 4 and term.lower() not in {"this", "it", "which", "there"}:
                definitions.append({"term": term.title(), "definition": meaning})
                continue
        
        m2 = colon_regex.match(u)
        if m2:
            term = m2.group(1).strip()
            meaning = m2.group(2).strip() + "."
            if len(term.split()) <= 4:
                definitions.append({"term": term.title(), "definition": meaning})

    # Deduplicate by term
    seen = set()
    deduped = []
    for d in definitions:
        t_key = d["term"].lower()
        if t_key not in seen:
            seen.add(t_key)
            deduped.append(d)
    return deduped[:6]

def extract_chapter_key_concepts(text: str, max_count: int = 6) -> List[str]:
    """Identifies prominent technical concepts, frameworks, and subject keywords."""
    words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
    stopwords = {"Chapter", "Section", "Page", "University", "Figure", "Table", "Author", "Student", "Lecture", "The", "This", "These", "Note", "Notes"}
    
    freq = {}
    for w in words:
        clean = w.strip()
        if clean not in stopwords and len(clean) > 3 and len(clean.split()) <= 3:
            freq[clean] = freq.get(clean, 0) + 1
            
    sorted_concepts = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [c[0] for c in sorted_concepts[:max_count]]

def summarize_chapter_deterministic(ch: Dict[str, Any], subject: str = "") -> Dict[str, Any]:
    """Generates structured chapter summary with bullet points, concepts, definitions, and formulas."""
    text = ch["text"]
    units = split_into_semantic_units(text)
    
    summary_bullets = []
    for u in units:
        if len(summary_bullets) >= 5:
            break
        # Pick sentences that express definitions, principles, or summaries
        if any(w in u.lower() for w in ["principle", "meaning", "used to", "allows", "important", "architecture", "consists", "algorithm", "primary", "mechanism", "technique"]):
            bullet = u.strip()
            if not bullet.endswith((".", "!", "?")):
                bullet += "."
            if bullet not in summary_bullets:
                summary_bullets.append(bullet)
                
    if not summary_bullets:
        for u in units[:4]:
            bullet = u.strip()
            if not bullet.endswith((".", "!", "?")):
                bullet += "."
            summary_bullets.append(bullet)

    key_concepts = extract_chapter_key_concepts(text)
    definitions = extract_chapter_definitions(text)
    formulas = extract_chapter_formulas(text)

    return {
        "chapterNumber": ch["chapterNumber"],
        "title": ch["title"],
        "startPage": ch["startPage"],
        "endPage": ch["endPage"],
        "summary": summary_bullets or ["Comprehensive academic coverage of the topic."],
        "keyConcepts": key_concepts,
        "importantDefinitions": definitions,
        "importantFormulas": formulas
    }

async def call_gemini_chapter_summary(ch: Dict[str, Any], subject: str = "") -> Optional[Dict[str, Any]]:
    """Calls Gemini to produce grounded, high-fidelity chapter summary."""
    if not settings.GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    prompt = (
        f"You are the CampusVerse Academic Chapter Summarizer.\n"
        f"Subject: {subject}\n"
        f"Chapter: {ch['title']} (Pages {ch['startPage']}-{ch['endPage']})\n\n"
        f"INSTRUCTIONS:\n"
        f"Based STRICTLY and EXCLUSIVELY on the provided chapter text:\n"
        f"1. Generate 3 to 5 concise bullet-point summary items.\n"
        f"2. Extract 4 to 6 important Key Concepts / Topics.\n"
        f"3. Extract 2 to 4 Important Definitions with 'term' and 'definition'.\n"
        f"4. Extract any Important Formulas (equations, Big-O complexity, math expressions in LaTeX notation). If none exist, return an empty array.\n"
        f"Do NOT invent facts outside the text.\n\n"
        f"Return STRICTLY a JSON object with keys: summary (list of strings), keyConcepts (list of strings), importantDefinitions (list of objects with term and definition), importantFormulas (list of strings).\n\n"
        f"CHAPTER TEXT:\n{ch['text'][:12000]}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "maxOutputTokens": 800,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                clean_json = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
                return {
                    "chapterNumber": ch["chapterNumber"],
                    "title": ch["title"],
                    "startPage": ch["startPage"],
                    "endPage": ch["endPage"],
                    "summary": parsed.get("summary", []),
                    "keyConcepts": parsed.get("keyConcepts", []),
                    "importantDefinitions": parsed.get("importantDefinitions", []),
                    "importantFormulas": parsed.get("importantFormulas", [])
                }
    except Exception as e:
        logger.warning("Gemini chapter summarization notice for %s: %s", ch['title'], e)
    return None

async def generate_document_chapter_summaries(
    document_id: str,
    title: str,
    pages_text: List[str],
    subject: str = ""
) -> Dict[str, Any]:
    """
    Main orchestrator for generating chapter-wise summaries, key concepts,
    important definitions, and formulas across all pages of a document.
    """
    chapters = detect_chapter_boundaries(pages_text)
    summarized_chapters = []

    for ch in chapters:
        # Check if Gemini key is available
        if settings.GEMINI_API_KEY and len(ch["text"].split()) >= 30:
            gem_res = await call_gemini_chapter_summary(ch, subject=subject)
            if gem_res:
                summarized_chapters.append(gem_res)
                continue

        # Fallback deterministic extractor
        ch_res = summarize_chapter_deterministic(ch, subject=subject)
        summarized_chapters.append(ch_res)

    return {
        "documentId": document_id,
        "title": title,
        "subject": subject,
        "totalChapters": len(summarized_chapters),
        "chapters": summarized_chapters
    }
