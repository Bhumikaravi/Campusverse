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
    assert res1["decision"] == "REJECTED" and res1["document_type"] == AcademicDocType.CERTIFICATE
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

if __name__ == "__main__":
    run_tests()
