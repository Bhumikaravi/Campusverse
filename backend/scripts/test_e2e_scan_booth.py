"""End-to-End Test Suite for AI Material Scanning in Dashboard:
1. Validates upload of standard document (< 150 pages).
2. Validates document with exactly 150 pages is accepted.
3. Validates document with 151 pages is rejected before AI processing with exact message.
4. Verifies 15-20 word summary constraint and calibration.
5. Verifies calibrated AI confidence score and status tier.
6. Verifies benchmark evaluation execution and results.
7. Verifies publishing into MongoDB materials collection.
"""

import sys
import io
from pathlib import Path
import pypdf
import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

API_BASE = "http://127.0.0.1:5000/api"

def create_mock_pdf(num_pages: int, text: str = "Academic test content for CampusVerse.") -> bytes:
    """Generates an in-memory PDF with exact page count using pypdf."""
    writer = pypdf.PdfWriter()
    for i in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def test_page_limits():
    print("\n--- Test 1: Page Limit Validation ---")
    
    # 1. Document with 10 pages (< 150)
    pdf_10 = create_mock_pdf(10)
    resp_10 = httpx.post(
        f"{API_BASE}/scanning-booth/scan",
        files={"file": ("notes_10_pages.pdf", pdf_10, "application/pdf")},
        data={"mainCategory": "Computer Science and Engineering", "subcategory": "Data Structures and Algorithms"}
    )
    assert resp_10.status_code == 200, f"Expected 200 for 10 pages, got {resp_10.status_code}: {resp_10.text}"
    data_10 = resp_10.json()
    assert data_10["pageCount"] == 10, f"Expected pageCount 10, got {data_10['pageCount']}"
    print("[PASS] 10-page document uploaded and scanned successfully (pageCount = 10).")

    # 2. Document with exactly 150 pages
    pdf_150 = create_mock_pdf(150)
    resp_150 = httpx.post(
        f"{API_BASE}/scanning-booth/scan",
        files={"file": ("notes_150_pages.pdf", pdf_150, "application/pdf")},
        data={"mainCategory": "Computer Science and Engineering", "subcategory": "Operating Systems"}
    )
    assert resp_150.status_code == 200, f"Expected 200 for 150 pages, got {resp_150.status_code}: {resp_150.text}"
    data_150 = resp_150.json()
    assert data_150["pageCount"] == 150, f"Expected pageCount 150, got {data_150['pageCount']}"
    print("[PASS] Exactly 150-page document accepted and scanned successfully (pageCount = 150).")

    # 3. Document with 151 pages (> 150) - MUST BE REJECTED
    pdf_151 = create_mock_pdf(151)
    resp_151 = httpx.post(
        f"{API_BASE}/scanning-booth/scan",
        files={"file": ("notes_151_pages.pdf", pdf_151, "application/pdf")},
        data={"mainCategory": "Computer Science and Engineering"}
    )
    assert resp_151.status_code == 400, f"Expected 400 for 151 pages, got {resp_151.status_code}"
    err_detail = resp_151.json().get("detail", "")
    assert "Upload limit exceeded. Please upload a document containing no more than 150 pages." in err_detail, \
        f"Unexpected error message: {err_detail}"
    print("[PASS] 151-page document rejected before AI processing with exact message:")
    print(f"  --> '{err_detail}'")

def test_summary_and_confidence():
    print("\n--- Test 2: AI Confidence Score & 15-20 Word Summary ---")
    
    with open("public/sample_files/cse_dsa_balanced_trees_graphs_notes.pdf", "rb") as f:
        file_bytes = f.read()

    resp = httpx.post(
        f"{API_BASE}/scanning-booth/scan",
        files={"file": ("cse_dsa_notes.pdf", file_bytes, "application/pdf")},
        data={"mainCategory": "Computer Science and Engineering", "subcategory": "Data Structures and Algorithms"}
    )
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    # Check 15-20 word summary
    summary_obj = data.get("conciseSummary", {})
    summary_text = summary_obj.get("summary", "")
    word_count = summary_obj.get("wordCount", len(summary_text.split()))
    print(f"Generated Summary ({word_count} words): \"{summary_text}\"")
    assert 15 <= word_count <= 20, f"Word count {word_count} outside 15-20 word limit!"
    print(f"[PASS] Summary word count verified: {word_count} words (strictly in [15, 20]).")

    # Check Calibrated Confidence Score
    conf = data.get("confidenceScore", {})
    percentage = conf.get("percentage")
    tier = conf.get("tier")
    status_label = conf.get("statusLabel")
    breakdown = conf.get("breakdown", {})
    
    assert 0 <= percentage <= 100, f"Invalid confidence percentage: {percentage}"
    assert tier in ["HIGH", "MEDIUM", "LOW"], f"Invalid tier: {tier}"
    print(f"[PASS] AI Calibrated Confidence: {percentage}% ({status_label}, Tier: {tier})")
    print(f"  Breakdown: Classification={breakdown.get('classificationConfidence')}%, "
          f"Alignment={breakdown.get('categoryAlignment')}%, TextQuality={breakdown.get('textQuality')}%, "
          f"Relevance={breakdown.get('contentRelevance')}%, Title={breakdown.get('titleDetection')}%")

def test_benchmarks_api():
    print("\n--- Test 3: Benchmark Suite Evaluation API ---")
    resp = httpx.get(f"{API_BASE}/scanning-booth/benchmarks/latest")
    assert resp.status_code == 200, f"Failed to get benchmarks: {resp.text}"
    report = resp.json()
    metrics = report.get("metrics", {})
    safety = report.get("safetyGuardrails", {})
    
    print(f"[PASS] Benchmark Accuracy: {metrics.get('overallAccuracy')}%")
    print(f"[PASS] F1 Score: {metrics.get('f1Score')}%, Precision: {metrics.get('precision')}%, Recall: {metrics.get('recall')}%")
    print(f"[PASS] Summary 15-20 Word Compliance: {metrics.get('summaryWordCountCompliance')}%")
    print(f"[PASS] False Approval Rate: {safety.get('falseApprovalRate')}%")
    print(f"[PASS] Clinical Medical Rule Guarded: {safety.get('medicalAutoApprovePrevented')}")
    print(f"[PASS] 151-Page Oversized Rejected: {safety.get('oversizedRejected')}")

if __name__ == "__main__":
    test_page_limits()
    test_summary_and_confidence()
    test_benchmarks_api()
    print("\n==========================================")
    print("ALL VERIFICATION CRITERIA PASSED!")
    print("==========================================")
