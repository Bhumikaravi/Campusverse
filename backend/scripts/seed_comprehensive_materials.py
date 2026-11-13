"""Seed comprehensive real study materials with physical files and MongoDB database records.
Ensures every main category has its own distinct subcategories, topics, and real readable files.
"""

import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
UPLOADS_DIR = BACKEND_DIR / "uploads" / "materials"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Document generation libraries
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from docx import Document
from pptx import Presentation

def create_pdf(file_path: Path, title: str, subtitle: str, category: str, subcategory: str, topic: str, content_sections: list):
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=15
    )
    heading_style = ParagraphStyle(
        'DocH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(subtitle, subtitle_style))
    story.append(Paragraph(f"<b>CampusVerse Academic Library</b> &bull; {category} &gt; {subcategory} &gt; <b>{topic}</b>", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=15))

    for h, p in content_sections:
        story.append(Paragraph(h, heading_style))
        story.append(Paragraph(p, body_style))
        story.append(Spacer(1, 4))

    doc.build(story)
    return file_path.stat().st_size

def create_docx(file_path: Path, title: str, subtitle: str, category: str, subcategory: str, topic: str, content_sections: list):
    doc = Document()
    doc.add_heading(title, level=0)
    p_meta = doc.add_paragraph()
    p_meta.add_run(f"CampusVerse Verified Notes | {category} > {subcategory} > {topic}\n").bold = True
    p_meta.add_run(subtitle).italic = True

    for h, p in content_sections:
        doc.add_heading(h, level=1)
        doc.add_paragraph(p)

    doc.save(str(file_path))
    return file_path.stat().st_size

def create_pptx(file_path: Path, title: str, subtitle: str, category: str, subcategory: str, topic: str, content_sections: list):
    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title_box = slide.shapes.title
    sub_box = slide.placeholders[1]
    title_box.text = title
    sub_box.text = f"{category} | {subcategory}\nTopic: {topic}\n{subtitle}"

    bullet_slide_layout = prs.slide_layouts[1]
    for h, p in content_sections:
        s = prs.slides.add_slide(bullet_slide_layout)
        s.shapes.title.text = h
        tf = s.placeholders[1].text_frame
        tf.text = p

    prs.save(str(file_path))
    return file_path.stat().st_size

STUDY_MATERIALS_CATALOG = [
    # -------------------------------------------------------------
    # 1. GENERAL MEDICINE
    # -------------------------------------------------------------
    {
        "fileName": "med_cardio_hypertension_clinical_guide.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Clinical Practice Guidelines for Hypertension Management",
        "subject": "Cardiology",
        "mainCategory": "General Medicine",
        "subcategory": "Cardiology",
        "topic": "Hypertension",
        "department": "General Medicine",
        "semester": 4,
        "category": "notes",
        "rating": 5.0,
        "ratingCount": 42,
        "downloads": 680,
        "uploaderName": "Dr. Ramesh Menon (Dept of Medicine)",
        "description": "Comprehensive clinical practice guideline covering ACC/AHA diagnostic staging, secondary hypertension etiologies, first-line antihypertensive drugs, and crisis protocols.",
        "content": [
            ("1. Diagnostic Criteria & Blood Pressure Classification",
             "According to the ACC/AHA guidelines, normal resting blood pressure is defined as systolic < 120 mmHg and diastolic < 80 mmHg. Stage 1 hypertension is defined as SBP 130-139 mmHg or DBP 80-89 mmHg. Stage 2 hypertension is defined as SBP >= 140 mmHg or DBP >= 90 mmHg based on an average of two or more properly measured seated BP readings on separate occasions."),
            ("2. Primary vs. Secondary Etiologies",
             "Primary (essential) hypertension accounts for over 90% of cases and involves a multifactorial interplay of renal sodium excretion, sympathetic nervous system overactivity, and renin-angiotensin-aldosterone system (RAAS) dysregulation. Secondary causes: renal artery stenosis, primary aldosteronism, pheochromocytoma, and Cushing syndrome."),
            ("3. First-Line Pharmacotherapy",
             "The four primary drug classes recommended include: ACE inhibitors (Lisinopril), Angiotensin II Receptor Blockers (Losartan), Calcium Channel Blockers (Amlodipine), and Thiazide-like diuretics (Chlorthalidone). In diabetic patients, ACEi/ARBs provide essential renal protection by dilating efferent arterioles.")
        ]
    },
    {
        "fileName": "med_cardio_ecg_interpretation_handbook.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Systematic 12-Lead ECG Interpretation Handbook",
        "subject": "Cardiology",
        "mainCategory": "General Medicine",
        "subcategory": "Cardiology",
        "topic": "ECG interpretation",
        "department": "General Medicine",
        "semester": 4,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 58,
        "downloads": 820,
        "uploaderName": "Dr. A. K. Sundaram (Cardiologist)",
        "description": "Step-by-step 12-lead ECG analysis guide covering rate calculation, cardiac axis, bundle branch blocks, STEMI localizations, and ventricular arrhythmias.",
        "content": [
            ("1. Systematic ECG Reading Framework",
             "A disciplined 7-step method prevents missed pathology: 1) Rate (300 divided by number of large boxes between R-R intervals), 2) Rhythm (sinus vs ectopic), 3) Cardiac Axis (Lead I and aVF analysis: normal -30 to +90 deg), 4) PR Interval (120-200 ms), 5) QRS duration (< 120 ms), 6) ST Segment elevation/depression, and 7) T wave morphology."),
            ("2. Acute Coronary Syndrome Localizations",
             "ST-elevation myocardial infarction (STEMI) localizes anatomically according to lead groupings: Anterior wall infarction involves Leads V1-V4 (LAD artery); Lateral wall infarction involves Leads I, aVL, V5, V6 (Left Circumflex); Inferior wall infarction involves Leads II, III, aVF (Right Coronary Artery).")
        ]
    },
    {
        "fileName": "med_clinical_history_taking_framework.docx",
        "fileType": "docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "title": "Comprehensive Medical History Taking & Review of Systems",
        "subject": "General Medicine and Clinical Practice",
        "mainCategory": "General Medicine",
        "subcategory": "General Medicine and Clinical Practice",
        "topic": "Patient history taking",
        "department": "General Medicine",
        "semester": 3,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 35,
        "downloads": 540,
        "uploaderName": "Dr. Priya V. (Clinical Tutor)",
        "description": "Standard medical history taking protocol covering chief complaints, history of present illness (SOCRATES framework), comorbidities, and systemic reviews.",
        "content": [
            ("1. Patient Introduction and Chief Complaint",
             "Establish rapport, confirm patient identity, age, and occupation. Record the chief complaint in the patient's own concise words along with exact chronological duration."),
            ("2. History of Present Illness (SOCRATES Framework)",
             "For pain and major symptoms, apply the SOCRATES mnemonic: Site, Onset, Character, Radiation, Associations, Timing, Exacerbating/Relieving factors, and Severity (1 to 10 scale).")
        ]
    },
    {
        "fileName": "med_respiratory_asthma_copd_guidelines.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Asthma Pathophysiology, Spirometry & GINA Stepwise Therapy",
        "subject": "Respiratory Medicine",
        "mainCategory": "General Medicine",
        "subcategory": "Respiratory Medicine",
        "topic": "Asthma",
        "department": "General Medicine",
        "semester": 4,
        "category": "notes",
        "rating": 4.8,
        "ratingCount": 44,
        "downloads": 710,
        "uploaderName": "Dr. Sarah Thomas (Pulmonology)",
        "description": "Detailed lecture notes covering bronchial hyperresponsiveness, spirometric FEV1/FVC reversibility criteria, inhaler therapy, and acute exacerbation management.",
        "content": [
            ("1. Pathophysiology of Bronchial Asthma",
             "Asthma is a chronic inflammatory disorder of the conducting airways characterized by bronchial hyperresponsiveness, reversible airflow obstruction, eosinophilic infiltration, and goblet cell hyperplasia resulting in mucous plugging."),
            ("2. Spirometry & Reversibility Testing",
             "Diagnostic confirmation requires demonstrating airflow limitation (reduced FEV1/FVC ratio < 0.70) with significant bronchodilator reversibility: an increase in FEV1 by >= 12% and >= 200 mL measured 15 minutes post albuterol inhalation.")
        ]
    },
    {
        "fileName": "med_endocrine_diabetes_clinical_protocol.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Type 1 & Type 2 Diabetes Mellitus Management Protocols",
        "subject": "Endocrinology",
        "mainCategory": "General Medicine",
        "subcategory": "Endocrinology",
        "topic": "Diabetes mellitus",
        "department": "General Medicine",
        "semester": 5,
        "category": "notes",
        "rating": 5.0,
        "ratingCount": 61,
        "downloads": 940,
        "uploaderName": "Dr. K. N. Rao (Endocrinology)",
        "description": "Clinical practice notes on glycemic targets, HbA1c diagnostic cutoffs, oral hypoglycemic agents, basal-bolus insulin regimens, and diabetic ketoacidosis.",
        "content": [
            ("1. Diagnostic Criteria & Glycemic Targets",
             "Diabetes mellitus is diagnosed when: Fasting Plasma Glucose >= 126 mg/dL (7.0 mmol/L), 2-hour post 75g OGTT >= 200 mg/dL, HbA1c >= 6.5%, or classic symptoms with random glucose >= 200 mg/dL."),
            ("2. Pharmacological Armamentarium",
             "Metformin remains the foundational first-line agent. SGLT2 inhibitors (Empagliflozin, Dapagliflozin) provide established cardio-renal protection, while GLP-1 receptor agonists promote weight reduction.")
        ]
    },

    # -------------------------------------------------------------
    # 2. COMPUTER SCIENCE AND ENGINEERING
    # -------------------------------------------------------------
    {
        "fileName": "cse_dsa_balanced_trees_graphs_notes.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "AVL Trees, Red-Black Trees & Binary Search Tree Implementations",
        "subject": "Data Structures and Algorithms",
        "mainCategory": "Computer Science and Engineering",
        "subcategory": "Data Structures and Algorithms",
        "topic": "Trees & Binary Search Trees",
        "department": "Computer Science and Engineering",
        "semester": 3,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 89,
        "downloads": 1420,
        "uploaderName": "Bhumika Ravi (Dept of CSE)",
        "description": "Complete notes covering BST insertion/deletion, AVL balance factor calculations and rotations, time complexity analysis, and practice coding problems.",
        "content": [
            ("1. Binary Search Tree (BST) Properties",
             "For every node X, left subtree keys are strictly less than X.key, and right subtree keys are strictly greater. Inorder traversal yields sorted sequence. In degenerate trees, search time degrades to O(N)."),
            ("2. AVL Self-Balancing Trees",
             "AVL trees maintain Balance Factor (height(left) - height(right)) in {-1, 0, +1}. Imbalances are resolved via 4 rotation types: Left-Left (Single Right), Right-Right (Single Left), Left-Right, and Right-Left.")
        ]
    },
    {
        "fileName": "cse_dbms_sql_normalization_guide.docx",
        "fileType": "docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "title": "Relational Database Normalization: 1NF, 2NF, 3NF & BCNF Guide",
        "subject": "Database Management Systems",
        "mainCategory": "Computer Science and Engineering",
        "subcategory": "Database Management Systems",
        "topic": "Normalization (1NF to BCNF)",
        "department": "Computer Science and Engineering",
        "semester": 4,
        "category": "notes",
        "rating": 4.8,
        "ratingCount": 74,
        "downloads": 1180,
        "uploaderName": "Aarav Sharma (CSE)",
        "description": "Formal functional dependency theory, Armstrong's axioms, lossless join decomposition, dependency preservation proofs, and BCNF case problems.",
        "content": [
            ("1. Functional Dependencies & Normal Forms",
             "1NF requires atomic attribute values. 2NF removes partial dependencies where a non-prime attribute depends on a subset of a candidate key. 3NF removes transitive dependencies."),
            ("2. Boyce-Codd Normal Form (BCNF)",
             "A relation is in BCNF if for every non-trivial functional dependency X -> A, X is strictly a superkey. BCNF eliminates all redundancy based on functional dependencies.")
        ]
    },
    {
        "fileName": "cse_os_cpu_scheduling_deadlocks.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "CPU Scheduling Algorithms & Deadlock Banker's Protocol",
        "subject": "Operating Systems",
        "mainCategory": "Computer Science and Engineering",
        "subcategory": "Operating Systems",
        "topic": "Process Scheduling & Deadlocks",
        "department": "Computer Science and Engineering",
        "semester": 4,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 92,
        "downloads": 1350,
        "uploaderName": "Sneha Patel (CSE)",
        "description": "Mathematical problems and Gantt charts for FCFS, Shortest Job First, Round Robin, Coffman deadlock conditions, and Banker's safety algorithm.",
        "content": [
            ("1. CPU Scheduling Metrics & Algorithms",
             "Scheduling criteria evaluate CPU utilization, throughput, turnaround time, waiting time, and response time. Preemptive algorithms include Shortest Remaining Time First (SRTF) and Round Robin (RR)."),
            ("2. Deadlock Coffman Conditions & Banker's Algorithm",
             "Deadlock requires: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait. Banker's Algorithm ensures resource allocations only transition between safe states.")
        ]
    },
    {
        "fileName": "cse_networks_tcp_ip_osi_architecture.pptx",
        "fileType": "pptx",
        "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "title": "OSI Reference Model vs TCP/IP Protocol Architecture",
        "subject": "Computer Networks",
        "mainCategory": "Computer Science and Engineering",
        "subcategory": "Computer Networks",
        "topic": "OSI vs TCP/IP Protocol Stack",
        "department": "Computer Science and Engineering",
        "semester": 5,
        "category": "slides",
        "rating": 4.8,
        "ratingCount": 63,
        "downloads": 980,
        "uploaderName": "Prof. S. R. Chawla (Networks Lab)",
        "description": "Comprehensive presentation deck comparing 7-layer OSI model functions with 4-layer TCP/IP suite, packet encapsulation, and IP subnetting.",
        "content": [
            ("1. Protocol Stack Comparisons",
             "Comparison between the theoretical 7-layer OSI model and the pragmatic 4-layer TCP/IP Internet stack (Network Interface, Internet, Transport, Application)."),
            ("2. Transport Protocols: TCP vs UDP",
             "TCP offers reliable byte-stream transmission with a 3-way handshake and sliding-window flow control. UDP offers low-latency connectionless datagram delivery.")
        ]
    },
    {
        "fileName": "cse_cybersecurity_cryptography_pki.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Public Key Cryptography, RSA Math & Web PKI Security",
        "subject": "Cybersecurity",
        "mainCategory": "Computer Science and Engineering",
        "subcategory": "Cybersecurity",
        "topic": "Cryptography & Public Key Infrastructure",
        "department": "Computer Science and Engineering",
        "semester": 6,
        "category": "notes",
        "rating": 5.0,
        "ratingCount": 54,
        "downloads": 790,
        "uploaderName": "Cyber Security Cell",
        "description": "Mathematical foundations of asymmetric RSA encryption, Diffie-Hellman key exchange, SHA-256 digital signatures, and X.509 certificate chains.",
        "content": [
            ("1. Asymmetric Cryptography and RSA",
             "RSA security relies on the hardness of factoring large semiprimes n = p * q. Key generation uses Euler's totient phi(n) = (p-1)*(q-1) to compute public exponent e and private key d."),
            ("2. Public Key Infrastructure (PKI) & TLS",
             "X.509 certificates bind public keys to validated domains via Certificate Authorities. Modern TLS 1.3 leverages ephemeral Diffie-Hellman (ECDHE) for Perfect Forward Secrecy.")
        ]
    },

    # -------------------------------------------------------------
    # 3. CIVIL ENGINEERING
    # -------------------------------------------------------------
    {
        "fileName": "civil_structural_rcc_beam_design.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Limit State Design of Singly & Doubly Reinforced RCC Beams",
        "subject": "Structural Engineering",
        "mainCategory": "Civil Engineering",
        "subcategory": "Structural Engineering",
        "topic": "Reinforced Concrete Design (RCC)",
        "department": "Civil Engineering",
        "semester": 5,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 47,
        "downloads": 730,
        "uploaderName": "Er. Vikram Rathore (Structures)",
        "description": "IS 456 code-compliant structural design manual covering neutral axis depth, moment of resistance, shear stirrup spacing, and crack control.",
        "content": [
            ("1. Limit State Design Principles (IS 456:2000)",
             "Ensures safety against bending and shear collapse and serviceability deflection limits (span/250). Limiting neutral axis Xu,max / d is 0.48 for Fe 415 steel."),
            ("2. Under-Reinforced Rectangular Sections",
             "Under-reinforced sections ensure tension steel yields prior to concrete crushing, providing ductile warning before ultimate failure occurs.")
        ]
    },
    {
        "fileName": "civil_geotech_soil_mechanics_foundations.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Mohr-Coulomb Shear Strength & Shallow Foundation Design",
        "subject": "Geotechnical Engineering",
        "mainCategory": "Civil Engineering",
        "subcategory": "Geotechnical Engineering",
        "topic": "Soil Mechanics & Shear Strength",
        "department": "Civil Engineering",
        "semester": 4,
        "category": "notes",
        "rating": 4.8,
        "ratingCount": 38,
        "downloads": 610,
        "uploaderName": "Dr. Manjunath (Geotech)",
        "description": "Direct shear and triaxial shear test interpretations, Terzaghi's bearing capacity equations, consolidation settlement, and footing design.",
        "content": [
            ("1. Mohr-Coulomb Failure Criterion",
             "Shear strength tau_f = c' + sigma' * tan(phi'), balancing effective cohesion c' and internal friction angle phi' derived from triaxial tests."),
            ("2. Terzaghi's Bearing Capacity Equations",
             "For shallow footings, ultimate bearing capacity qu = c*Nc + gamma*Df*Nq + 0.5*gamma*B*N_gamma with safety factor 2.5 to 3.0.")
        ]
    },

    # -------------------------------------------------------------
    # 4. MECHANICAL ENGINEERING
    # -------------------------------------------------------------
    {
        "fileName": "mech_thermo_laws_rankine_cycles.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "First & Second Laws of Thermodynamics and Vapor Power Cycles",
        "subject": "Thermodynamics",
        "mainCategory": "Mechanical Engineering",
        "subcategory": "Thermodynamics",
        "topic": "Laws of Thermodynamics",
        "department": "Mechanical Engineering",
        "semester": 3,
        "category": "notes",
        "rating": 5.0,
        "ratingCount": 65,
        "downloads": 890,
        "uploaderName": "Prof. Harish B. (Thermal Engg)",
        "description": "Comprehensive notes covering closed and open steady-flow energy equations, Clausius inequality, entropy generation, and reheat Rankine cycles.",
        "content": [
            ("1. First and Second Laws of Thermodynamics",
             "Steady Flow Energy Equation: h1 + (V1^2)/2 + gz1 + q = h2 + (V2^2)/2 + gz2 + w. Carnot maximum efficiency eta = 1 - (TL/TH)."),
            ("2. Rankine Vapor Power Cycle",
             "The standard cycle comprises pump compression, boiler heat addition, turbine expansion, and condenser rejection, enhanced by reheat.")
        ]
    },
    {
        "fileName": "mech_fluid_mechanics_navier_stokes.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Navier-Stokes Equations, Boundary Layer Separation & Drag",
        "subject": "Fluid Mechanics",
        "mainCategory": "Mechanical Engineering",
        "subcategory": "Fluid Mechanics",
        "topic": "Boundary Layer Theory",
        "department": "Mechanical Engineering",
        "semester": 4,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 51,
        "downloads": 760,
        "uploaderName": "Dr. S. K. Roy (Fluid Dynamics)",
        "description": "Differential Navier-Stokes derivations, Prandtl boundary layer equations, momentum thickness, flow separation control, and lift-to-drag curves.",
        "content": [
            ("1. Navier-Stokes Momentum Equations",
             "Balances inertial forces against pressure gradients and viscous diffusion: rho*(DV/Dt) = -grad(p) + mu*nabla^2(V) + rho*g."),
            ("2. Prandtl Boundary Layer Theory",
             "Viscous deceleration is confined to a thin layer delta near solid boundaries. Adverse pressure gradients trigger boundary layer separation.")
        ]
    },

    # -------------------------------------------------------------
    # 5. ELECTRICAL AND ELECTRONICS ENGINEERING
    # -------------------------------------------------------------
    {
        "fileName": "eee_machines_induction_transformers.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Three-Phase Induction Motor Torque-Speed & Equivalent Circuit",
        "subject": "Electrical Machines",
        "mainCategory": "Electrical and Electronics Engineering",
        "subcategory": "Electrical Machines",
        "topic": "Induction Motors (Single & 3-Phase)",
        "department": "Electrical and Electronics Engineering",
        "semester": 4,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 49,
        "downloads": 720,
        "uploaderName": "Prof. N. Venkatesh (Machines)",
        "description": "Rotating magnetic field theory, per-phase equivalent circuit derivation, maximum breakdown torque formulas, and circle diagram analysis.",
        "content": [
            ("1. Rotating Magnetic Field & Slip",
             "Three-phase stator winding currents displaced by 120 deg establish a constant magnitude flux rotating at synchronous speed Ns = 120*f/P."),
            ("2. Torque-Slip Characteristic",
             "Torque is proportional to s*E2^2*R2 / (R2^2 + (s*X2)^2). Maximum breakdown torque occurs at slip s_max = R2 / X2.")
        ]
    },
    {
        "fileName": "eee_power_systems_faults_stability.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Symmetrical Components & Power Transmission Line Faults",
        "subject": "Power Systems",
        "mainCategory": "Electrical and Electronics Engineering",
        "subcategory": "Power Systems",
        "topic": "Fault Analysis & Symmetrical Components",
        "department": "Electrical and Electronics Engineering",
        "semester": 5,
        "category": "notes",
        "rating": 5.0,
        "ratingCount": 43,
        "downloads": 640,
        "uploaderName": "Dr. T. G. Prasad (Power Systems)",
        "description": "Fortescue transformation for positive/negative/zero sequences, single line-to-ground (SLG) fault calculation, and synchronous swing equation.",
        "content": [
            ("1. Fortescue Symmetrical Components",
             "Unbalanced three-phase phasors are resolved into Positive (a-b-c), Negative (a-c-b), and Zero sequence components."),
            ("2. Transmission Fault Analysis",
             "Single line-to-ground fault current If = 3 * Ea / (Z1 + Z2 + Z0 + 3*Zf), modeled by series connection of the sequence networks.")
        ]
    },

    # -------------------------------------------------------------
    # 6. BUSINESS AND MANAGEMENT
    # -------------------------------------------------------------
    {
        "fileName": "mgmt_corporate_finance_capital_budgeting.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Capital Budgeting: Net Present Value (NPV), IRR & Cost of Capital",
        "subject": "Financial Management",
        "mainCategory": "Business and Management",
        "subcategory": "Financial Management",
        "topic": "Corporate Finance & Capital Budgeting",
        "department": "Business and Management",
        "semester": 2,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 39,
        "downloads": 580,
        "uploaderName": "Prof. Rajesh Sengupta (Finance)",
        "description": "Discounted cash flow modeling, internal rate of return, weighted average cost of capital (WACC), and Capital Asset Pricing Model (CAPM).",
        "content": [
            ("1. Capital Budgeting Evaluation Metrics",
             "Net Present Value (NPV) discounts project cash inflows at the cost of capital. A positive NPV indicates shareholder wealth maximization."),
            ("2. Weighted Average Cost of Capital (WACC)",
             "WACC blends equity and after-tax debt costs: WACC = (E/V)*Ke + (D/V)*Kd*(1 - T), where Ke is derived via CAPM.")
        ]
    },

    # -------------------------------------------------------------
    # 7. LAW
    # -------------------------------------------------------------
    {
        "fileName": "law_constitutional_fundamental_rights.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Fundamental Rights, Due Process & Constitutional Writs",
        "subject": "Constitutional Law",
        "mainCategory": "Law",
        "subcategory": "Constitutional Law",
        "topic": "Fundamental Rights & Constitutional Remedies",
        "department": "Law",
        "semester": 2,
        "category": "notes",
        "rating": 5.0,
        "ratingCount": 36,
        "downloads": 520,
        "uploaderName": "Adv. Ananya Deshmukh (Law Faculty)",
        "description": "In-depth jurisprudence on Equality before law (Art 14), Freedom of speech (Art 19), Right to Life (Art 21), and High Court writ jurisdictions.",
        "content": [
            ("1. The Golden Triangle (Articles 14, 19, 21)",
             "State actions curtailing personal liberty must satisfy procedural fairness, reasonableness, and the proportionality test."),
            ("2. Prerogative Writ Remedies",
             "Constitutional courts issue 5 writs: Habeas Corpus, Mandamus, Prohibition, Certiorari, and Quo Warranto to enforce fundamental rights.")
        ]
    },

    # -------------------------------------------------------------
    # 8. SCIENCE
    # -------------------------------------------------------------
    {
        "fileName": "sci_physics_newton_mechanics.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Classical Mechanics & Newton's Laws of Motion",
        "subject": "Physics",
        "mainCategory": "Science",
        "subcategory": "Physics",
        "topic": "Classical Mechanics & Newton's Laws",
        "department": "Science",
        "semester": 1,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 31,
        "downloads": 480,
        "uploaderName": "Dr. R. Ramanathan (Physics)",
        "description": "Foundational mechanics notes covering inertial reference frames, Newton's three laws, momentum conservation, and Lagrangian formulations.",
        "content": [
            ("1. Inertial Frames & Newton's Laws",
             "First Law defines inertial frames. Second Law F = dp/dt establishes equations of motion. Third Law asserts equal and opposite forces."),
            ("2. Conservation Principles & Energy",
             "Linear and angular momentum conservation in isolated systems, work-energy theorem, and conservative potential fields.")
        ]
    },

    # -------------------------------------------------------------
    # 9. COMMERCE
    # -------------------------------------------------------------
    {
        "fileName": "comm_accounting_financial_reporting.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Corporate Financial Reporting & IFRS Standards Guide",
        "subject": "Accounting",
        "mainCategory": "Commerce",
        "subcategory": "Accounting",
        "topic": "Corporate Financial Reporting Standards",
        "department": "Commerce",
        "semester": 2,
        "category": "notes",
        "rating": 4.8,
        "ratingCount": 28,
        "downloads": 450,
        "uploaderName": "Prof. S. Natarajan (Commerce)",
        "description": "Detailed guide on corporate balance sheet disclosures, income statements, cash flow statements, and IFRS/GAAP reconciliation.",
        "content": [
            ("1. Financial Statement Preparation",
             "Components of a complete set of financial statements under IFRS: Statement of Financial Position, Profit or Loss, and Cash Flows."),
            ("2. Revenue Recognition (IFRS 15)",
             "The five-step model: Identify contract, identify performance obligations, determine transaction price, allocate price, recognize revenue.")
        ]
    },

    # -------------------------------------------------------------
    # 10. ARTS AND HUMANITIES
    # -------------------------------------------------------------
    {
        "fileName": "arts_psychology_cognitive_memory.pdf",
        "fileType": "pdf",
        "mimeType": "application/pdf",
        "title": "Cognitive Psychology: Memory Models & Attention Frameworks",
        "subject": "Psychology",
        "mainCategory": "Arts and Humanities",
        "subcategory": "Psychology",
        "topic": "Cognitive Psychology & Memory",
        "department": "Arts and Humanities",
        "semester": 1,
        "category": "notes",
        "rating": 4.9,
        "ratingCount": 33,
        "downloads": 510,
        "uploaderName": "Dr. Meenakshi S. (Psychology)",
        "description": "Comprehensive review of Atkinson-Shiffrin multistore memory model, Baddeley's working memory model, encoding, and cognitive retrieval.",
        "content": [
            ("1. Multi-Store Memory Model",
             "Sensory memory, Short-Term Memory (STM capacity 7 +/- 2 chunks), and Long-Term Memory (LTM with episodic and semantic stores)."),
            ("2. Baddeley & Hitch Working Memory Model",
             "Central executive coordinating phonological loop, visuo-spatial sketchpad, and episodic buffer during active cognitive processing.")
        ]
    }
]

async def seed_all():
    print("=" * 60)
    print("CAMPUSVERSE STRICT TITLE-BASED CATEGORY & MATERIAL SEEDER")
    print("=" * 60)

    # 1. Connect MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017/campusverse")
    db = client["campusverse"]
    print("Connected to MongoDB successfully.")

    # 2. Reseed Academic Categories
    from app.services.category_data import INITIAL_CATEGORIES_DATA
    await db["academic_categories"].delete_many({})
    for cat in INITIAL_CATEGORIES_DATA:
        await db["academic_categories"].insert_one(dict(cat))
    print(f"Academic categories seeded: {len(INITIAL_CATEGORIES_DATA)} main faculties.")

    # 3. Clean existing materials
    await db["materials"].delete_many({})
    print("Cleared old materials.")

    # 4. Generate files and insert records
    created_count = 0
    for item in STUDY_MATERIALS_CATALOG:
        fn = item["fileName"]
        target_path = UPLOADS_DIR / fn
        ext = f".{item['fileType']}"

        # Generate physical file
        if item["fileType"] == "pdf":
            file_size = create_pdf(
                target_path,
                item["title"],
                item["description"],
                item["mainCategory"],
                item["subcategory"],
                item["topic"],
                item["content"]
            )
        elif item["fileType"] == "docx":
            file_size = create_docx(
                target_path,
                item["title"],
                item["description"],
                item["mainCategory"],
                item["subcategory"],
                item["topic"],
                item["content"]
            )
        elif item["fileType"] == "pptx":
            file_size = create_pptx(
                target_path,
                item["title"],
                item["description"],
                item["mainCategory"],
                item["subcategory"],
                item["topic"],
                item["content"]
            )

        # Compute file hash
        with open(target_path, "rb") as f:
            file_bytes = f.read()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

        storage_key = f"materials/{fn}"
        now = datetime.utcnow()

        doc = {
            "title": item["title"],
            "description": item["description"],
            "mainCategory": item["mainCategory"],
            "subcategory": item["subcategory"],
            "topic": item["topic"],
            "department": item["department"],
            "semester": item["semester"],
            "subject": item["subject"],
            "category": item["category"],
            "uploader": "campusverse-faculty",
            "uploaderName": item["uploaderName"],
            "storageKey": storage_key,
            "storageProvider": "local",
            "originalName": fn,
            "mimeType": item["mimeType"],
            "extension": ext,
            "size": len(file_bytes),
            "fileHash": file_hash,
            "status": "ADMIN_APPROVED",
            "downloads": item["downloads"],
            "rating": item["rating"],
            "ratingCount": item["ratingCount"],
            "createdAt": now,
            "updatedAt": now
        }

        res = await db["materials"].insert_one(doc)
        mat_id = str(res.inserted_id)
        file_url = f"/api/materials/{mat_id}/file"
        await db["materials"].update_one({"_id": res.inserted_id}, {"$set": {"fileUrl": file_url}})

        print(f" [{created_count+1}] Created: {item['mainCategory']} > {item['subcategory']} > {item['topic']} ({fn})")
        created_count += 1

    print("=" * 60)
    print(f"SUCCESS: Seeded {created_count} category-specific real study materials.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(seed_all())
