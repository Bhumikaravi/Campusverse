"""AI Scanning Booth Service.
Performs comprehensive document review:
1. Spelling & Grammar Analysis
2. Academic Content & Factual Consistency Review
3. Quality & Formatting Evaluation (OCR errors, inconsistent headers, blanks, duplicate text)
4. Category & Subcategory Prediction
5. Corrected text generation (allowing selective corrections)
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger("campusverse.scanning_booth")

# Standard Engineering and Academic taxonomy knowledge
ENGINEERING_TAXONOMY = {
    "Civil Engineering": [
        "Structural Engineering", "Construction Technology", "Geotechnical Engineering",
        "Transportation Engineering", "Environmental Engineering", "Surveying", "Building Materials"
    ],
    "Mechanical Engineering": [
        "Thermodynamics", "Manufacturing Technology", "Machine Design",
        "Fluid Mechanics", "Engineering Mechanics", "CAD/CAM"
    ],
    "Computer Science Engineering": [
        "Artificial Intelligence and Machine Learning", "Data Structures and Algorithms",
        "Database Management Systems", "Operating Systems", "Computer Networks",
        "Web Development", "Software Engineering", "Cybersecurity"
    ],
    "Electrical Engineering": [
        "Electrical Machines", "Power Systems", "Control Systems",
        "Electrical Circuits", "Power Electronics"
    ],
    "Electronics and Communication Engineering": [
        "Digital Electronics", "Analog Electronics", "Communication Systems",
        "Microprocessors and Microcontrollers", "Embedded Systems", "Signal Processing"
    ],
    "Biomedical Engineering": [
        "Medical Instrumentation", "Biomedical Signal Processing", "Medical Imaging",
        "Biomechanics", "Clinical Engineering"
    ],
    "Chemical Engineering": [
        "Chemical Process Engineering", "Heat and Mass Transfer",
        "Reaction Engineering", "Process Control"
    ],
    "Aerospace Engineering": [
        "Aerodynamics", "Flight Mechanics", "Aircraft Structures", "Propulsion Systems"
    ]
}

# Domain keywords for deterministic classification across all academic faculties
FACULTY_KEYWORDS = {
    ("General Medicine", "Cardiovascular Medicine"): ["hypertension", "systolic", "diastolic", "blood pressure", "coronary artery", "heart failure", "ecg", "electrocardiogram", "myocardial", "arrhythmia", "stemi"],
    ("General Medicine", "Clinical Medicine"): ["patient history", "physical examination", "vital signs", "clinical diagnosis", "auscultation", "chief complaint", "socrates"],
    ("General Medicine", "Respiratory Medicine"): ["asthma", "copd", "pneumonia", "tuberculosis", "spirometry", "bronchodilator", "fev1", "pulmonary"],
    ("General Medicine", "Endocrinology"): ["diabetes mellitus", "insulin", "glucose", "hba1c", "ketoacidosis", "thyroid", "endocrine"],
    ("General Medicine", "Infectious Diseases"): ["malaria", "dengue", "plasmodium", "fever", "antimicrobial", "antibiotic resistance", "pathogen"],
    ("General Medicine", "Gastroenterology"): ["gastritis", "peptic ulcer", "gerd", "helicobacter", "hepatitis", "cirrhosis", "gastrointestinal"],
    ("General Medicine", "Renal Medicine"): ["acute kidney injury", "nephron", "creatinine", "gfr", "chronic kidney disease", "electrolyte", "dialysis"],
    ("General Medicine", "Emergency and Preventive Medicine"): ["triage", "basic life support", "cpr", "emergency assessment", "first-aid", "vaccination", "immunization"],
    
    ("Computer Science and Engineering", "Data Structures and Algorithms"): ["algorithm", "data structure", "binary tree", "bst", "avl tree", "red-black tree", "graph algorithm", "bfs", "dfs", "dijkstra", "dynamic programming"],
    ("Computer Science and Engineering", "Database Management Systems"): ["dbms", "sql", "normalization", "1nf", "2nf", "3nf", "bcnf", "relational algebra", "acid", "transaction management"],
    ("Computer Science and Engineering", "Operating Systems"): ["operating system", "cpu scheduling", "fcfs", "shortest job", "round robin", "deadlock", "banker", "paging", "virtual memory"],
    ("Computer Science and Engineering", "Computer Networks"): ["computer networks", "osi model", "tcp/ip", "packet encapsulation", "subnetting", "transport layer", "routing"],
    ("Computer Science and Engineering", "Cybersecurity"): ["cybersecurity", "cryptography", "rsa", "public key", "aes", "diffie-hellman", "penetration testing", "owasp"],
    ("Computer Science and Engineering", "Artificial Intelligence"): ["artificial intelligence", "search heuristics", "a* search", "minimax", "knowledge representation", "propositional logic"],
    ("Computer Science and Engineering", "Machine Learning"): ["machine learning", "gradient descent", "linear regression", "logistic regression", "neural network", "deep learning"],
    
    ("Civil Engineering", "Structural Engineering"): ["structural analysis", "reinforced concrete", "rcc", "beam design", "bending moment", "shear force", "stirrups", "is 456"],
    ("Civil Engineering", "Geotechnical Engineering"): ["geotechnical", "soil mechanics", "mohr-coulomb", "shear strength", "triaxial", "bearing capacity", "foundation engineering"],
    ("Civil Engineering", "Transportation Engineering"): ["transportation", "highway geometric", "pavement design", "traffic engineering", "cbr", "super-elevation"],
    ("Civil Engineering", "Surveying"): ["surveying", "total station", "theodolite", "gps mapping", "gis", "traverse", "levelling"],
    ("Civil Engineering", "Building Materials"): ["concrete mix", "portland cement", "aggregate", "slump test", "compressive strength", "building materials"],
    ("Civil Engineering", "Fluid Mechanics"): ["fluid statics", "bernoulli", "pipe flow", "darcy-weisbach", "hydraulic grade", "open channel"],
    
    ("Mechanical Engineering", "Thermodynamics"): ["thermodynamics", "rankine cycle", "carnot", "first law", "second law", "entropy", "exergy", "steam turbine"],
    ("Mechanical Engineering", "Fluid Mechanics"): ["navier-stokes", "boundary layer", "prandtl", "flow separation", "form drag", "fluid dynamics"],
    ("Mechanical Engineering", "Machine Design"): ["machine design", "spur gear", "helical gear", "lewis equation", "bearing", "fatigue failure"],
    ("Mechanical Engineering", "Manufacturing Processes"): ["manufacturing", "cnc machining", "metal casting", "merchant circle", "tool wear", "welding"],
    ("Mechanical Engineering", "Strength of Materials"): ["strength of materials", "principal stresses", "mohr's circle", "hooke's law", "beam bending", "torsion"],
    
    ("Electrical and Electronics Engineering", "Electrical Machines"): ["induction motor", "transformer", "synchronous generator", "torque-slip", "equivalent circuit", "stator"],
    ("Electrical and Electronics Engineering", "Power Systems"): ["power systems", "fault analysis", "symmetrical components", "transmission line", "swing equation", "load flow"],
    ("Electrical and Electronics Engineering", "Control Systems"): ["control systems", "root locus", "bode plot", "transfer function", "gain margin", "phase margin"],
    ("Electrical and Electronics Engineering", "Digital Electronics"): ["digital electronics", "boolean algebra", "k-map", "multiplexer", "flip-flop", "fpga", "vhdl"],
    
    ("Business and Management", "Finance & Accounting"): ["capital budgeting", "net present value", "npv", "internal rate of return", "irr", "wacc", "corporate finance", "capm"],
    ("Law", "Constitutional & Administrative Law"): ["constitutional law", "fundamental rights", "article 14", "article 19", "article 21", "judicial review", "writ petition", "habeas corpus", "mandamus"]
}

COMMON_SPELLING_MISTAKES = {
    "teh": ("the", "Typo in common definite article"),
    "recieve": ("receive", "Rule: 'i' before 'e' except after 'c'"),
    "seperate": ("separate", "Common vowel confusion ('a' not 'e')"),
    "definately": ("definitely", "Spelling error in adverb"),
    "occured": ("occurred", "Double 'r' required in past tense"),
    "untill": ("until", "Single 'l' in modern standard English"),
    "succesful": ("successful", "Double 'c' and double 's' required"),
    "algorithim": ("algorithm", "Technical misspelling of algorithm"),
    "databse": ("database", "Missing 'a' in technical compound word"),
    "proccess": ("process", "Single 'c' required"),
    "schedulling": ("scheduling", "Single 'l' in scheduling"),
    "synchonization": ("synchronization", "Missing 'r' in synchronization"),
    "complier": ("compiler", "Inverted letters in technical term"),
    "artifical": ("artificial", "Missing second 'i'"),
    "lenght": ("length", "Transposed 'th'"),
    "heigth": ("height", "Spelling confusion with length"),
    "preformance": ("performance", "Transposed prefix letters"),
}

def deterministic_scan(text: str, selected_main: str = "Engineering", selected_sub: Optional[str] = None) -> Dict[str, Any]:
    """Fast, reliable heuristic scan for spelling, academic checks, formatting, and category matching."""
    cleaned = text.strip()
    words = re.findall(r"\b[A-Za-z]+\b", cleaned)
    total_words = len(words)
    
    issues: List[Dict[str, Any]] = []
    issue_counter = 1

    # 1. Spelling and Typo Detection
    found_typos = set()
    for w in words:
        wl = w.lower()
        if wl in COMMON_SPELLING_MISTAKES and wl not in found_typos:
            found_typos.add(wl)
            correct, reason = COMMON_SPELLING_MISTAKES[wl]
            rep = correct.capitalize() if w[0].isupper() else correct
            issues.append({
                "id": f"iss-{issue_counter}",
                "category": "Spelling",
                "page": 1,
                "original": w,
                "suggestion": rep,
                "reason": reason,
                "confidence": 0.95,
                "status": "pending"
            })
            issue_counter += 1
            if len(issues) >= 8:
                break

    # 2. Grammar & Style checks
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    for s in sentences:
        s_clean = s.strip()
        if re.search(r"\b(is|are|was|were)\s+(increased|decreased|found)\s+by\s+the\s+because\b", s_clean, re.I):
            issues.append({
                "id": f"iss-{issue_counter}",
                "category": "Grammar",
                "page": 1,
                "original": s_clean[:80] + "...",
                "suggestion": re.sub(r"by\s+the\s+because", "because", s_clean)[:80] + "...",
                "reason": "Redundant preposition combination before causal clause",
                "confidence": 0.88,
                "status": "pending"
            })
            issue_counter += 1
            break

    # 3. Academic Content & Contradiction Review
    lower_text = cleaned.lower()
    if "first-come first-served" in lower_text or "fcfs" in lower_text:
        if "preemptive" in lower_text and not "non-preemptive" in lower_text:
            issues.append({
                "id": f"iss-{issue_counter}",
                "category": "Academic Review",
                "page": 1,
                "original": "FCFS algorithm description",
                "suggestion": "Clarify that standard FCFS is strictly a Non-Preemptive scheduling algorithm.",
                "reason": "Potentially inaccurate explanation: FCFS is non-preemptive by definition.",
                "confidence": 0.92,
                "status": "pending"
            })
            issue_counter += 1

    if "deadlock" in lower_text and not any(k in lower_text for k in ["mutual exclusion", "hold and wait", "circular wait", "no preemption"]):
        issues.append({
            "id": f"iss-{issue_counter}",
            "category": "Academic Review",
            "page": 1,
            "original": "Deadlock explanation section",
            "suggestion": "Include all 4 Coffman necessary conditions (Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait).",
            "reason": "Important missing foundational criteria required for complete university exam answers.",
            "confidence": 0.85,
            "status": "pending"
        })
        issue_counter += 1

    # 4. Quality & Formatting Review
    duplicate_paragraphs = 0
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if len(p.strip()) > 60]
    seen_paras = set()
    for p in paragraphs:
        p_sub = p[:100]
        if p_sub in seen_paras:
            duplicate_paragraphs += 1
            issues.append({
                "id": f"iss-{issue_counter}",
                "category": "Formatting & Quality",
                "page": 1,
                "original": p[:80] + "...",
                "suggestion": "Remove repeated duplicate paragraph to maintain clean document flow.",
                "reason": "Identified duplicate paragraph blocks.",
                "confidence": 0.90,
                "status": "pending"
            })
            issue_counter += 1
            break
        seen_paras.add(p_sub)

    # 5. Category & Subcategory Prediction
    pair_scores = {}
    for (f_main, f_sub), kws in FACULTY_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in lower_text)
        pair_scores[(f_main, f_sub)] = score

    best_pair = max(pair_scores, key=pair_scores.get)
    best_score = pair_scores[best_pair]

    if best_score > 0:
        pred_main, pred_sub = best_pair
        pred_conf = min(0.96, 0.50 + (best_score * 0.08))
    else:
        pred_main = selected_main or "Computer Science and Engineering"
        pred_sub = selected_sub or "Data Structures and Algorithms"
        pred_conf = 0.65

    # Check for category mismatch warning
    category_match = True
    mismatch_warning = None
    if selected_sub and best_score >= 2 and pred_sub.lower() != selected_sub.lower():
        category_match = False
        mismatch_warning = f"Content indicates strong affiliation with '{pred_main} > {pred_sub}' rather than selected '{selected_sub}'. Please verify classification."

    # Determine if clinical/medical review is required
    is_medical = (pred_main == "General Medicine" or (selected_main and selected_main.lower() == "general medicine"))

    # Compute overall quality score (0 - 100)
    deductions = (len([i for i in issues if i['category'] == 'Spelling']) * 3) + \
                 (len([i for i in issues if i['category'] == 'Grammar']) * 4) + \
                 (len([i for i in issues if i['category'] == 'Academic Review']) * 6) + \
                 (len([i for i in issues if i['category'] == 'Formatting & Quality']) * 4)
    quality_score = max(55, min(98, 100 - deductions))

    # Overall Status indicator
    if len(issues) == 0:
        status_label = "No major issues detected"
    elif quality_score >= 85 and not any(i['category'] == 'Academic Review' for i in issues):
        status_label = "Minor corrections suggested"
    elif quality_score >= 70:
        status_label = "Important issues require review"
    else:
        status_label = "Scan incomplete or quality review required"

    ocr_quality = "High Quality Digital Text" if total_words > 50 else "Short or Scanned Excerpt"

    return {
        "qualityScore": round(quality_score, 1),
        "statusLabel": status_label,
        "totalWords": total_words,
        "ocrQuality": ocr_quality,
        "categoryMatch": category_match,
        "mismatchWarning": mismatch_warning,
        "isMedicalReviewRequired": is_medical,
        "predictedCategory": {
            "mainCategory": pred_main,
            "subcategory": pred_sub,
            "confidence": round(pred_conf, 2)
        },
        "counts": {
            "spelling": len([i for i in issues if i['category'] == 'Spelling']),
            "grammar": len([i for i in issues if i['category'] == 'Grammar']),
            "academic": len([i for i in issues if i['category'] == 'Academic Review']),
            "formatting": len([i for i in issues if i['category'] == 'Formatting & Quality']),
            "totalIssues": len(issues)
        },
        "issues": issues,
        "extractedTextSnippet": cleaned[:3000]
    }

async def call_ai_scanning_model(text: str, selected_main: str, selected_sub: Optional[str]) -> Optional[Dict[str, Any]]:
    """Calls Gemini AI model for full contextual review if API key is present."""
    if not settings.GEMINI_API_KEY:
        return None

    prompt = f"""You are the AI Scanning Booth for CampusVerse, a university academic portal.
Analyze this study material excerpt for:
1. Spelling and grammatical mistakes (preserve technical abbreviations/symbols).
2. Factual statements, contradictions, or missing university syllabus requirements.
3. Formatting flaws (OCR errors, repeated blocks, missing headers).
4. Predict the most accurate engineering branch (Civil, Mechanical, Computer Science, Electrical, Electronics and Communication, Biomedical, Chemical, Aerospace).

Selected Category: {selected_main} -> {selected_sub}

Respond strictly in valid JSON format matching this schema:
{{
  "qualityScore": 88.5,
  "statusLabel": "No major issues detected | Minor corrections suggested | Important issues require review",
  "categoryMatch": true,
  "mismatchWarning": null,
  "predictedCategory": {{
    "mainCategory": "Engineering",
    "subcategory": "Computer Science Engineering",
    "confidence": 0.92
  }},
  "issues": [
    {{
      "id": "iss-1",
      "category": "Spelling | Grammar | Academic Review | Formatting & Quality",
      "page": 1,
      "original": "misspelled text",
      "suggestion": "corrected text",
      "reason": "Detailed explanation of correction",
      "confidence": 0.90,
      "status": "pending"
    }}
  ]
}}

Document Text Excerpt:
{text[:6000]}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.15,
            "responseMimeType": "application/json",
            "maxOutputTokens": 2048
        }
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                clean = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
                result = json.loads(clean)
                result["ocrQuality"] = "High Quality (AI Processed)"
                result["totalWords"] = len(text.split())
                result["counts"] = {
                    "spelling": len([i for i in result.get("issues", []) if i.get("category") == "Spelling"]),
                    "grammar": len([i for i in result.get("issues", []) if i.get("category") == "Grammar"]),
                    "academic": len([i for i in result.get("issues", []) if i.get("category") == "Academic Review"]),
                    "formatting": len([i for i in result.get("issues", []) if i.get("category") == "Formatting & Quality"]),
                    "totalIssues": len(result.get("issues", []))
                }
                return result
    except Exception as e:
        logger.warning("Gemini AI scan failed: %s. Falling back to deterministic scan.", e)
        return None

async def run_scanning_booth_analysis(text: str, selected_main: str = "Engineering", selected_sub: Optional[str] = None) -> Dict[str, Any]:
    """Top-level scanner integrating Gemini AI with fallback."""
    ai_result = await call_ai_scanning_model(text, selected_main, selected_sub)
    if ai_result:
        ai_result["extractedTextSnippet"] = text[:3000]
        return ai_result
    return deterministic_scan(text, selected_main, selected_sub)

def apply_selected_corrections(original_text: str, accepted_issues: List[Dict[str, Any]]) -> str:
    """Applies user-accepted corrections to produce a corrected document version without overwriting original."""
    modified_text = original_text
    for item in accepted_issues:
        orig = item.get("original", "").strip()
        sugg = item.get("suggestion", "").strip()
        if orig and sugg and orig in modified_text:
            modified_text = modified_text.replace(orig, sugg, 1)
    return modified_text
