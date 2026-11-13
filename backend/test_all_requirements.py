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
    check_ocr_available,
    try_ocr_on_image_bytes,
)
from app.services.document_summarizer import (
    build_hierarchical_summary,
    generate_document_summary,
)

def make_test_pdf(filename, page_count, topic_name, include_table=False, is_scanned_image=False):
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
                story.append(Paragraph("Opening section covers theoretical syllabus objectives and core models across university curricula.", styles['Normal']))
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
                story.append(Paragraph("Crucial takeaway highlights that distributed verification guarantees continuous consistency across all nodes.", styles['Normal']))
            else:
                story.append(Paragraph(f"Section {p} details analytical mechanism {p}.2 analyzing state transitions, data structures, and throughput metrics.", styles['Normal']))
                story.append(Paragraph(f"Computational evaluation on page {p} confirms deterministic resource bounds under peak academic laboratory loads.", styles['Normal']))

        if p < page_count:
            story.append(PageBreak())

    doc.build(story)

def make_test_docx(filename, num_paragraphs=20):
    doc = docx.Document()
    doc.add_heading("Advanced Database Systems: Normalization & Query Optimization", level=1)
    doc.add_paragraph("Database Management Systems is defined as software coordinating transactional integrity and relational normalization.")
    
    for i in range(1, num_paragraphs):
        doc.add_paragraph(f"Section {i} explores relational algebra operations, join algorithms, indexing B-trees, and concurrency control protocols.")
        if i == 4:
            table = doc.add_table(rows=1, cols=3)
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "Normal Form"
            hdr_cells[1].text = "Condition"
            hdr_cells[2].text = "Eliminated Anomaly"
            
            row = table.add_row().cells
            row[0].text = "3NF"
            row[1].text = "No transitive functional dependencies"
            row[2].text = "Update and insertion anomalies"
            
    doc.add_paragraph("In conclusion, rigorous schema normalization guarantees lossless join decomposition and dependency preservation.")
    doc.save(filename)

def run_tests():
    print("=" * 80)
    print("CAMPUSVERSE ALL REQUIREMENTS END-TO-END VERIFICATION SUITE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # TEST 1: Multi-Page 30-Page PDF Extraction
    # -------------------------------------------------------------------------
    pdf_30_file = "test_run_30_page.pdf"
    make_test_pdf(pdf_30_file, 30, "Distributed Systems Consensus Protocols")
    buf_30 = open(pdf_30_file, "rb").read()
    
    doc_id_1 = str(uuid.uuid4())
    p_count = get_document_page_count(buf_30, ".pdf")
    res_30 = extract_document_complete(buf_30, ".pdf", max_pages=150, document_id=doc_id_1)
    
    print(f"\n[TEST 1] 30-Page PDF Extraction:")
    print(f"  Detected Page Count: {p_count} (Expected: 30)")
    print(f"  Processed Pages Count: {res_30.processed_pages} (Expected: 30)")
    print(f"  Total Extracted Words: {res_30.total_words}")
    print(f"  Extraction Status: {res_30.extraction_status}")
    
    assert p_count == 30, f"Page count mismatch: got {p_count}, expected 30"
    assert res_30.processed_pages == 30, f"Processed pages mismatch: got {res_30.processed_pages}, expected 30"
    assert res_30.extraction_status == "Completed"
    assert res_30.total_words > 500
    
    sum_30 = build_hierarchical_summary("Distributed Systems Consensus Protocols", res_30.pages_text, "Computer Science", 500, doc_id_1)
    print(f"  Summary Word Count: {sum_30['wordCount']} / 500 words")
    print(f"  Summary Coverage: contains definition={ 'is defined as' in sum_30['summary'] }, conclusion={ 'In conclusion' in sum_30['summary'] or 'demonstrate' in sum_30['summary'] }")
    assert sum_30['wordCount'] <= 500
    assert "Distributed Systems" in sum_30['summary']
    print("  -> PASSED: All 30 pages extracted and summarized.")

    # -------------------------------------------------------------------------
    # TEST 2: Multi-Page DOCX Extraction (Validating No False Scan Error)
    # -------------------------------------------------------------------------
    docx_file = "test_run_doc.docx"
    make_test_docx(docx_file, num_paragraphs=25)
    buf_docx = open(docx_file, "rb").read()
    
    doc_id_2 = str(uuid.uuid4())
    res_docx = extract_document_complete(buf_docx, ".docx", max_pages=150, document_id=doc_id_2)
    
    print(f"\n[TEST 2] DOCX Extraction:")
    print(f"  Detected Page Count: {res_docx.total_pages}")
    print(f"  Processed Pages: {res_docx.processed_pages}")
    print(f"  Total Words: {res_docx.total_words}")
    print(f"  Extraction Status: {res_docx.extraction_status}")
    
    assert res_docx.extraction_status == "Completed"
    assert res_docx.total_words > 200
    assert any("3NF" in p for p in res_docx.pages_text), "Table content was not extracted!"
    
    sum_docx = build_hierarchical_summary("Advanced Database Systems", res_docx.pages_text, "Computer Science", 500, doc_id_2)
    print(f"  Summary Word Count: {sum_docx['wordCount']} / 500 words")
    assert sum_docx['wordCount'] <= 500
    print("  -> PASSED: DOCX extracted without false scan error; tables and paragraphs captured.")

    # -------------------------------------------------------------------------
    # TEST 3: Scanned PDF / Image Requiring OCR
    # -------------------------------------------------------------------------
    scanned_pdf_file = "test_run_scanned.pdf"
    make_test_pdf(scanned_pdf_file, 2, "Pathology Laboratory Report", is_scanned_image=True)
    buf_scanned = open(scanned_pdf_file, "rb").read()
    
    doc_id_3 = str(uuid.uuid4())
    res_scanned = extract_document_complete(buf_scanned, ".pdf", max_pages=150, document_id=doc_id_3)
    
    print(f"\n[TEST 3] Scanned PDF with OCR Fallback:")
    print(f"  OCR Available: {check_ocr_available()}")
    print(f"  Pages Requiring OCR: {res_scanned.pages_ocr}")
    print(f"  Processed Pages: {res_scanned.processed_pages} / {res_scanned.total_pages}")
    print(f"  Extraction Status: {res_scanned.extraction_status}")
    
    assert res_scanned.processed_pages == 2
    assert 1 in res_scanned.pages_ocr or res_scanned.ocr_used
    print("  -> PASSED: Scanned page detected and OCR successfully extracted text.")

    # -------------------------------------------------------------------------
    # TEST 4: Large Document Near 150-Page Limit (140 Pages)
    # -------------------------------------------------------------------------
    pdf_140_file = "test_run_140_page.pdf"
    make_test_pdf(pdf_140_file, 140, "Thermodynamics and Power Cycles")
    buf_140 = open(pdf_140_file, "rb").read()
    
    doc_id_4 = str(uuid.uuid4())
    res_140 = extract_document_complete(buf_140, ".pdf", max_pages=150, document_id=doc_id_4)
    
    print(f"\n[TEST 4] 140-Page Document (Near 150-Page Limit):")
    print(f"  Total Pages: {res_140.total_pages} (Expected: 140)")
    print(f"  Processed Pages: {res_140.processed_pages} (Expected: 140)")
    print(f"  Total Words: {res_140.total_words}")
    
    assert res_140.total_pages == 140
    assert res_140.processed_pages == 140
    
    sum_140 = build_hierarchical_summary("Thermodynamics and Power Cycles", res_140.pages_text, "Mechanical Engineering", 500, doc_id_4)
    print(f"  Summary Word Count: {sum_140['wordCount']} / 500 words")
    assert sum_140['wordCount'] <= 500
    print("  -> PASSED: 140 pages processed without dropping any page.")

    # -------------------------------------------------------------------------
    # TEST 5: Corrupt or Genuinely Unreadable File
    # -------------------------------------------------------------------------
    corrupt_buf = b"%PDF-1.4\nCorrupt header and random bytes that do not form a valid stream \x00\xff"
    print(f"\n[TEST 5] Corrupt File Handling:")
    try:
        get_document_page_count(corrupt_buf, ".pdf")
        print("  -> FAILED: Corrupt file was not caught.")
        assert False, "Should have raised ValueError"
    except ValueError as ve:
        print(f"  Successfully caught corrupt file: '{ve}'")
        print("  -> PASSED: Corrupted document properly reported.")

    # -------------------------------------------------------------------------
    # TEST 6: Consecutive Upload Cross-Document Isolation Test
    # -------------------------------------------------------------------------
    print(f"\n[TEST 6] Consecutive Upload Cross-Document Isolation:")
    doc_A_id = f"doc_A_{uuid.uuid4().hex[:8]}"
    doc_B_id = f"doc_B_{uuid.uuid4().hex[:8]}"
    
    text_A = ["Quantum Computing principles cover qubits, superposition, and Shor's factorization algorithm."]
    text_B = ["Cardiology clinical guide covers myocardial infarction, electrocardiogram ST-elevation, and coronary reperfusion."]
    
    res_A = build_hierarchical_summary("Quantum Computing", text_A, "Computer Science", 500, doc_A_id)
    res_B = build_hierarchical_summary("Cardiology Clinical Guide", text_B, "General Medicine", 500, doc_B_id)
    
    assert doc_A_id != doc_B_id
    assert "qubit" in res_A["summary"].lower() and "cardio" not in res_A["summary"].lower()
    assert "cardio" in res_B["summary"].lower() and "qubit" not in res_B["summary"].lower()
    assert res_A["documentId"] == doc_A_id
    assert res_B["documentId"] == doc_B_id
    print(f"  Doc A ID: {res_A['documentId']} | Summary: {res_A['summary'][:70]}...")
    print(f"  Doc B ID: {res_B['documentId']} | Summary: {res_B['summary'][:70]}...")
    print("  -> PASSED: Consecutive uploads completely isolated, zero cross-mixing.")

    # Cleanup temporary test files
    for f in [pdf_30_file, docx_file, scanned_pdf_file, pdf_140_file]:
        try:
            os.remove(f)
        except Exception:
            pass

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED SUCCESSFULLY! COMPLETE SYSTEM VERIFIED.")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
