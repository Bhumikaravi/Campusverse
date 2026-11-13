import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.services.text_extract import extract_document_pages, get_document_page_count
from app.services.document_summarizer import build_hierarchical_summary

def make_test_pdf(filename, page_count, subject_name):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    story = []
    
    for p in range(1, page_count + 1):
        story.append(Paragraph(f"<b>{subject_name} - Chapter Section {p}</b>", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        if p == 1:
            story.append(Paragraph(f"{subject_name} is defined as a systematic academic discipline investigating structural principles and computational foundations.", styles['Normal']))
            story.append(Paragraph(f"Page {p} introduces the overarching framework and theoretical syllabus objectives for undergraduate study.", styles['Normal']))
        elif p == page_count // 2:
            story.append(Paragraph(f"Core mathematical relationship on page {p}: efficiency formula is given by eta = Work_output / Heat_input with O(n log n) runtime complexity.", styles['Normal']))
            story.append(Paragraph(f"Experimental models analyze empirical convergence rates across distributed benchmark clusters.", styles['Normal']))
        elif p == page_count:
            story.append(Paragraph(f"In conclusion, experimental results demonstrate consistent performance scaling across all test configurations.", styles['Normal']))
            story.append(Paragraph(f"Crucial takeaway highlights that multi-tier validation guarantees optimal system reliability.", styles['Normal']))
        else:
            story.append(Paragraph(f"Section {p} examines analytical method {p}.3 covering algorithmic properties, state transitions, and memory allocation.", styles['Normal']))
            story.append(Paragraph(f"The mechanism on page {p} coordinates operational throughput while minimizing latency overhead.", styles['Normal']))
            
        if p < page_count:
            story.append(PageBreak())
            
    doc.build(story)

test_files = [
    ("test_5_page.pdf", 5, "Civil Engineering Structural Analysis", "Civil Engineering"),
    ("test_30_page.pdf", 30, "Computer Science Operating Systems", "Computer Science"),
    ("test_100_page.pdf", 100, "General Medicine Clinical Pathology", "General Medicine")
]

def run_tests():
    print("=" * 70)
    print("TESTING MULTI-LENGTH DOCUMENTS: 5-PAGE, 30-PAGE, AND 100-PAGE FILES")
    print("=" * 70)

    for fname, pages_expected, doc_title, category in test_files:
        make_test_pdf(fname, pages_expected, doc_title)
        data = open(fname, "rb").read()
        
        # 1. Page count check
        p_count = get_document_page_count(data, ".pdf")
        assert p_count == pages_expected, f"Expected {pages_expected} pages, got {p_count}"
        
        # 2. Extract pages list
        pages = extract_document_pages(data, ".pdf", max_pages=150)
        assert len(pages) == pages_expected, f"Extracted {len(pages)} pages, expected {pages_expected}"
        
        # 3. Hierarchical summarization across whole document
        res = build_hierarchical_summary(doc_title, pages, category, max_words=500)
        
        print(f"\nDocument: {fname}")
        print(f"  Target Pages: {pages_expected} | Extracted Pages: {res['pageCount']}")
        print(f"  Academic Category: {res['academicCategory']}")
        print(f"  Summary Word Count: {res['wordCount']} / {res['maxWords']} words")
        print(f"  Processing Status: {res['status']}")
        
        assert res['wordCount'] <= 500, f"Exceeded max words: {res['wordCount']}"
        assert res['status'] in ["Completed", "Summary ready"], f"Unexpected status: {res['status']}"
        
        # Check proportional length
        if pages_expected == 5:
            assert res['wordCount'] <= 180, f"5-page summary should be concise, got {res['wordCount']}"
        if pages_expected == 100:
            assert res['wordCount'] >= 200, f"100-page summary should be comprehensive, got {res['wordCount']}"
            
        print("  Summary Preview:")
        print("   \"" + res['summary'][:240] + "...\"")
        
        # Clean up test file
        try:
            os.remove(fname)
        except Exception:
            pass

    print("\n" + "=" * 70)
    print("ALL 5-PAGE, 30-PAGE, AND 100-PAGE TESTS PASSED COMPLETELY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
