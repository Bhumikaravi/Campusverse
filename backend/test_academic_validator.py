import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.config import settings
settings.GEMINI_API_KEY = ""  # Test deterministic deep semantic engine locally without network latency

from app.services.academic_validator import (
    validate_document_relevance_sync,
    AcademicDocType
)

def run_tests():
    print("=" * 75)
    print("  CAMPUSVERSE DEEP AI DOCUMENT CONTENT ANALYSIS & RELEVANCE SUITE")
    print("=" * 75)

    tests_passed = 0
    total_tests = 12

    # -------------------------------------------------------------------------
    # TEST 1: Certificate containing "This is to certify that" -> REJECTED
    # -------------------------------------------------------------------------
    cert_1 = """
    CERTIFICATE OF COMPLETION
    This is to certify that Rahul Sharma has successfully completed the 8-week Summer Internship
    in Machine Learning & Data Analytics organized by TechCorp Solutions from June 2026 to August 2026.
    During the internship, he demonstrated exceptional dedication and technical excellence.
    Awarded this certificate on 15th August 2026.
    Authorized Signatory
    Director, TechCorp Academy
    """
    res1 = validate_document_relevance_sync(cert_1, title="Internship Certificate", filename="Certificate.pdf", selected_subject="Machine Learning")
    assert res1["decision"] == "REJECTED" and res1["document_type"] in [AcademicDocType.CERTIFICATE, AcademicDocType.INTERNSHIP_CERTIFICATE]
    assert len(res1["certificate_indicators"]) > 0
    print(f"  [PASS] Test 1: Certificate with 'This is to certify that' -> REJECTED")
    print(f"         Purpose: {res1['overall_purpose']}")
    print(f"         Indicators: {res1['detected_important_phrases'][:3]}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 2: Certificate WITHOUT the word "certificate" -> REJECTED
    # -------------------------------------------------------------------------
    cert_without_word_cert = """
    NATIONAL SKILLS DEVELOPMENT INITIATIVE
    Awarded to: Ananya Deshmukh
    In recognition of successful completion and dedication in the Professional Training Programme on Applied Artificial Intelligence.
    Completion Date: October 24, 2026 | Credential ID: NSDI-2026-89412
    Issued by: Global Education Foundation
    Authorized Signatory: Dr. R. K. Nair
    Director of Training
    """
    assert "certificate" not in cert_without_word_cert.lower()
    res2 = validate_document_relevance_sync(cert_without_word_cert, title="Course Award", filename="Ananya_Award.pdf", selected_subject="Artificial Intelligence")
    assert res2["decision"] == "REJECTED" and res2["document_type"] == AcademicDocType.CERTIFICATE
    print(f"  [PASS] Test 2: Certificate WITHOUT the word 'certificate' -> REJECTED")
    print(f"         Purpose: {res2['overall_purpose']}")
    print(f"         Indicators: {res2['detected_important_phrases'][:3]}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 3: Certificate containing Python and AI terminology -> REJECTED
    # -------------------------------------------------------------------------
    cert_with_tech_terms = """
    DEEP LEARNING INSTITUTE OF TECHNOLOGY
    This is to certify that S. Karthik has successfully completed the advanced training course in:
    Applied Python Programming, Machine Learning, Deep Neural Networks, and Natural Language Processing.
    Awarded on: 18th September 2026
    Duration: 60 Hours of Practical Labs
    Issued by: Global AI Academy
    Authorized Signatory: Chief Learning Officer
    """
    res3 = validate_document_relevance_sync(cert_with_tech_terms, title="Python Deep Learning Certificate", filename="Python_Cert.pdf", selected_subject="Python Programming")
    assert res3["decision"] == "REJECTED" and res3["document_type"] == AcademicDocType.CERTIFICATE
    print(f"  [PASS] Test 3: Certificate with Python & AI terminology -> REJECTED")
    print(f"         Purpose: {res3['overall_purpose']}")
    print(f"         Indicators: {res3['detected_important_phrases'][:3]}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 4: Certificate containing issue dates and signatures -> REJECTED
    # -------------------------------------------------------------------------
    cert_with_dates_signatures = """
    ACHIEVEMENT RECOGNITION
    Presented to: Meera Nair
    In appreciation of successful participation in the International Data Science Summit 2026.
    Date of Issue: November 05, 2026
    Credential Verification ID: #DS-2026-9081
    Authorized Signature: Dr. Elena Rostova
    Head of Institution
    Institutional Seal Affixed
    """
    res4 = validate_document_relevance_sync(cert_with_dates_signatures, title="Summit Recognition", filename="Recognition.pdf", selected_subject="Data Science")
    assert res4["decision"] == "REJECTED" and res4["document_type"] == AcademicDocType.CERTIFICATE
    print(f"  [PASS] Test 4: Certificate with issue dates and signatures -> REJECTED")
    print(f"         Purpose: {res4['overall_purpose']}")
    print(f"         Indicators: {res4['detected_important_phrases'][:3]}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 5: Resume with technical skills -> REJECTED
    # -------------------------------------------------------------------------
    resume_text = """
    Bhumika Ravi
    Email: bhumika@example.com | Phone: +91 9876543210 | Bangalore, India
    LinkedIn: linkedin.com/in/bhumikaravi | GitHub: github.com/bhumikaravi

    CAREER OBJECTIVE:
    Motivated Computer Science undergraduate seeking an ambitious Software Engineering internship.

    EDUCATION:
    - B.Tech in Computer Science and Engineering, CGPA: 9.2 (2023 - 2027)

    TECHNICAL SKILLS:
    - Languages: Python, Java, JavaScript, C++
    - Web Technologies: React, FastAPI, Node.js, Tailwind CSS
    - Databases: MongoDB, PostgreSQL

    PROJECTS:
    1. CampusVerse - Full Stack Student Learning Platform
    2. Deep Learning Classifier for digit recognition

    DECLARATION:
    I hereby declare that the details provided above are true to the best of my knowledge.
    """
    res5 = validate_document_relevance_sync(resume_text, title="Bhumika CV", filename="Resume.pdf", selected_subject="Computer Science")
    assert res5["decision"] == "REJECTED" and res5["document_type"] == AcademicDocType.RESUME_CV
    print(f"  [PASS] Test 5: Resume with technical skills -> REJECTED")
    print(f"         Purpose: {res5['overall_purpose']}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 6: Placement offer letter -> REJECTED
    # -------------------------------------------------------------------------
    placement_offer_text = """
    CAMPUS PLACEMENT SELECTION - OFFER OF EMPLOYMENT
    To: Candidate Sneha Patel
    Date: November 10, 2026
    
    Dear Sneha,
    We are pleased to offer you the position of Associate Software Engineer at CloudScale Innovations.
    Your selection was confirmed during the recent on-campus placement recruitment drive.
    
    Compensation Structure:
    - Annual CTC: INR 12,00,000 per annum
    - Fixed Pay: INR 9,50,000
    - Variable Pay: INR 2,50,000
    
    Terms and conditions of employment:
    - Date of Joining: July 15, 2027
    - Probation Period: 6 months from the reporting date
    Please sign and return the duplicate copy of this letter of intent.
    Director of Talent Acquisition
    """
    res6 = validate_document_relevance_sync(placement_offer_text, title="Sneha Offer Letter", filename="Offer_Letter.pdf", selected_subject="Computer Science")
    assert res6["decision"] == "REJECTED" and res6["document_type"] == AcademicDocType.PLACEMENT_RECRUITMENT
    print(f"  [PASS] Test 6: Placement offer letter -> REJECTED")
    print(f"         Purpose: {res6['overall_purpose']}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 7: Academic notes containing the word "certificate" in an explanation -> APPROVED
    # -------------------------------------------------------------------------
    digital_cert_study_notes = """
    Lecture 8: Network Security & Cryptography
    Topic: Public Key Infrastructure (PKI) and Digital Certificates
    Department of Computer Science & Engineering

    1. What is a Digital Certificate?
    Definition: A digital certificate is an electronic document used to prove the ownership of a public key.
    The certificate contains information about the key, identity information of its owner, and the digital signature
    of an entity that has verified the certificate's contents (the Certificate Authority).
    
    2. The X.509 Digital Certificate Standard:
    The most common format for public-key certificates is defined by ITU-T standard X.509.
    Key components of an X.509 certificate:
    - Version number (usually v3).
    - Serial number (unique identifier issued by the CA).
    - Signature algorithm identifier (e.g. SHA-256 with RSA).
    - Issuer name (Certificate Authority entity).
    - Validity period: Not Before and Not After dates.
    - Subject name: The identity of the machine or individual.
    - Subject Public Key Information.

    3. How SSL/TLS Certificates Work:
    When a web browser connects to a secure HTTPS server, the server transmits its SSL/TLS certificate.
    The browser verifies the certificate against its pre-installed list of trusted root Certificate Authorities.
    If valid, a symmetric session key is negotiated using the server's public key.
    If the certificate has expired, or is listed in the Certificate Revocation List (CRL) or OCSP,
    the browser displays a security warning.

    Review Questions:
    Q1. Explain the role of a Certificate Authority (CA) in Public Key Infrastructure (PKI).
    Q2. Differentiate between a self-signed certificate and a CA-signed digital certificate.
    """
    res7 = validate_document_relevance_sync(digital_cert_study_notes, title="PKI and Digital Certificates Notes", filename="Cryptography_Lecture_8.pdf", selected_subject="Network Security")
    assert res7["decision"] == "APPROVED" and res7["is_academic"] is True
    print(f"  [PASS] Test 7: Academic notes containing 'certificate' in an explanation -> APPROVED")
    print(f"         Purpose: {res7['overall_purpose']}")
    print(f"         Academic Indicators: {res7['academic_indicators'][:3]}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 8: Textbook containing dates and institutional names -> APPROVED
    # -------------------------------------------------------------------------
    history_textbook = """
    Chapter 3: Economic Development and Policy in Post-Independence India
    Course: Indian Economic History | Department of Economics

    Section 3.1: Post-Independence Policy Framework (1947–1991)
    Following the attainment of independence on August 15, 1947, the Planning Commission was established in March 1950
    by the Government of India under Prime Minister Jawaharlal Nehru.
    Key national development institutions were established during this formative era:
    - The Reserve Bank of India (RBI), nationalized in 1949.
    - The Indian Institutes of Technology (IITs), the first established at Kharagpur in 1951.
    - The State Bank of India, established under the SBI Act in 1955.

    Section 3.2: The Industrial Policy Resolution of 1956
    The 1956 resolution laid the foundation for the public sector's commanding heights in core heavy industries.
    Between 1950 and 1980, the average annual GDP growth rate stabilized around 3.5%, characterized by economists
    as the historic Hindu rate of growth before the structural reforms of 1991.

    Discussion Questions:
    1. Analyze the macroeconomic objectives behind the nationalization of commercial banks in 1969.
    2. Explain the role of the Planning Commission in early five-year plans.
    """
    res8 = validate_document_relevance_sync(history_textbook, title="Indian Economic History Textbook", filename="Economics_Chapter_3.pdf", selected_subject="Economics")
    assert res8["decision"] == "APPROVED" and res8["document_type"] == AcademicDocType.TEXTBOOK_CHAPTER
    print(f"  [PASS] Test 8: Textbook containing dates & institutional names -> APPROVED")
    print(f"         Purpose: {res8['overall_purpose']}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 9: Genuine subject notes with minor grammatical errors -> APPROVED
    # -------------------------------------------------------------------------
    notes_with_typos = """
    Lecture 5: Binary Serch Algoritm and Complexity Analysis
    Departmnt of Computr Science
    
    In this chpater we study the binary serch techniqe on sorted arrays.
    Binaary serch works by repeatedly dividing the serch interval in half.
    If the target value is less than the middle elemet, the serch continues in the lower half.
    Otherwis, the serch continues in the upper half.
    
    Time Complecsity:
    Best case: O(1) when the target is at the midle index.
    Worst case: O(log n) where n is the number of elemets.
    Space Complecsity: O(1) for the iterative implementasion.
    
    Recap:
    Binary serch requires the input colection to be sorted beforehand.
    """
    res9 = validate_document_relevance_sync(notes_with_typos, title="Binary Search Notes", filename="Binary_Search.pdf", selected_subject="Computer Science")
    assert res9["decision"] == "APPROVED" and res9["is_academic"] is True
    print(f"  [PASS] Test 9: Genuine subject notes with minor grammatical errors -> APPROVED")
    print(f"         Quality Score: {res9['document_quality']} (acceptable: {res9['is_acceptable_quality']})")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 10: Scanned certificate PDF (via OCR) -> REJECTED
    # -------------------------------------------------------------------------
    scanned_cert_ocr = """
    CERTIFICATE OF PARTICIPATION
    Proudly presented to Rajesh Kumar for attending the National Robotics Symposium 2026.
    Organized by Department of Mechatronics, IIT Madras.
    Convener Signature | Dean Academic Affairs Signature
    Institutional Seal Affixed | Date: 14-10-2026
    """
    res10 = validate_document_relevance_sync(scanned_cert_ocr, title="Scanned Certificate", filename="Scan_Cert.pdf", selected_subject="Mechatronics", ocr_applied=True)
    assert res10["decision"] == "REJECTED" and res10["document_type"] == AcademicDocType.CERTIFICATE
    print(f"  [PASS] Test 10: Scanned certificate PDF (OCR) -> REJECTED")
    print(f"         Purpose: {res10['overall_purpose']}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 11: Multi-page academic notes (document-wide analysis) -> APPROVED
    # -------------------------------------------------------------------------
    page_1 = """
    Module 1: Introduction to Database Management Systems
    Department of Information Technology
    A database is an organized collection of structured information or data.
    DBMS Architecture: The 3-schema architecture divides the system into physical, logical, and view levels.
    """
    page_2 = """
    Module 2: Relational Query Languages and SQL
    Relational algebra operations: Select, Project, Cartesian Product, Union, Set Difference, and Natural Join.
    SQL aggregate functions: COUNT(), SUM(), AVG(), MIN(), MAX() with GROUP BY and HAVING clauses.
    """
    page_3 = """
    Module 3: Transaction Processing and ACID Properties
    A transaction is a unit of program execution that accesses and updates data items.
    ACID Properties:
    - Atomicity: All or nothing execution.
    - Consistency: Preserves database invariants.
    - Isolation: Transactions execute without interference.
    - Durability: Committed updates persist permanently.
    Review Exercises: Explain the two-phase locking protocol.
    """
    full_multi_page = f"{page_1}\n\n{page_2}\n\n{page_3}"
    res11 = validate_document_relevance_sync(
        text=full_multi_page,
        title="DBMS Comprehensive Course Notes",
        filename="DBMS_Full_Notes.pdf",
        selected_subject="Database Management Systems",
        pages_text=[page_1, page_2, page_3],
        total_pages=3
    )
    assert res11["decision"] == "APPROVED" and res11["is_academic"] is True
    assert res11["total_pages_analyzed"] == 3
    print(f"  [PASS] Test 11: Multi-page academic notes (3 pages analyzed) -> APPROVED")
    print(f"         Purpose: {res11['overall_purpose']}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 12: Poor-quality and corrupted documents -> REJECTED
    # -------------------------------------------------------------------------
    corrupted_gibberish = """
    asdfghjkl zxcvbnm qweqweqwe bbbbb ccccc ddddd \x00\x01\x02 ???%%%###$$$&&&***
    zzzzzzzz aaaaaaaaa mmmmmmmm llllllll pppppppp
    """
    res12 = validate_document_relevance_sync(corrupted_gibberish, title="Corrupt File", filename="Corrupt.pdf", selected_subject="Physics")
    assert res12["decision"] == "REJECTED" and res12["document_type"] in [AcademicDocType.CORRUPTED_OR_POOR_QUALITY, AcademicDocType.EMPTY_OR_UNREADABLE]
    print(f"  [PASS] Test 12: Poor-quality and corrupted document -> REJECTED")
    print(f"         Purpose: {res12['overall_purpose']}")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 13: College Fee Receipt -> REJECTED (FEE_RECEIPT)
    # -------------------------------------------------------------------------
    fee_receipt_text = """
    NATIONAL INSTITUTE OF ENGINEERING & TECHNOLOGY
    STUDENT COPY - ACCOUNTS BRANCH
    COLLEGE FEE RECEIPT
    Receipt No: REC-2026/89412
    Date of Issue: 12-08-2026
    Received with thanks from: Rahul Sharma
    Roll Number: 23CS042
    Degree / Department: B.Tech Computer Science & Engineering
    Semester: 4th Semester (Batch 2023-2027)

    PARTICULARS OF FEE:
    1. Tuition Fee (Semester IV): Rs. 65,000.00
    2. Computer Laboratory & Internet Fee: Rs. 10,000.00
    3. University Examination Fee: Rs. 2,500.00
    4. Library & Sports Development Fee: Rs. 2,500.00

    Total Amount Paid: Rs. 80,000.00
    Amount in Words: Rupees Eighty Thousand Only
    Payment Mode: UPI (UTR No: 492019482910)
    Transaction Status: Paid Successfully
    Cashier Signature & Institutional Seal
    Note: Fees once paid will not be refunded under any circumstances.
    """
    res13 = validate_document_relevance_sync(fee_receipt_text, title="College Fee Receipt", filename="Fee_Receipt_Sem4.pdf", selected_subject="Computer Science")
    assert res13["decision"] == "REJECTED" and res13["document_type"] == AcademicDocType.FEE_RECEIPT
    assert "college fee receipt or financial payment record" in res13["student_message"]
    print(f"  [PASS] Test 13: College Fee Receipt -> REJECTED (FEE_RECEIPT)")
    print(f"         Student Message: {res13['student_message'][:80]}...")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 14: Tuition Fee Receipt -> REJECTED (FEE_RECEIPT)
    # -------------------------------------------------------------------------
    tuition_receipt_text = """
    ST. XAVIER COLLEGE OF ADVANCED STUDIES
    FEE CHALLAN / TUITION FEE RECEIPT
    Challan No: CH-2026-5501 | Academic Year: 2026-2027
    Student Name: Priya Varma | Course: BCA Semester 5
    Tuition Fee: Rs. 45,000.00
    Lab & Practical Fee: Rs. 5,000.00
    Total Amount: Rs. 50,000.00
    Paid By: Net Banking | Bank Reference: HDFC-8921049281
    Status: Payment Received
    Accounts Clerk Signature: Authorized
    """
    res14 = validate_document_relevance_sync(tuition_receipt_text, title="Tuition Fee Challan", filename="Tuition_Fee_Receipt.pdf", selected_subject="Computer Science")
    assert res14["decision"] == "REJECTED" and res14["document_type"] == AcademicDocType.FEE_RECEIPT
    print(f"  [PASS] Test 14: Tuition Fee Receipt -> REJECTED (FEE_RECEIPT)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 15: Examination Fee Receipt -> REJECTED (FEE_RECEIPT)
    # -------------------------------------------------------------------------
    exam_fee_receipt = """
    STATE TECHNOLOGICAL UNIVERSITY - EXAMINATION BRANCH
    EXAMINATION FEE RECEIPT & HALL TICKET PAYMENT SLIP
    Receipt Number: EXAM-REC-2026-7819
    Student Registration: 1MS22CS104
    Semester: 6th Semester End Examination
    Exam Fee Amount Paid: Rs. 3,200.00
    Mode: Online Payment Gateway | Transaction Date: 02-11-2026
    Signature of Controller of Examinations
    """
    res15 = validate_document_relevance_sync(exam_fee_receipt, title="Exam Fee Receipt", filename="Exam_Fee_Receipt.pdf", selected_subject="Computer Science")
    assert res15["decision"] == "REJECTED" and res15["document_type"] == AcademicDocType.FEE_RECEIPT
    print(f"  [PASS] Test 15: Examination Fee Receipt -> REJECTED (FEE_RECEIPT)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 16: Hostel Fee Receipt -> REJECTED (FEE_RECEIPT)
    # -------------------------------------------------------------------------
    hostel_fee_receipt = """
    UNIVERSITY CAMPUS RESIDENCES
    HOSTEL AND MESS FEE RECEIPT
    Receipt No: HSTL-2026-092
    Resident: Karthik M. | Room No: B-204
    Hostel Rent: Rs. 35,000.00
    Mess Advance: Rs. 25,000.00
    Total Paid: Rs. 60,000.00
    Payment Successful via UPI Ref: 48920194829
    Warden Signature & Stamp Affixed
    """
    res16 = validate_document_relevance_sync(hostel_fee_receipt, title="Hostel Fee Receipt", filename="Hostel_Fee_Receipt.pdf", selected_subject="General")
    assert res16["decision"] == "REJECTED" and res16["document_type"] == AcademicDocType.FEE_RECEIPT
    print(f"  [PASS] Test 16: Hostel Fee Receipt -> REJECTED (FEE_RECEIPT)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 17: UPI Payment Screenshot / Digital Receipt -> REJECTED (PAYMENT_RECEIPT)
    # -------------------------------------------------------------------------
    upi_receipt_text = """
    Google Pay - Payment Receipt
    Payment Successful
    ₹2,450.00
    Paid to: University Bookstore & Stationery
    UPI Transaction ID: 429104820194
    To: bookdepot@okaxis
    Google Transaction ID: CICAgODV4-92KLA
    Debited from: State Bank of India (**** 4910)
    Payment Date: 10 Nov 2026, 02:45 PM
    UTR Number: 431092849102
    Order ID: ORD-99214-GPay
    """
    res17 = validate_document_relevance_sync(upi_receipt_text, title="Payment Receipt", filename="GooglePay_Receipt.pdf", selected_subject="Mathematics")
    assert res17["decision"] == "REJECTED" and res17["document_type"] == AcademicDocType.PAYMENT_RECEIPT
    assert "Financial documents, payment receipts, invoices" in res17["student_message"]
    print(f"  [PASS] Test 17: Digital Payment / UPI Transaction Receipt -> REJECTED (PAYMENT_RECEIPT)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 18: Bank Statement -> REJECTED (BANK_STATEMENT)
    # -------------------------------------------------------------------------
    bank_statement_text = """
    STATE BANK OF INDIA - STATEMENT OF ACCOUNT
    Account Holder: Ramesh Kumar
    Account Number: 00000039281749281 | Branch: MG Road Bangalore
    Statement Period: 01-10-2026 to 31-10-2026
    Opening Balance: Rs. 42,500.00
    05-10-2026 | UPI-COLLEGE-FEE | Withdrawal: Rs. 25,000.00 | Balance: Rs. 17,500.00
    12-10-2026 | NEFT-SALARY-CREDIT | Deposit: Rs. 65,000.00 | Balance: Rs. 82,500.00
    Closing Balance: Rs. 82,500.00
    """
    res18 = validate_document_relevance_sync(bank_statement_text, title="Bank Statement", filename="Bank_Statement_Oct2026.pdf", selected_subject="Finance")
    assert res18["decision"] == "REJECTED" and res18["document_type"] == AcademicDocType.BANK_STATEMENT
    print(f"  [PASS] Test 18: Bank Statement -> REJECTED (BANK_STATEMENT)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 19: College Admission Payment Receipt -> REJECTED (FEE_RECEIPT)
    # -------------------------------------------------------------------------
    admission_receipt_text = """
    APEX GLOBAL UNIVERSITY
    ADMISSION FEE PAYMENT RECEIPT
    Application No: AGU-ADM-2026-90412
    Candidate: Deepika S. | Admitted Program: M.Tech Computer Science
    Admission Fee: Rs. 1,20,000.00
    Registration Fee: Rs. 15,000.00
    Total Amount Paid: Rs. 1,35,000.00
    Transaction ID: TXN-ADMISSION-89214981
    Payment Status: Confirmed & Paid
    Authorized Signature: Registrar Admissions
    """
    res19 = validate_document_relevance_sync(admission_receipt_text, title="Admission Fee Receipt", filename="Admission_Receipt.pdf", selected_subject="Computer Science")
    assert res19["decision"] == "REJECTED" and res19["document_type"] == AcademicDocType.FEE_RECEIPT
    print(f"  [PASS] Test 19: College Admission Payment Receipt -> REJECTED (FEE_RECEIPT)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 20: Financial Accounting Textbook discussing Receipts & Invoices -> APPROVED
    # -------------------------------------------------------------------------
    accounting_textbook = """
    Chapter 6: Source Documents, Receipts, and Double-Entry Bookkeeping
    Course: Financial Accounting | Department of Commerce & Management Studies
    
    Learning Objectives:
    After studying this chapter, students will be able to:
    1. Define source documents and explain the significance of payment receipts and invoices in accounting.
    2. Understand how cash memos, purchase invoices, and debit notes are journalized.
    
    Section 6.1: The Concept of a Payment Receipt
    Definition: In financial accounting, a receipt is an objective documentary evidence proving that cash or 
    its electronic equivalent was received from a debtor or customer. A receipt serves as the prime source 
    document from which transactions are posted to the Cash Book.
    
    Section 6.2: Difference Between an Invoice and a Receipt
    While a sales invoice represents a bill demanding payment for goods delivered on credit, a payment receipt 
    is issued only after the actual settlement of monetary consideration has taken place.
    
    Review Questions:
    Q1. Explain the role of a voucher in establishing internal control over cash payments.
    Q2. How do auditors verify payments recorded in the cash book using stamped receipts?
    """
    res20 = validate_document_relevance_sync(accounting_textbook, title="Financial Accounting Chapter 6", filename="Accounting_Chapter_6.pdf", selected_subject="Accounting")
    assert res20["decision"] == "APPROVED" and res20["is_academic"] is True
    print(f"  [PASS] Test 20: Financial Accounting Textbook discussing Receipts -> APPROVED")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 21: Study Notes Discussing Payment Receipts in E-Commerce -> APPROVED
    # -------------------------------------------------------------------------
    ecommerce_notes = """
    Lecture 9: Electronic Commerce and Secure Digital Payment Systems
    Department of Information Technology | Web Engineering Series
    
    1. Payment System Architecture:
    In modern online transaction systems, payment gateways facilitate secure cryptographic handshake between 
    the merchant, customer, acquiring bank, and issuing bank. 
    
    2. Generation of Digital Payment Receipts:
    Definition: A digital payment receipt is a cryptographically signed JSON data payload generated upon 
    the successful settlement of a payment transaction. The receipt payload typically contains a unique 
    transaction hash, payment gateway token, amount, currency, and timestamp.
    
    3. Audit Trails and Ledger Verification:
    In electronic payment systems, maintaining verifiable logs of all generated invoices and payment receipts 
    is critical for non-repudiation and regulatory compliance.
    
    Review Questions:
    1. Describe how symmetric session keys protect payment credentials in transit.
    2. Explain how digital signatures guarantee the integrity of an electronic receipt.
    """
    res21 = validate_document_relevance_sync(ecommerce_notes, title="E-Commerce Payment Systems Lecture", filename="Ecommerce_Lecture_9.pdf", selected_subject="Computer Science")
    assert res21["decision"] == "APPROVED" and res21["is_academic"] is True
    print(f"  [PASS] Test 21: Study Notes Discussing Payment Receipts -> APPROVED")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 22: Scanned Academic Notes (OCR First) -> APPROVED
    # -------------------------------------------------------------------------
    scanned_notes_ocr = """
    Lecture 3: Newton's Laws of Motion and Classical Mechanics
    Department of Physics
    
    Newton's Second Law of Motion:
    The acceleration of an object is directly proportional to the net force acting upon it
    and inversely proportional to its mass.
    Formula: F = m * a
    Where F is force in Newtons (N), m is mass in kilograms (kg), and a is acceleration in m/s^2.
    
    Example Problem:
    Calculate the net force required to accelerate a 1500 kg vehicle at a rate of 2.5 m/s^2.
    Solution:
    F = 1500 kg * 2.5 m/s^2 = 3750 N.
    """
    res22 = validate_document_relevance_sync(scanned_notes_ocr, title="Scanned Physics Notes", filename="Physics_Newton_Scan.pdf", selected_subject="Physics", ocr_applied=True)
    assert res22["decision"] == "APPROVED" and res22["is_academic"] is True
    print(f"  [PASS] Test 22: Scanned Academic Notes (OCR First) -> APPROVED")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 23: User's Exact LMS Submission Receipt -> REJECTED (PAYMENT_RECEIPT)
    # -------------------------------------------------------------------------
    lms_receipt_text = "Your submission was successful! Course: Fall26_ASAC_CA_BCA_Semester_5_SecA_E1CAA401, Deep Learning Assessment: Project 13: CNN Architecture Comparison 10/6/26."
    res23 = validate_document_relevance_sync(
        text=lms_receipt_text,
        title="",
        filename="receipt-Fall26_ASAC_CA_BCA_Semester_5_SecA_E1CAA401.pdf",
        selected_subject="Computer Science"
    )
    assert res23["decision"] == "REJECTED" and res23["document_type"] == AcademicDocType.PAYMENT_RECEIPT
    assert "Financial documents, payment receipts, invoices" in res23["student_message"]
    print(f"  [PASS] Test 23: User's LMS Receipt (receipt-Fall26_ASAC_CA_BCA_Semester_5...) -> REJECTED")
    print(f"         Document Type: {res23['document_type']}")
    print(f"         Student Message: {res23['student_message']}")
    tests_passed += 1

    print("=" * 75)
    print(f"Result: ALL {tests_passed} REAL-WORLD VALIDATION SUITE TESTS PASSED PERFECTLY!")
    print("=" * 75)

    # =========================================================================
    # SECTION 7 FINAL TESTING: ALL 12 MANDATORY TEST CASES
    # =========================================================================
    print("\n" + "=" * 75)
    print("  SECTION 7 FINAL TESTING SUITE: 12 REQUIRED TEST CASES & CHATBOT ISOLATION")
    print("=" * 75)
    final_12_passed = 0

    # 1. Genuine mathematics notes – APPROVE
    math_notes = """
    Lecture 4: Linear Algebra and Matrix Transformations
    Department of Mathematics
    
    1. Eigenvalues and Eigenvectors:
    Definition: Let A be an n x n square matrix. A non-zero vector v is an eigenvector of A if there exists a scalar lambda such that:
    A * v = lambda * v
    Here, lambda is called the eigenvalue corresponding to eigenvector v.
    
    2. Characteristic Equation:
    To determine the eigenvalues of A, we solve the characteristic equation:
    det(A - lambda * I) = 0
    where I is the n x n identity matrix.
    
    3. Example Problem:
    Find the eigenvalues of matrix A = [[2, 1], [1, 2]].
    Step 1: Compute (A - lambda * I) = [[2 - lambda, 1], [1, 2 - lambda]].
    Step 2: Characteristic equation: (2 - lambda)^2 - 1 = 0.
    Solving gives lambda_1 = 3 and lambda_2 = 1.
    """
    r1 = validate_document_relevance_sync(math_notes, title="Linear Algebra Lecture 4", filename="Linear_Algebra_Notes.pdf", selected_subject="Mathematics")
    assert r1["decision"] == "APPROVED" and r1["is_academic"] is True
    print("  [PASS] 1. Genuine mathematics notes -> APPROVED")
    final_12_passed += 1

    # 2. Biology chapter PDF – APPROVE
    bio_chapter = """
    Chapter 3: Cell Biology and Cellular Respiration
    Department of Biological Sciences
    
    1. The Mitochondria and Cellular Energy:
    The mitochondrion is the power plant of eukaryotic cells, generating most of the cell's chemical energy in the form of Adenosine Triphosphate (ATP).
    
    2. Stages of Cellular Respiration:
    Cellular respiration proceeds through three distinct biochemical pathways:
    - Glycolysis: Takes place in the cytoplasm, breaking down one glucose molecule into two pyruvate molecules, yielding a net of 2 ATP and 2 NADH.
    - The Krebs Cycle (Citric Acid Cycle): Occurs in the mitochondrial matrix, oxidizing acetyl-CoA into carbon dioxide, generating NADH and FADH2.
    - The Electron Transport Chain (ETC): Located in the inner mitochondrial membrane, utilizing oxidative phosphorylation to generate approximately 30-32 ATP per glucose molecule.
    
    Review Questions:
    Q1. Describe the role of ATP synthase in chemiosmosis.
    Q2. Explain the biochemical difference between aerobic and anaerobic glycolysis.
    """
    r2 = validate_document_relevance_sync(bio_chapter, title="Chapter 3.pdf", filename="Chapter 3.pdf", selected_subject="Biology")
    assert r2["decision"] == "APPROVED" and r2["is_academic"] is True
    print("  [PASS] 2. Biology chapter PDF -> APPROVED")
    final_12_passed += 1

    # 3. Python programming notes – APPROVE
    python_notes = """
    Module 2: Python Data Structures and Algorithms
    Department of Computer Science & Engineering
    
    1. Object-Oriented Programming in Python:
    Classes provide a means of bundling data and functionality together. Creating a new class creates a new type of object, allowing new instances of that type to be made.
    
    2. Implementation of Binary Search:
    Definition: Binary search is an efficient algorithm for finding an item from a sorted list of items. It works by repeatedly dividing in half the portion of the list that could contain the item.
    
    Code Example:
    def binary_search(arr, target):
        low = 0
        high = len(arr) - 1
        while low <= high:
            mid = (low + high) // 2
            if arr[mid] == target:
                return mid
            elif arr[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
        return -1
    
    Complexity Analysis:
    Time Complexity: O(log n) where n is the number of elements in the sorted array.
    Space Complexity: O(1) for the iterative implementation.
    """
    r3 = validate_document_relevance_sync(python_notes, title="Python Data Structures", filename="Python_Module_2.pdf", selected_subject="Computer Science")
    assert r3["decision"] == "APPROVED" and r3["is_academic"] is True
    print("  [PASS] 3. Python programming notes -> APPROVED")
    final_12_passed += 1

    # 4. Previous-year question paper – APPROVE
    pyq_paper = """
    UNIVERSITY END SEMESTER EXAMINATION - NOVEMBER 2025
    B.Tech Degree Examination | Fifth Semester
    Branch: Computer Science and Engineering
    Subject: Database Management Systems (CS501)
    Time: 3 Hours                                                    Maximum Marks: 100
    
    PART A (Answer all questions, 10 x 2 = 20 Marks)
    1. Define 3NF and BCNF with suitable relational examples.
    2. What are the ACID properties in database transaction management?
    3. Differentiate between dense and sparse index structures.
    4. Explain the concept of write-ahead logging (WAL).
    
    PART B (Answer any 5 questions, 5 x 16 = 80 Marks)
    5. (a) Given the relation R(A, B, C, D, E) with functional dependencies:
       F = {A -> BC, CD -> E, B -> D, E -> A}. Find all candidate keys of R.
       (b) Normalize the relation R into Third Normal Form (3NF).
    """
    r4 = validate_document_relevance_sync(pyq_paper, title="DBMS University Question Paper", filename="DBMS_PYQ_2025.pdf", selected_subject="Computer Science")
    assert r4["decision"] == "APPROVED" and r4["is_academic"] is True
    print("  [PASS] 4. Previous-year question paper -> APPROVED")
    final_12_passed += 1

    # 5. College assignment – APPROVE
    assignment_doc = """
    Assignment 3: Operating Systems - CPU Scheduling and Memory Management
    Department of Information Technology | Semester 4
    Submission Due Date: October 28, 2026 | Total Marks: 25
    
    Problem 1 (10 Marks):
    Consider the following set of processes arriving at time 0 with given burst times:
    Process P1: 8 ms, P2: 4 ms, P3: 9 ms, P4: 5 ms.
    Draw Gantt charts and calculate average turnaround time and average waiting time for:
    (a) First-Come, First-Served (FCFS)
    (b) Shortest Job First (SJF) non-preemptive
    (c) Round Robin (RR) with time quantum = 4 ms.
    
    Problem 2 (15 Marks):
    Explain the paging mechanism used in modern operating systems to prevent external fragmentation.
    Include diagrams showing logical address translation using the Page Table Base Register (PTBR) and TLB cache hit workflow.
    """
    r5 = validate_document_relevance_sync(assignment_doc, title="OS Assignment 3", filename="OS_Assignment_3.pdf", selected_subject="Operating Systems")
    assert r5["decision"] == "APPROVED" and r5["is_academic"] is True
    print("  [PASS] 5. College assignment -> APPROVED")
    final_12_passed += 1

    # 6. Personal resume – REJECT
    resume_doc = """
    Rahul Sharma
    Email: rahul.sharma@gmail.com | Phone: +91 9876543210 | Bangalore, India
    LinkedIn: linkedin.com/in/rahulsharma | GitHub: github.com/rahulsharma
    
    CAREER OBJECTIVE:
    Motivated Computer Science graduate seeking a Software Development Engineer role to apply strong skills in Python, React, and Machine Learning.
    
    EDUCATION:
    - B.Tech in Computer Science and Engineering, ABC Institute of Technology (2022 - 2026) | CGPA: 8.9/10
    - Higher Secondary School, CBSE (2020 - 2022) | Percentage: 94%
    
    TECHNICAL SKILLS:
    - Languages: Python, C++, Java, JavaScript, SQL
    - Frameworks: FastAPI, Django, React, PyTorch
    - Tools: Git, Docker, Kubernetes, AWS
    
    WORK EXPERIENCE:
    Software Engineering Intern | XYZ Tech Solutions (Jan 2026 - Present)
    - Built scalable REST APIs using FastAPI handling 50,000 daily requests.
    - Optimized database indexing in MongoDB reducing query latency by 35%.
    
    PROJECTS:
    - CampusVerse Notes Platform: Developed full-stack educational app with RAG search.
    
    DECLARATION:
    I hereby declare that all information stated above is true to the best of my knowledge.
    """
    r6 = validate_document_relevance_sync(resume_doc, title="Python Notes.pdf", filename="Python Notes.pdf", selected_subject="Python")
    assert r6["decision"] == "REJECTED" and r6["document_type"] in [AcademicDocType.RESUME, AcademicDocType.RESUME_CV]
    assert "CampusVerse only accepts academic study materials. This document appears to be a personal resume" in r6["student_message"]
    print(f"  [PASS] 6. Personal resume ('Python Notes.pdf' with resume) -> REJECTED")
    print(f"         Student Message: {r6['student_message']}")
    final_12_passed += 1

    # 7. Cooking recipe – REJECT
    recipe_doc = """
    Delicious Homemade Italian Lasagna Recipe
    Prep Time: 30 minutes | Cook Time: 50 minutes | Servings: 8 servings
    
    Ingredients:
    - 1 pound sweet Italian sausage
    - 1 pound lean ground beef
    - 1 cup minced onion
    - 2 cloves garlic, crushed
    - 1 can (28 ounces) crushed tomatoes
    - 2 tablespoons chopped fresh parsley
    - 1 teaspoon dried basil leaves
    - 1/2 teaspoon salt
    - 12 lasagna noodles
    - 16 ounces ricotta cheese
    - 1 egg
    - 4 cups shredded mozzarella cheese
    
    Cooking Instructions:
    Step 1: In a Dutch oven, cook sausage, beef, onion, and garlic over medium heat until well browned.
    Step 2: Stir in crushed tomatoes, parsley, basil, and salt. Simmer over low heat for about 25 minutes.
    Step 3: Preheat the oven to 375 degrees F (190 degrees C).
    Step 4: Layer lasagna noodles, meat sauce, ricotta cheese, and mozzarella cheese in a 9x13 inch baking dish.
    Step 5: Bake in the preheated oven for 50 minutes until golden brown and bubbling. Let stand 15 minutes before serving.
    """
    r7 = validate_document_relevance_sync(recipe_doc, title="Italian Lasagna Recipe", filename="Lasagna_Recipe.pdf", selected_subject="Culinary")
    assert r7["decision"] == "REJECTED" and r7["document_type"] == AcademicDocType.COOKING_RECIPE
    assert "This document contains cooking-related content rather than academic study material" in r7["student_message"]
    print(f"  [PASS] 7. Cooking recipe -> REJECTED")
    print(f"         Student Message: {r7['student_message']}")
    final_12_passed += 1

    # 8. Internship completion certificate – REJECT
    internship_cert = """
    CERTIFICATE OF INTERNSHIP COMPLETION
    This is to certify that Mr. Aditya Verma has successfully completed his 3-month Software Development Internship
    at Horizon Technologies Pvt Ltd from June 1, 2026 to August 31, 2026.
    During the internship period, he worked diligently on our Cloud Infrastructure team and exhibited excellent technical competence.
    We wish him all the best in his future professional endeavors.
    Awarded on: 31st August 2026 | Certificate ID: HT-INT-2026-4401
    Authorized Signature: Rajesh Kumar
    Vice President - Engineering
    Official Corporate Seal Affixed
    """
    r8 = validate_document_relevance_sync(internship_cert, title="Aditya Internship Certificate", filename="Internship_Certificate.pdf", selected_subject="Computer Science")
    assert r8["decision"] == "REJECTED" and r8["document_type"] in [AcademicDocType.CERTIFICATE, AcademicDocType.INTERNSHIP_CERTIFICATE]
    assert "Internship certificates and employment documents are not accepted as study materials" in r8["student_message"]
    print(f"  [PASS] 8. Internship completion certificate -> REJECTED")
    print(f"         Student Message: {r8['student_message']}")
    final_12_passed += 1

    # 9. Job application – REJECT
    job_app = """
    To,
    The Head of Human Resources
    Global Software Solutions Ltd.
    Bangalore, India
    
    Date: October 12, 2026
    Subject: Application for the position of Junior Data Engineer (Job ID: DE-2026-09)
    
    Dear Sir/Madam,
    
    I am writing to express my strong interest in applying for the post of Junior Data Engineer at your esteemed organization.
    Having completed my coursework in database systems, distributed computing, and data pipelines, I have developed solid foundational knowledge in ETL workflows and SQL performance tuning.
    
    Please find my enclosed resume and academic transcripts for your review and consideration. I welcome the opportunity to discuss how my skill set aligns with your team's objectives.
    
    Thank you for your time and consideration of my candidature.
    
    Yours sincerely,
    Sneha Kulkarni
    Phone: +91 9988776655
    """
    r9 = validate_document_relevance_sync(job_app, title="Sneha Job Application", filename="Job_Application_Cover_Letter.pdf", selected_subject="Computer Science")
    assert r9["decision"] == "REJECTED" and r9["document_type"] in [AcademicDocType.JOB_APPLICATION, AcademicDocType.PERSONAL_CORRESPONDENCE]
    assert "Job applications and employment-related documents are not accepted" in r9["student_message"]
    print(f"  [PASS] 9. Job application -> REJECTED")
    print(f"         Student Message: {r9['student_message']}")
    final_12_passed += 1

    # 10. College fee receipt – REJECT
    fee_receipt = """
    ST. XAVIER'S COLLEGE OF ENGINEERING & TECHNOLOGY
    STUDENT TUITION & HOSTEL FEE RECEIPT (OFFICE COPY)
    Receipt No: RCPT-2026-88192                                      Date: 14/08/2026
    Student Name: Vikram Mehra                                      Enrollment No: EN22CS104
    Branch / Course: B.Tech Computer Science                        Semester: Semester 5
    
    Fee Particulars:
    1. Tuition Fee (Odd Semester 2026-27):                          Rs. 45,000.00
    2. Laboratory & Practical Consumables:                           Rs.  6,500.00
    3. Library & Electronic Journal Subscription:                    Rs.  2,500.00
    4. Examination & Assessment Fee:                                Rs.  3,000.00
    5. Hostel & Mess Dues:                                          Rs. 28,000.00
    Total Amount Paid:                                              Rs. 85,000.00
    Payment Mode: Online / UPI Ref: 2026081498129031
    Payment Status: Payment Successful
    
    Seal & Signature of Cashier
    Accounts Department
    Fees once paid are non-refundable.
    """
    r10 = validate_document_relevance_sync(fee_receipt, title="Vikram Fee Receipt", filename="College_Fee_Receipt.pdf", selected_subject="Engineering")
    assert r10["decision"] == "REJECTED" and r10["document_type"] == AcademicDocType.FEE_RECEIPT
    assert "college fee receipt or financial payment record" in r10["student_message"]
    print(f"  [PASS] 10. College fee receipt -> REJECTED")
    print(f"          Student Message: {r10['student_message']}")
    final_12_passed += 1

    # 11. Random personal document – REJECT
    random_personal = """
    My Personal Vacation Packing List and Weekend Plans
    Summer Trip 2026 - Goa Beach Getaway
    
    Items to pack:
    - 3 pairs of swimming trunks and board shorts
    - Ray-Ban sunglasses and sunscreen lotion SPF 50
    - Waterproof camera with extra SD cards
    - Portable Bluetooth speaker and power bank
    - Casual evening shirts, flip-flops, and beach towel
    
    Weekend Itinerary:
    Friday: Reach hotel at 3 PM, check in, head straight to Baga beach for sunset snacks and coconut water.
    Saturday: Rent a scooter, explore the old Portuguese forts, visit Anjuna flea market, and have seafood dinner.
    Sunday: Lazy morning breakfast by the pool, souvenir shopping, and pack bags for evening flight back home.
    """
    r11 = validate_document_relevance_sync(random_personal, title="Goa Trip Plans", filename="Vacation_Plans.pdf", selected_subject="General")
    assert r11["decision"] == "REJECTED"
    print(f"  [PASS] 11. Random personal document -> REJECTED")
    print(f"          Student Message: {r11['student_message']}")
    final_12_passed += 1

    # 12. Mixed academic and personal document – NEEDS REVIEW
    mixed_doc = """
    Dear Diary,
    Today was a really tiring day. I woke up at 7 AM and went for a long jog in the park.
    Afterwards, I felt overwhelmed by my upcoming exams and wrote down these thoughts.
    I miss hanging out with my friends on weekends and watching movies all night.
    
    Here are the study points I reviewed in between my breaks:
    1. Definition: An algorithm is a finite sequence of well-defined computer-implementable instructions.
    2. The time complexity of bubble sort in worst case is O(n^2).
    3. In a binary tree, each node has at most two children referred to as the left child and right child.
    
    I need to plan my weekend road trip with cousins once this semester is over. Hopefully I can get some sleep tonight.
    """
    r12 = validate_document_relevance_sync(mixed_doc, title="Diary and Algorithm Points", filename="Diary_Study_Notes.pdf", selected_subject="Computer Science")
    assert r12["decision"] in ["NEEDS_REVIEW", "REJECTED"]
    print(f"  [PASS] 12. Mixed academic and personal document -> {r12['decision']}")
    print(f"          Student Message: {r12['student_message']}")
    final_12_passed += 1

    # -------------------------------------------------------------------------
    # VERIFY CHATBOT ISOLATION: Rejected documents CANNOT be retrieved via chatbot
    # -------------------------------------------------------------------------
    print("\n  [VERIFY] Testing Chatbot Isolation for Rejected Content...")
    from app.routers.chat import get_available_chat_materials, create_chat_session, CreateSessionRequest
    from app.mock_db import mock_db_instance
    import asyncio

    async def verify_chatbot():
        # Insert a sample rejected document into mock_db
        rej_id = "test_rejected_doc_12345"
        await mock_db_instance["materials"].insert_one({
            "_id": rej_id,
            "id": rej_id,
            "title": "Rejected Personal Resume",
            "status": "REJECTED",
            "uploader": "test_user_1",
            "academicCategory": "Computer Science"
        })

        # Test 1: Available chat materials must NOT list the rejected material
        chat_mats_res = await get_available_chat_materials(
            current_user={"id": "test_user_1", "role": "student"},
            db=mock_db_instance
        )
        chat_mat_ids = [m["id"] for m in chat_mats_res["materials"]]
        assert rej_id not in chat_mat_ids, "Security breach: Rejected material was returned in chat materials list!"
        print("  [PASS] Chatbot Isolation: Rejected document does NOT appear in available chat materials list.")

        # Test 2: Attempting to create a chat session with the rejected material MUST fail with HTTP 400
        session_blocked = False
        try:
            await create_chat_session(
                payload=CreateSessionRequest(materialIds=[rej_id]),
                current_user={"id": "test_user_1", "role": "student"},
                db=mock_db_instance
            )
        except Exception as exc:
            session_blocked = True
            assert "rejected" in str(exc.detail).lower() or "academic" in str(exc.detail).lower()
            print(f"  [PASS] Chatbot Isolation: Session creation with rejected document blocked: {exc.detail}")

        assert session_blocked is True, "Security breach: Session created with rejected material!"

    asyncio.run(verify_chatbot())

    print("=" * 75)
    print(f"SUCCESS: ALL {final_12_passed}/12 MANDATORY TEST CASES AND CHATBOT ISOLATION VERIFIED!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
