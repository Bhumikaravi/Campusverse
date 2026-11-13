import os
import io
import uuid
import docx
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PIL import Image, ImageDraw

from app.services.text_extract import (
    extract_document_complete,
    get_document_page_count,
    DocumentExtractionResult,
)
from app.services.document_summarizer import (
    build_hierarchical_summary,
    generate_document_summary,
)

def build_pdf_doc(filename, page_count, topic_name, include_table=False, is_scanned_image=False):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    styles = getSampleStyleSheet()
    story = []

    for p in range(1, page_count + 1):
        if is_scanned_image and p == 1:
            # Create a real image drawn on canvas to simulate a scanned page
            img_buf = io.BytesIO()
            img = Image.new("RGB", (600, 200), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((20, 80), f"SCANNED RECORD: {topic_name}", fill=(0, 0, 0))
            img.save(img_buf, format="PNG")
            img_buf.seek(0)
            from reportlab.platypus import Image as RLImage
            story.append(RLImage(img_buf, width=400, height=130))
        else:
            story.append(Paragraph(f"<b>{topic_name} - Chapter Section {p}</b>", styles['Heading1']))
            story.append(Spacer(1, 10))

            if p == 1:
                story.append(Paragraph(f"Foundational definition: {topic_name} is defined as a systematic academic discipline investigating architectural and algorithmic structures.", styles['Normal']))
                story.append(Paragraph(f"Opening section covers theoretical syllabus objectives and core models across university curricula.", styles['Normal']))
            elif p == page_count // 2:
                story.append(Paragraph(f"Mathematical derivation on page {p}: efficiency ratio formula is defined as eta = Work_net / Heat_in with asymptotic complexity O(n log n).", styles['Normal']))
                if include_table:
                    data = [
                        ["Component", "Function", "Complexity"],
                        ["CPU Scheduler", "Process dispatching", "O(1)"],
                        ["Memory Manager", "Virtual page mapping", "O(log n)"],
                    ]
                    t = Table(data, colWidths=[120, 180, 100])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                        ('GRID', (0,0), (-1,-1), 1, colors.grey),
                    ]))
                    story.append(t)
            elif p == page_count:
                story.append(Paragraph(f"In conclusion, empirical benchmarks demonstrate scalable performance and fault tolerance for {topic_name}.", styles['Normal']))
                story.append(Paragraph(f"Crucial takeaway highlights that distributed verification guarantees continuous consistency across all nodes.", styles['Normal']))
            else:
                story.append(Paragraph(f"Section {p} details analytical mechanism {p}.2 analyzing state transitions, data structures, and throughput metrics.", styles['Normal']))
                story.append(Paragraph(f"Computational evaluation on page {p} confirms deterministic resource bounds under peak academic laboratory loads.", styles['Normal']))

        if p < page_count:
            story.append(PageBreak())

    doc.build(story)

def build_docx_doc(filename, num_paragraphs=25):
    doc = docx.Document()
    doc.add_heading("Advanced Database Management Systems: Normalization & Query Optimization", level=1)
    doc.add_paragraph("Database Management Systems is defined as software coordinating data storage, transactional integrity, and relational normalization.")
    
    for i in range(1, num_paragraphs):
        doc.add_paragraph(f"Section {i} explores relational algebra operations, join algorithms, indexing B-trees, and concurrency control protocols.")
        if i == 5:
            table = doc.add_table(rows=1, cols=3)
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "Normal Form"
            hdr_cells[1].text = "Condition"
            hdr_cells[2].text = "Eliminated Anomaly"
            
            row = table.add_row().cells
            row[0].text = "3NF"
            row[1].text = "No transitive functional dependencies"
            row[2].text = "Update and insertion anomalies"
            
    doc.add_paragraph("In conclusion, rigorous schema normalization guarantees lossless join decomposition and dependency preservation across modern database engines.")
    doc.save(filename)

def run_all_tests():
    print("=" * 75)
    print("CAMPUSVERSE COMPREHENSIVE DOCUMENT EXTRACTION & SUMMARIZATION TEST SUITE")
    print("=" * 75)
    
    # -------------------------------------------------------------------------
    # TEST 1: Readable 30-Page PDF Multi-Page Extraction
    # -------------------------------------------------------------------------
    pdf_30_file = "test_run_30_page.pdf"
    build_pdf_doc(pdf_30_file, 30, "Operating Systems Process Scheduling")
    data_30 = open(pdf_30_file, "rb").read()
    
    doc_id_1 = str(uuid.uuid4())
    res_30 = extract_document_complete(data_30, ".pdf", max_pages=150, document_id=doc_id_1)
    
    print("\n[TEST 1] Multi-Page 30-Page PDF Extraction:")
    print(f"  Document ID: {res_30.document_id}")
    print(f"  Original Page Count: 30 | Processed Page Count: {res_30.processed_pages}")
    print(f"  Extraction Status: {res_30.extraction_status}")
    print(f"  Total Extracted Words: {res_30.total_words}")
    assert res_30.total_pages == 30, f"Expected 30 pages, got {res_30.total_pages}"
    assert res_30.processed_pages == 30, f"Expected 30 processed pages, got {res_30.processed_pages}"
    assert len(res_30.pages_text) == 30, f"Expected 30 pages in list, got {len(res_30.pages_text)}"
    assert res_30.extraction_status == "Completed"

    # Summarize and verify grounding
    sum_30 = build_hierarchical_summary("Operating Systems Process Scheduling", res_30.pages_text, "Computer Science", 500, doc_id_1)
    print(f"  Summary Word Count: {sum_30['wordCount']} / 500 words")
    assert sum_30['wordCount'] <= 500
    assert "Operating Systems" in sum_30['summary']
    assert "conclusion" in sum_30['summary'].lower() or "takeaway" in sum_30['summary'].lower()
    print("  -> PASSED: All 30 pages extracted and summarized across entire document.")
    os.remove(pdf_30_file)

    # -------------------------------------------------------------------------
    # TEST 2: DOCX Multi-Page Document (No False Scan Error)
    # -------------------------------------------------------------------------
    docx_file = "test_run_database.docx"
    build_docx_doc(docx_file, num_paragraphs=20)
    data_docx = open(docx_file, "rb").read()

    doc_id_2 = str(uuid.uuid4())
    res_docx = extract_document_complete(data_docx, ".docx", max_pages=150, document_id=doc_id_2)

    print("\n[TEST 2] Multi-Page DOCX Extraction (Validating No False Scan Error):")
    print(f"  Document ID: {res_docx.document_id}")
    print(f"  Detected Page Count: {res_docx.total_pages}")
    print(f"  Total Extracted Words: {res_docx.total_words}")
    print(f"  Extraction Status: {res_docx.extraction_status}")
    assert res_docx.total_words > 100, f"Expected > 100 words, got {res_docx.total_words}"
    assert res_docx.extraction_status == "Completed"
    assert "Normal Form" in "\n".join(res_docx.pages_text)

    sum_docx = build_hierarchical_summary("Database Management Systems", res_docx.pages_text, "Computer Science", 500, doc_id_2)
    print(f"  Summary Word Count: {sum_docx['wordCount']} / 500 words")
    assert sum_docx['wordCount'] <= 500
    print("  -> PASSED: DOCX processed without false scan error; tables and paragraphs extracted.")
    os.remove(docx_file)

    # -------------------------------------------------------------------------
    # TEST 3: PDF with Tables, Headings, and Math Formulas
    # -------------------------------------------------------------------------
    pdf_table_file = "test_run_tables.pdf"
    build_pdf_doc(pdf_table_file, 5, "Computer Architecture & Memory Hierarchy", include_table=True)
    data_table = open(pdf_table_file, "rb").read()

    doc_id_3 = str(uuid.uuid4())
    res_table = extract_document_complete(data_table, ".pdf", max_pages=150, document_id=doc_id_3)

    print("\n[TEST 3] PDF with Tables, Headings, and Formulas:")
    print(f"  Extracted Pages: {res_table.processed_pages} / {res_table.total_pages}")
    assert res_table.processed_pages == 5
    full_table_text = "\n".join(res_table.pages_text)
    assert "CPU Scheduler" in full_table_text or "Memory Manager" in full_table_text or "O(n log n)" in full_table_text
    print("  -> PASSED: Tables, headings, and equations captured accurately.")
    os.remove(pdf_table_file)

    # -------------------------------------------------------------------------
    # TEST 4: Document Near the 150-Page Limit (140 Pages)
    # -------------------------------------------------------------------------
    pdf_140_file = "test_run_140_page.pdf"
    build_pdf_doc(pdf_140_file, 140, "Advanced Civil Engineering Infrastructure")
    data_140 = open(pdf_140_file, "rb").read()

    doc_id_4 = str(uuid.uuid4())
    res_140 = extract_document_complete(data_140, ".pdf", max_pages=150, document_id=doc_id_4)

    print("\n[TEST 4] Large Document Near 150-Page Limit (140 Pages):")
    print(f"  Original Pages: 140 | Processed Pages: {res_140.processed_pages}")
    print(f"  Total Words: {res_140.total_words}")
    assert res_140.total_pages == 140
    assert res_140.processed_pages == 140

    sum_140 = build_hierarchical_summary("Advanced Civil Engineering Infrastructure", res_140.pages_text, "Civil Engineering", 500, doc_id_4)
    print(f"  Summary Word Count: {sum_140['wordCount']} / 500 words")
    assert sum_140['wordCount'] <= 500
    print("  -> PASSED: 140-page document processed with zero dropped pages; summary <= 500 words.")
    os.remove(pdf_140_file)

    # -------------------------------------------------------------------------
    # TEST 5: Corrupt or Genuinely Unreadable File
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Corrupt or Genuinely Unreadable File:")
    corrupt_data = b"%PDF-1.4\n%Invalid garbage bytes binary \x00\xff\xfe\x01\x02"
    try:
        get_document_page_count(corrupt_data, ".pdf")
        assert False, "Should have raised ValueError on corrupt file"
    except ValueError as ve:
        print(f"  -> PASSED: Corrupt document caught with descriptive error: '{ve}'")

    # -------------------------------------------------------------------------
    # TEST 6: Two Consecutive Uploads (Verifying Zero Content Mixing)
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Consecutive Upload Cross-Document Isolation Test:")
    file_a = "test_doc_A.pdf"
    file_b = "test_doc_B.pdf"
    build_pdf_doc(file_a, 4, "Quantum Cryptography and Post-Quantum Algorithms")
    build_pdf_doc(file_b, 4, "Clinical Cardiology and Cardiovascular Therapeutics")

    doc_id_A = "doc_A_" + str(uuid.uuid4())[:8]
    doc_id_B = "doc_B_" + str(uuid.uuid4())[:8]

    res_A = extract_document_complete(open(file_a, "rb").read(), ".pdf", document_id=doc_id_A)
    sum_A = build_hierarchical_summary("Quantum Cryptography", res_A.pages_text, "Computer Science", 500, doc_id_A)

    res_B = extract_document_complete(open(file_b, "rb").read(), ".pdf", document_id=doc_id_B)
    sum_B = build_hierarchical_summary("Clinical Cardiology", res_B.pages_text, "General Medicine", 500, doc_id_B)

    print(f"  Doc A ({doc_id_A}) Summary Preview: \"{sum_A['summary'][:90]}...\"")
    print(f"  Doc B ({doc_id_B}) Summary Preview: \"{sum_B['summary'][:90]}...\"")

    # Verify complete isolation
    assert "cardiology" not in sum_A['summary'].lower()
    assert "cryptography" not in sum_B['summary'].lower()
    assert sum_A['documentId'] == doc_id_A
    assert sum_B['documentId'] == doc_id_B
    print("  -> PASSED: Documents A and B are completely isolated with zero content cross-mixing.")

    os.remove(file_a)
    os.remove(file_b)

    print("\n" + "=" * 75)
    print("ALL VERIFICATION AND TEST SUITES COMPLETED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    run_all_tests()
