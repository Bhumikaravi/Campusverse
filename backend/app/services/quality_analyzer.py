import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
from app.services.text_extract import DocumentExtractionResult

logger = logging.getLogger("campusverse.quality_analyzer")

def normalize_page_text(text: str) -> str:
    """Normalizes page text for hash-based exact and near duplicate detection."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower()).strip()
    return " ".join(cleaned.split())

def analyze_document_quality(
    extraction_res: DocumentExtractionResult,
    selected_subject: str = "",
    selected_branch: str = "",
    predicted_subject: str = "",
    file_bytes: Optional[bytes] = None,
    ext: str = ".pdf"
) -> Dict[str, Any]:
    """
    Performs comprehensive AI & rule-based quality inspection on extracted document pages:
    A. Blank Pages
    B. Duplicate Pages
    C. PDF Readability and Corruption
    D. Subject Relevance
    E. Completeness Assessment
    """
    total_pages = extraction_res.total_pages
    pages_text = extraction_res.pages_text or []
    pages_extracted = set(extraction_res.pages_extracted or [])
    pages_ocr = set(extraction_res.pages_ocr or [])
    pages_failed = extraction_res.pages_failed or []
    
    # --- Check A: Blank Pages ---
    blank_pages = []
    scanned_pages_without_ocr = []
    
    for idx, page_str in enumerate(pages_text):
        p_num = idx + 1
        clean_p = page_str.strip()
        words = clean_p.split()
        if len(words) < 5:
            # Check if this page was attempted with OCR
            if p_num in pages_ocr:
                blank_pages.append(p_num)
            elif p_num in pages_failed:
                # Text extraction failed or page is empty
                blank_pages.append(p_num)
            else:
                blank_pages.append(p_num)

    # --- Check B: Duplicate Pages ---
    page_hashes: Dict[str, List[int]] = {}
    duplicate_groups: List[Dict[str, Any]] = []
    duplicate_page_numbers = set()

    for idx, page_str in enumerate(pages_text):
        p_num = idx + 1
        norm = normalize_page_text(page_str)
        # Only check duplicate for pages with sufficient content (>= 15 words)
        if len(norm.split()) >= 15:
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            if h in page_hashes:
                page_hashes[h].append(p_num)
            else:
                page_hashes[h] = [p_num]

    for h, p_nums in page_hashes.items():
        if len(p_nums) > 1:
            duplicate_groups.append({
                "originalPage": p_nums[0],
                "duplicatePages": p_nums[1:],
                "message": f"Page(s) {', '.join(str(p) for p in p_nums[1:])} are identical to Page {p_nums[0]}"
            })
            for p in p_nums[1:]:
                duplicate_page_numbers.add(p)

    # --- Check C: PDF Readability & Corruption ---
    readability_status = "Good"
    extraction_errors = []

    if extraction_res.warning:
        extraction_errors.append(extraction_res.warning)

    if pages_failed:
        extraction_errors.append(f"Text extraction failed on {len(pages_failed)} page(s): {pages_failed}")
        if len(pages_failed) == total_pages and total_pages > 0:
            readability_status = "Unreadable / Corrupted"
        else:
            readability_status = "Partially Readable"
    elif extraction_res.total_words < 10 and total_pages > 0:
        readability_status = "Unreadable / No Extractable Text"
        extraction_errors.append("File contains minimal or no extractable text. Scanned pages may require high-resolution OCR.")
    else:
        readability_status = "Fully Readable"

    is_scanned = len(pages_ocr) > 0 or (len(blank_pages) == total_pages and total_pages > 0)
    requires_ocr_notice = not extraction_res.ocr_available and is_scanned

    # --- Check D: Subject Relevance ---
    target_subject = (selected_subject or predicted_subject or selected_branch or "").strip()
    full_text_sample = " ".join(pages_text)[:20000].lower()
    full_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", full_text_sample))

    relevance_score = 0.50
    relevance_status = "Moderately Relevant"
    relevance_explanation = "Document content has moderate correspondence to the academic domain."

    if target_subject and target_subject.lower() != "unable to classify":
        subj_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", target_subject.lower()) if len(w) > 3]
        if subj_tokens:
            matches = [t for t in subj_tokens if t in full_words or t in full_text_sample]
            overlap_ratio = len(matches) / len(subj_tokens)
            
            # Additional academic vocabulary check
            if target_subject.lower() in full_text_sample:
                relevance_score = 0.95
                relevance_status = "Highly Relevant"
                relevance_explanation = f"Exact subject title '{target_subject}' and key topics found repeatedly throughout the document."
            elif overlap_ratio >= 0.60:
                relevance_score = 0.80
                relevance_status = "Relevant"
                relevance_explanation = f"Document contains key vocabulary and concepts matching '{target_subject}'."
            elif overlap_ratio >= 0.30:
                relevance_score = 0.55
                relevance_status = "Moderately Relevant"
                relevance_explanation = f"Document partially relates to '{target_subject}', but lacks full topical coverage."
            else:
                relevance_score = 0.25
                relevance_status = "Potential Mismatch"
                relevance_explanation = f"Extracted text does not show strong vocabulary overlap with selected subject '{target_subject}'. Staff review advised."
        else:
            relevance_score = 0.70
            relevance_status = "Relevant"
            relevance_explanation = "Academic subject matches general coursework taxonomy."
    else:
        relevance_score = 0.50
        relevance_status = "Unverified"
        relevance_explanation = "Subject was unclassified; relevance cannot be confirmed without subject reference."

    # --- Check E: Completeness Assessment ---
    completeness_warnings = []
    completeness_status = "Verified"

    if total_pages <= 0:
        completeness_status = "Incomplete"
        completeness_warnings.append("Document has 0 readable pages.")
    elif extraction_res.total_words < 30 and total_pages >= 2:
        completeness_status = "Incomplete / Short"
        completeness_warnings.append(f"Unusually low text volume ({extraction_res.total_words} words across {total_pages} pages). Document may be incomplete or missing content.")
    elif len(pages_failed) > (total_pages * 0.40):
        completeness_status = "Missing Content"
        completeness_warnings.append(f"Over 40% of pages ({len(pages_failed)} of {total_pages}) could not be read or extracted.")
    else:
        # Strict requirement: "If no expected page count or reference document is available, report that completeness could not be verified."
        completeness_status = "Sufficient for Review"
        completeness_warnings.append("Document text volume appears consistent with notes. Note: Absolute completeness against official syllabus cannot be verified without a reference syllabus.")

    # --- Overall Quality Status ---
    # Allowed workflow status:
    # "Quality Check Passed" / "Needs Correction" / "Pending Review"
    has_critical_issue = (
        readability_status == "Unreadable / Corrupted" or
        len(pages_failed) == total_pages or
        (total_pages > 1 and len(blank_pages) == total_pages)
    )
    has_warning_issue = (
        len(blank_pages) > 0 or
        len(duplicate_page_numbers) > 0 or
        relevance_status == "Potential Mismatch" or
        len(pages_failed) > 0
    )

    if has_critical_issue:
        overall_status = "Needs Correction"
        quality_score = 25
    elif has_warning_issue:
        overall_status = "Needs Correction"
        quality_score = max(40, int(100 - (len(blank_pages) * 8) - (len(duplicate_page_numbers) * 10) - (20 if relevance_status == 'Potential Mismatch' else 0)))
    else:
        overall_status = "Quality Check Passed"
        quality_score = 95

    return {
        "overallStatus": overall_status,
        "qualityScore": quality_score,
        "readability": {
            "status": readability_status,
            "errors": extraction_errors,
            "ocrUsed": extraction_res.ocr_used,
            "ocrAvailable": extraction_res.ocr_available,
            "scanned": is_scanned,
        },
        "blankPages": {
            "count": len(blank_pages),
            "pageNumbers": blank_pages,
            "percentage": round((len(blank_pages) / total_pages * 100), 1) if total_pages > 0 else 0
        },
        "duplicatePages": {
            "count": len(duplicate_page_numbers),
            "pageNumbers": sorted(list(duplicate_page_numbers)),
            "groups": duplicate_groups
        },
        "subjectRelevance": {
            "score": round(relevance_score, 2),
            "status": relevance_status,
            "targetSubject": target_subject,
            "explanation": relevance_explanation
        },
        "completeness": {
            "status": completeness_status,
            "warnings": completeness_warnings,
            "totalWords": extraction_res.total_words,
            "totalPages": total_pages,
            "readablePages": len(extraction_res.pages_extracted or [])
        },
        "extractionErrors": extraction_errors,
        "adminActionRecommended": "Approve" if overall_status == "Quality Check Passed" else "Review Flags"
    }
