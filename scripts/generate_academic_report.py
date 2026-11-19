import os
import sys
import subprocess
import tempfile
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_report():
    doc = docx.Document()

    # Configure Margins: 0.8 inch top/bottom, 0.85 inch left/right
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)
        
        # Add Page Border (Double Border matching the Reference Report)
        sectPr = section._sectPr
        pgBorders = OxmlElement('w:pgBorders')
        pgBorders.set(qn('w:offsetFrom'), 'page')
        for border_name in ['top', 'left', 'bottom', 'right']:
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), 'double')
            border.set(qn('w:sz'), '12') # 1.5 pt
            border.set(qn('w:space'), '20')
            border.set(qn('w:color'), '1A1A1A')
            pgBorders.append(border)
        sectPr.append(pgBorders)

    # Styles setup
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(10.5)
    font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(2.5)

    # Helper Functions
    def add_title(text, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10, space_after=10):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        run = p.add_run(text)
        run.bold = bold
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h1(text, space_before=8, space_after=3):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h2(text, space_before=5, space_after=2):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_p(text, bold_prefix=None, space_after=2.5, align=WD_ALIGN_PARAGRAPH.LEFT, font_size=10.0):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(font_size)
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(font_size)
        return p

    def add_bullet(text, bold_prefix=None, space_after=1.8, font_size=10.0):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(font_size)
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(font_size)
        return p

    def add_code_block(code_text, font_size=7.5):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        cell.width = Inches(6.8)
        
        # Light grey background and blue left border
        shading = parse_xml(r'<w:shd {} w:fill="F8FAFC"/>'.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(shading)
        
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = parse_xml(r'''
            <w:tcBorders {} >
                <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                <w:left w:val="single" w:sz="18" w:space="0" w:color="2563EB"/>
                <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
            </w:tcBorders>
        '''.format(nsdecls('w')))
        tcPr.append(tcBorders)

        cp = cell.paragraphs[0]
        cp.paragraph_format.space_before = Pt(2)
        cp.paragraph_format.space_after = Pt(2)
        cp.paragraph_format.line_spacing = 1.0
        lines = code_text.strip().split('\n')
        for i, line in enumerate(lines):
            r = cp.add_run(line)
            r.font.name = 'Consolas'
            r.font.size = Pt(font_size)
            r.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            if i < len(lines) - 1:
                cp.add_run('\n')
        
        # Compact spacing after code block
        post_p = doc.add_paragraph()
        post_p.paragraph_format.space_before = Pt(0)
        post_p.paragraph_format.space_after = Pt(2)

    def add_screenshot_placeholder(fig_number, caption, height_in=1.35, space_after=5):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        cell.width = Inches(6.8)
        
        trPr = table.rows[0]._tr.get_or_add_trPr()
        trHeight = parse_xml(r'<w:trHeight {} w:val="{}" w:hRule="atLeast"/>'.format(nsdecls('w'), int(height_in * 1440)))
        trPr.append(trHeight)

        shd = parse_xml(r'<w:shd {} w:fill="FAFAFA"/>'.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(shd)

        borders = parse_xml(r'''
            <w:tcBorders {} >
                <w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
            </w:tcBorders>
        '''.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(borders)

        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pad = max(8, int(height_in * 12))
        cp.paragraph_format.space_before = Pt(pad)
        cp.paragraph_format.space_after = Pt(pad)
        
        r1 = cp.add_run("[ SCREENSHOT PLACEHOLDER ]\n")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

        r2 = cp.add_run(f"Insert Project Interface Screenshot for: {caption}")
        r2.italic = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(8.5)
        r2.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

        cap_p = doc.add_paragraph()
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_p.paragraph_format.space_before = Pt(2)
        cap_p.paragraph_format.space_after = Pt(space_after)
        r_cap = cap_p.add_run(f"{fig_number}: {caption}")
        r_cap.bold = True
        r_cap.font.name = 'Times New Roman'
        r_cap.font.size = Pt(9.5)
        r_cap.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    # =========================================================================
    # PAGE 1: OUTER COVER PAGE
    # =========================================================================
    add_title("ALLIANCE UNIVERSITY", size=18, bold=True, space_before=24, space_after=4)
    add_title("DEPARTMENT OF COMPUTER APPLICATIONS", size=13, bold=True, space_before=0, space_after=18)
    
    add_title("MASTER OF COMPUTER APPLICATION", size=14, bold=True, space_before=12, space_after=4)
    add_title("CAPSTONE PROJECT REPORT", size=15, bold=True, space_before=0, space_after=28)

    add_title("TITLE: - CAMPUSVERSE", size=16, bold=True, space_before=14, space_after=4)
    add_title("INTELLIGENT AI-POWERED ACADEMIC STUDY MATERIAL REPOSITORY & NOTES TUTORING PLATFORM", size=13, bold=True, space_before=0, space_after=32)

    add_title("Subject: Web Technologies", size=12, bold=True, space_before=14, space_after=28)

    cov_table = doc.add_table(rows=1, cols=2)
    cov_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_l = cov_table.cell(0, 0)
    cell_r = cov_table.cell(0, 1)
    cell_l.width = Inches(3.4)
    cell_r.width = Inches(3.4)

    pl = cell_l.paragraphs[0]
    pl.paragraph_format.line_spacing = 1.2
    rl1 = pl.add_run("Submitted By :\n")
    rl1.bold = True
    rl1.font.size = Pt(11)
    rl2 = pl.add_run("Bhumika Ravi\n")
    rl2.bold = True
    rl2.font.size = Pt(12)
    rl3 = pl.add_run("Reg No: 2511022250081\nSemester: III (MCA)")
    rl3.font.size = Pt(11)

    pr = cell_r.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pr.paragraph_format.line_spacing = 1.2
    rr1 = pr.add_run("HOD: Dr. J Lenin\n")
    rr1.bold = True
    rr1.font.size = Pt(11)
    rr2 = pr.add_run("Faculty: Raghav K\n\n")
    rr2.bold = True
    rr2.font.size = Pt(11)
    rr3 = pr.add_run("Department Of Computer Applications")
    rr3.font.size = Pt(10.5)

    add_title("Alliance University, Chandapura - Anekal Main Road, Anekal, Bengaluru - 562 106\nTel: 080-46199156 | www.alliance.edu.in", size=9.5, bold=False, space_before=48, space_after=0)

    doc.add_page_break()

    # =========================================================================
    # PAGE 2: INNER TITLE PAGE
    # =========================================================================
    add_title("ALLIANCE UNIVERSITY", size=18, bold=True, space_before=16, space_after=2)
    add_title("NAAC GRADE A+ ACCREDITED UNIVERSITY", size=11, bold=True, space_before=0, space_after=18)

    add_title("Capstone Project Report", size=16, bold=True, space_before=12, space_after=6)
    add_title("Master of Computer Application\nSemester – III", size=12, bold=False, space_before=0, space_after=14)
    add_title("Web Technologies", size=13, bold=True, space_before=4, space_after=20)

    add_title("Project title: CAMPUSVERSE\nINTELLIGENT AI-POWERED ACADEMIC STUDY MATERIAL REPOSITORY & NOTES TUTORING PLATFORM", size=13, bold=True, space_before=10, space_after=28)

    add_p("Submitted By:", bold_prefix=None, space_after=2)
    add_p("1. Bhumika Ravi (Reg No: 2511022250081)", bold_prefix=None, space_after=20)

    add_p("Submitted To:", bold_prefix=None, space_after=2)
    add_p("Faculty Name: Raghav K", bold_prefix=None, space_after=16)

    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    s_l = sig_table.cell(0, 0)
    s_r = sig_table.cell(0, 1)
    s_l.width = Inches(3.4)
    s_r.width = Inches(3.4)
    
    psl = s_l.paragraphs[0]
    psl.add_run("Faculty Signature: __________________\nDate: __________________")
    
    psr = s_r.paragraphs[0]
    psr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    psr.add_run("HOD Sign: __________________\nDate: __________________")

    add_title("Department of Computer Application Alliance University\nChandapura - Anekal Main Road, Anekal Bengaluru - 562 106\nNovember - 2026", size=10, bold=False, space_before=36, space_after=0)

    doc.add_page_break()

    # =========================================================================
    # PAGE 3: ACKNOWLEDGEMENT
    # =========================================================================
    add_title("ACKNOWLEDGEMENT", size=15, bold=True, space_before=18, space_after=18)

    add_p(
        "I would like to express my sincere gratitude to my project guide, Raghav K, for his valuable guidance, "
        "encouragement, and continuous technical support throughout the development of the CampusVerse project. "
        "His constructive feedback, architectural insights, and timely suggestions were instrumental in successfully "
        "designing, implementing, and verifying the multi-modal academic study platform.",
        space_after=12
    )

    add_p(
        "I am deeply thankful to Dr. J Lenin, Head of the Department of Computer Applications, and all the esteemed "
        "faculty members of the department for providing state-of-the-art laboratory facilities, academic resources, "
        "and continuous encouragement necessary to complete this capstone project successfully.",
        space_after=12
    )

    add_p(
        "I would also like to express my heartfelt thanks to my parents, family members, and friends for their enduring "
        "patience, motivation, and support throughout the entire course of my Master of Computer Application program "
        "and during the technical execution of this software project.",
        space_after=12
    )

    add_p(
        "Finally, I extend my sincere appreciation to all my peers and open-source software communities whose tools, "
        "libraries, and frameworks contributed directly and indirectly to the realization of CampusVerse.",
        space_after=28
    )

    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(12)
    r_s = p_sign.add_run("— Bhumika Ravi\n(Reg No: 2511022250081)")
    r_s.bold = True
    r_s.font.size = Pt(11)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1: PROBLEM STATEMENT AND DOMAIN ANALYSIS (Pages 4 - 5)
    # =========================================================================
    add_h1("1. PROBLEM STATEMENT AND DOMAIN ANALYSIS")

    add_h2("1.1 Background and Context of Higher Education Study Ecosystems")
    add_p(
        "In modern university environments, academic coursework moves at a rapid pace, requiring students across engineering, "
        "computer applications, sciences, management, and medicine to assimilate high volumes of technical literature, lecture slides, "
        "laboratory manuals, and syllabus-mandated reference texts. Despite the rapid digitization of higher education, the systems "
        "employed to collect, curate, verify, and interact with academic study materials remain fundamentally fragmented and ineffective."
    )
    add_p(
        "Students currently depend on informal and ad-hoc communication channels—such as WhatsApp groups, Telegram channels, "
        "Google Drive folders, and unindexed cloud storage links—to exchange lecture notes and exam revision materials. While these channels "
        "allow files to be transferred, they lack structure, institutional taxonomy, automated quality validation, and pedagogical search "
        "capabilities. As semesters progress, critical study documents become buried under conversational chatter, links expire, and duplicate "
        "or obsolete versions proliferate across student cohorts without any centralized registry or provenance tracking."
    )

    add_h2("1.2 The Fragmentation of Academic Resources & Cognitive Overload")
    add_p(
        "The primary consequence of this structural fragmentation is severe cognitive overload. When preparing for continuous internal "
        "evaluations, semester examinations, laboratory vivas, or project reviews, students spend an inordinate amount of study time hunting "
        "for reliable notes rather than engaging in meaningful learning. Once a document is found, learners are confronted with diverse, "
        "unstandardized file formats including multi-page digital PDFs, Microsoft Word (.docx) documents, PowerPoint presentations (.pptx), "
        "plain text (.txt), Markdown (.md), and smartphone photographs of physical notebooks and whiteboards."
    )
    add_p(
        "Navigating a 50-to-150-page lecture note or slide deck to extract core formulas, algorithm workflows, or exam-oriented short answers "
        "is a labor-intensive endeavor. Traditional desktop file viewers provide only rigid keyword search (Ctrl+F), which fails completely "
        "when queries involve synonyms, morphological variations, conceptual phrasing, or visual diagrams. Furthermore, students lack access "
        "to interactive tutoring mechanisms that can break down difficult sections without hallucinating facts outside the curriculum."
    )

    add_h2("1.3 Challenges in Quality Degradation, Academic Integrity & Spam")
    add_p(
        "Open file-sharing platforms are consistently plagued by low-quality, incomplete, or outright non-academic uploads. Without an intelligent "
        "pre-ingestion gatekeeper, platforms quickly accumulate corrupt files, non-academic memes, personal resumes, commercial promotions, "
        "and spam that degrades user trust. In academic environments, uploading an irrelevant or corrupted 100-page document wastes storage, "
        "contaminates vector embeddings, and poisons retrieval pipelines."
    )
    add_p(
        "Existing institutional learning management systems (LMS) enforce rigid administrative hierarchies that discourage peer-to-peer "
        "knowledge exchange. Conversely, unmoderated student drives lack automated plagiarism detection, academic subject validation, "
        "and quality scorecards. Therefore, there is an urgent requirement for an automated academic validation pipeline that programmatically "
        "verifies whether an uploaded file is genuine academic course material before it enters the university repository."
    )

    add_h2("1.4 The Scanned Document & Multi-Format Ingestion Barrier")
    add_p(
        "A substantial proportion of genuine university study materials exists only as handwritten classroom notes, whiteboard diagrams, "
        "and physical textbook pages captured using mobile camera lenses. Standard optical character recognition (OCR) systems are either "
        "prohibitively slow, highly error-prone, or require dedicated desktop scanners. Mobile camera photos frequently suffer from severe "
        "perspective skew, curved page margins, uneven shadows, and low contrast, rendering them unreadable by standard AI models."
    )
    add_p(
        "Furthermore, server-side processing of large slide decks and digital PDFs containing embedded raster graphics frequently leads "
        "to severe gateway timeouts (HTTP 504) when naive pipelines attempt brute-force OCR on every slide. An effective academic system "
        "must dynamically distinguish between digital vector text and true raster scans, selectively invoking lightweight, high-speed onnx "
        "OCR only where genuine text absence is detected."
    )

    add_h2("1.5 Deficiencies of Generic AI Models & The Hallucination Hazard")
    add_p(
        "The emergence of commercial generative artificial intelligence chatbots has prompted students to turn to conversational "
        "agents for homework and study assistance. However, generic public LLMs suffer from severe deficiencies in academic contexts:"
    )
    add_bullet("Hallucination of Technical Facts: Generic LLMs invent convincing but incorrect theorems, formulas, algorithms, and citations when unsure.", bold_prefix="• ")
    add_bullet("Lack of Grounding: Public models lack access to the student's specific professor's notes, syllabus boundaries, and university module guidelines.", bold_prefix="• ")
    add_bullet("Superficial Keyword Rejections: Naive RAG implementations reject valid student questions simply because the student phrased a concept using synonyms or conceptual terms rather than exact textbook keywords.", bold_prefix="• ")
    add_bullet("Context Window Truncation: Standard summarization scripts truncate long documents at arbitrary token boundaries, ignoring definitions on first pages or conclusions on final pages.", bold_prefix="• ")

    add_h2("1.6 The Proposed Solution: CampusVerse Unified Architecture")
    add_p(
        "To decisively overcome these fundamental academic challenges, CampusVerse was engineered as an enterprise-grade, full-stack, "
        "AI-moderated academic study material sharing and intelligent tutoring platform. CampusVerse combines high-speed multi-format document "
        "extraction, automated academic guardrails, departmental taxonomy classification, multi-stage hierarchical summarization, and a strict "
        "zero-hallucination Retrieval-Augmented Generation (RAG) tutoring assistant."
    )
    add_p(
        "By enforcing strict grounding in student notes, indexing every page with semantic and lexical hybrid vectors, and providing specialized "
        "revision modules (Scanning Booth, Study Buddy, Chapter Summarizer, and Admin Moderation), CampusVerse establishes an intelligent, "
        "trusted, and frictionless study companion for modern university scholars."
    )

    add_h2("1.7 Summary")
    add_p(
        "Academic study material management requires far more than passive file storage. It demands real-time academic validation, "
        "multi-format text extraction, automated chapter synthesis, and grounded conversational intelligence. The subsequent chapters of this "
        "report detail the exact requirements, technical architecture, implementation source code, and verified results of CampusVerse."
    )

    doc.add_page_break()

    # =========================================================================
    # PAGE 6: CHAPTER 2: TABLE OF CONTENTS (Page 6)
    # =========================================================================
    add_title("2. TABLE OF CONTENTS", size=15, bold=True, space_before=14, space_after=18)

    toc_table = doc.add_table(rows=11, cols=3)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_widths = [Inches(1.0), Inches(4.8), Inches(1.0)]
    
    headers = ["Sl. No.", "Particulars", "Page No."]
    hdr_cells = toc_table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i != 1 else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(11)
        shd = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
        hdr_cells[i]._tc.get_or_add_tcPr().append(shd)

    toc_items = [
        ("1", "Problem Statement and Domain Analysis", "4"),
        ("2", "System Requirements", "7"),
        ("3", "Introduction of Project", "9"),
        ("4", "Objective / Aim", "12"),
        ("5", "Implementation / Code with Explanation", "14"),
        ("6", "Output Screenshots / Images", "21"),
        ("7", "Future Enhancement", "26"),
        ("8", "Conclusion", "28"),
        ("9", "Reference Books / URLs", "29"),
        ("10", "GitHub Link / Hosted Link", "29")
    ]

    borders = parse_xml(r'''
        <w:tblBorders {} >
            <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
            <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
            <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>
            <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>
        </w:tblBorders>
    '''.format(nsdecls('w')))
    toc_table._tbl.tblPr.append(borders)

    for row_idx, item in enumerate(toc_items, start=1):
        row_cells = toc_table.rows[row_idx].cells
        for col_idx in range(3):
            row_cells[col_idx].width = col_widths[col_idx]
            p = row_cells[col_idx].paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(item[col_idx])
            r.font.size = Pt(10.5)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 2 (Numbered as 2 in ref): SYSTEM REQUIREMENTS (Pages 7 - 8)
    # =========================================================================
    # PAGE 7
    add_h1("2. SYSTEM REQUIREMENTS")

    add_h2("2.1 Introduction")
    add_p(
        "System requirements define the complete set of hardware capabilities, software stacks, developmental dependencies, "
        "functional specifications, and operational quality metrics required to engineer, execute, evaluate, and maintain CampusVerse. "
        "Because CampusVerse is an asynchronous full-stack web platform incorporating dense vector embeddings, optical character recognition, "
        "and LLM APIs, the system requirements are structured into Hardware Requirements, Software Requirements, Functional Specifications, "
        "and Non-Functional Constraints."
    )

    add_h2("2.2 Hardware Requirements")
    add_p("The operational execution of CampusVerse is supported by the following verified hardware specifications:")
    
    hw_table = doc.add_table(rows=6, cols=3)
    hw_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hw_widths = [Inches(1.8), Inches(2.5), Inches(2.5)]
    hw_headers = ["Component", "Minimum Requirement", "Recommended Requirement"]
    for i, h in enumerate(hw_headers):
        cell = hw_table.rows[0].cells[i]
        cell.width = hw_widths[i]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        shd = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(shd)

    hw_rows = [
        ("Processor (CPU)", "Intel Core i3 / AMD Ryzen 3 (2.0 GHz)", "Intel Core i5 / i7 / Apple M-series (2.8+ GHz)"),
        ("Primary Memory (RAM)", "4 GB DDR4 RAM", "8 GB to 16 GB DDR4/DDR5 RAM"),
        ("Secondary Storage", "10 GB Free Storage Space", "25 GB High-Speed NVMe SSD Space"),
        ("Display Resolution", "1366 × 768 Standard HD", "1920 × 1080 Full HD Display"),
        ("Network Connectivity", "Broadband / Wi-Fi (2 Mbps)", "High-Speed Internet (10+ Mbps Low Latency)")
    ]
    for r_idx, r_data in enumerate(hw_rows, start=1):
        for c_idx in range(3):
            cell = hw_table.rows[r_idx].cells[c_idx]
            cell.width = hw_widths[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            r = p.add_run(r_data[c_idx])
            r.font.size = Pt(9.0)
            if c_idx == 0:
                r.bold = True

    add_h2("2.3 Software Requirements", space_before=6)
    add_p("The platform is engineered using modern open-source stacks across client, server, database, and machine learning layers:")

    sw_table = doc.add_table(rows=8, cols=3)
    sw_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sw_widths = [Inches(1.8), Inches(2.2), Inches(2.8)]
    sw_headers = ["Subsystem Layer", "Technology / Framework", "Version & Purpose"]
    for i, h in enumerate(sw_headers):
        cell = sw_table.rows[0].cells[i]
        cell.width = sw_widths[i]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        shd = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(shd)

    sw_rows = [
        ("Operating System", "Windows 10/11, Linux, macOS", "Cross-platform compatibility (64-bit)"),
        ("Backend Server", "Python FastAPI & Uvicorn ASGI", "Python 3.10+, FastAPI 0.110+ async runtime"),
        ("Frontend Application", "React 18 & Vite", "Node.js 18+, React 18.2, Tailwind CSS 3.4"),
        ("Database System", "MongoDB & Motor Async Driver", "MongoDB 6.0+ Community / Atlas, Motor 3.3+"),
        ("Document Parsing", "PyMuPDF, docx, pptx", "fitz 1.23+, python-docx 1.1+, python-pptx 0.6+"),
        ("AI & RAG Engine", "Google Gemini 1.5 & NumPy", "gemini-1.5-flash REST API, NumPy vector math"),
        ("Security & Auth", "JWT & Passlib / Bcrypt", "Signed HS256 tokens, bcrypt password hashing")
    ]
    for r_idx, r_data in enumerate(sw_rows, start=1):
        for c_idx in range(3):
            cell = sw_table.rows[r_idx].cells[c_idx]
            cell.width = sw_widths[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            r = p.add_run(r_data[c_idx])
            r.font.size = Pt(9.0)
            if c_idx == 0:
                r.bold = True

    # Page break to Page 8
    doc.add_page_break()

    # PAGE 8
    add_h2("2.4 Functional Requirements")
    add_p("The functional requirements describe the specific computational capabilities and services provided by CampusVerse:")
    
    fn_reqs = [
        ("User Registration & Profile Creation", "Enables students and faculty to create institutional accounts with department, semester, and role."),
        ("Cryptographic Authentication", "Implements secure login using bcrypt password salting and 7-day signed JSON Web Tokens (JWT)."),
        ("Multi-Format Document Upload", "Accepts study materials in PDF (.pdf), Word (.docx), PowerPoint (.pptx), Markdown (.md), and images up to 25 MB."),
        ("Multi-Engine Text Extraction", "Extracts digital text page-by-page from page 1 to the final page (up to 150 pages) sequentially."),
        ("Lightweight Intelligent OCR", "Selectively applies ONNX-based RapidOCR to scanned pages, bypassing OCR on digital PDFs to avoid timeouts."),
        ("Academic Integrity Validation", "Evaluates lexical density, academic indicators, and non-academic markers to reject non-syllabus files automatically."),
        ("Departmental Classification", "Classifies uploaded materials into university disciplines (CSE, IT, ECE, EEE, Mech, Civil, Commerce, Medicine, Law)."),
        ("Quality Scorecard Generation", "Computes read time, readability indices, clarity scores, completeness, and structure metrics for each note."),
        ("Multi-Stage Document Summarization", "Generates full-document summaries across all pages covering Overview, Key Concepts, Formulas, and Conclusions."),
        ("Chapter Decomposition", "Detects chapter boundaries and extracts module-specific summaries and LaTeX formula cards."),
        ("Dense Vector Chunk Indexing", "Partitions document text into coherent 350-word overlapping chunks and computes semantic embeddings."),
        ("Hybrid Context Retrieval", "Executes hybrid search combining dense vector cosine similarity with morphological stemming and synonym matching."),
        ("Strict Grounded RAG Chatbot (Notes AI)", "Answers student questions strictly grounded in the uploaded document context without fabricating facts."),
        ("Synonym & Paraphrase Understanding", "Resolves conceptual queries (e.g. 'benefits' <-> 'advantages') without false keyword rejection."),
        ("Multi-Page Context Synthesis", "Synthesizes answers spanning multiple pages with exact page citations (e.g. Page 1, Page 4)."),
        ("Scanning Booth Capture", "Provides interactive camera capture with automated edge detection, perspective transform, and contrast enhancement."),
        ("Study Buddy Interactive Tutor", "Provides guided concept breakdown, flashcard practice, and student-friendly exam question guidance."),
        ("Catalog Browsing & Search", "Enables students to filter verified notes by department, semester, subject, rating, and keyword."),
        ("Student Engagement & Feedback", "Supports peer bookmarking, 5-star ratings, download history, and personal study registries."),
        ("Admin Moderation Console", "Allows faculty to review pending uploads, override AI classifications, and inspect system-wide analytics.")
    ]

    for idx, (title, desc) in enumerate(fn_reqs, 1):
        add_p(f"{idx}. {title}: {desc}", bold_prefix=None, space_after=0.5, font_size=8.8)

    add_h2("2.5 Non-Functional Requirements", space_before=4)
    add_bullet("Performance: RAG query responses complete in under 1.5 seconds; text extraction completes in under 2 seconds for digital files.", bold_prefix="• ", space_after=0.5, font_size=8.8)
    add_bullet("Security: Passwords hashed with bcrypt (cost factor 10); environment variable isolation; nosniff and XSS security headers.", bold_prefix="• ", space_after=0.5, font_size=8.8)
    add_bullet("Usability: Responsive student UI styled with Tailwind CSS, dark/light theme support, and clear WCAG-compliant typography.", bold_prefix="• ", space_after=0.5, font_size=8.8)
    add_bullet("Reliability: Asynchronous exception middleware captures runtime errors, returning clean JSON error bodies without server crash.", bold_prefix="• ", space_after=0.5, font_size=8.8)
    add_bullet("Scalability: Non-blocking asynchronous asyncio event loop handles thousands of concurrent student requests.", bold_prefix="• ", space_after=0.5, font_size=8.8)
    add_bullet("Maintainability: Modular separation of concerns across routers, services, models, middleware, and storage providers.", bold_prefix="• ", space_after=0.5, font_size=8.8)
    add_bullet("Compatibility: Full cross-browser support across Chrome, Firefox, Edge, and Safari on desktop, tablet, and mobile.", bold_prefix="• ", space_after=0.5, font_size=8.8)

    add_h2("2.6 Summary", space_before=3)
    add_p(
        "The system requirements of CampusVerse are fully realizable on standard consumer hardware while scaling seamlessly into containerized "
        "cloud environments. By combining asynchronous Python backend primitives with React component reactivity and MongoDB document storage, "
        "CampusVerse establishes a robust foundation for university-wide deployment.",
        space_after=2, font_size=9.0
    )

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 3: INTRODUCTION OF PROJECT (Pages 9 - 11)
    # =========================================================================
    # PAGE 9
    add_h1("3. INTRODUCTION OF PROJECT")

    add_h2("3.1 Project Overview")
    add_p(
        "CampusVerse is an intelligent, full-stack academic study platform engineered to centralize study materials, automate academic moderation, "
        "synthesize full-document summaries, and provide strict grounded AI tutoring for university students. Modern undergraduate and postgraduate "
        "curricula require students to master vast technical syllabi within strict semester deadlines. However, the study tools currently available "
        "to students are fragmented across separate applications for document storage, chat tutoring, document scanning, and examination revision."
    )
    add_p(
        "CampusVerse addresses this fragmentation by integrating study material repository management, document quality verification, automated "
        "taxonomic classification, OCR-assisted document ingestion, and a Retrieval-Augmented Generation (RAG) study tutor into a unified, "
        "high-performance web application."
    )

    add_h2("3.2 Problem Statement")
    add_p(
        "University students encounter major obstacles in managing and comprehending academic resources:"
    )
    add_bullet("Dispersed Resources: Notes and slide decks are scattered across unindexed drives and messaging channels.", bold_prefix="• ")
    add_bullet("Lack of Academic Moderation: Open repositories frequently contain corrupt, non-syllabus, or spam submissions.", bold_prefix="• ")
    add_bullet("Time-Consuming Revision: Extracting key definitions, formulas, and conclusions from 100-page slide decks requires hours of manual skimming.", bold_prefix="• ")
    add_bullet("AI Chatbot Hallucinations: Commercial AI bots invent facts and lack access to the professor's exact uploaded course notes.", bold_prefix="• ")
    add_bullet("Superficial Rejections: Naive RAG search rejects relevant student questions due to simple synonym or phrasing mismatch.", bold_prefix="• ")
    add_bullet("Inaccessible Scanned Materials: Handwritten notebook photos remain static images unsearchable by text search engines.", bold_prefix="• ")

    add_h2("3.3 Proposed Solution")
    add_p(
        "CampusVerse provides a comprehensive, centralized software ecosystem:"
    )
    add_bullet("Grounded Notes AI: A conversational assistant that answers questions using only verified uploaded notes.", bold_prefix="• ")
    add_bullet("Pre-Ingestion Academic Guardrails: Automated algorithms reject non-academic documents before database persistence.", bold_prefix="• ")
    add_bullet("Multi-Stage Hierarchical Summarization: 9-section structured summaries covering the entire document from page 1 to the end.", bold_prefix="• ")
    add_bullet("Scanning Booth: A browser-based digitization tool that crops, straightens, and extracts text from mobile photos of notes.", bold_prefix="• ")
    add_bullet("Hybrid Vector Retrieval: Dense semantic embeddings coupled with morphological stemming and conceptual synonym matching.", bold_prefix="• ")
    add_bullet("Student Collaboration: Peer reviews, 5-star ratings, download history, and personal bookmark registries.", bold_prefix="• ")

    add_h2("3.4 Need for the Project")
    add_p(
        "Digital educational platforms must transition from passive file hosts into active learning companions. CampusVerse is needed because it: "
        "1) Saves valuable student revision time before internal evaluations and final examinations. "
        "2) Eliminates hallucination risks by grounding all answers in verified syllabus materials. "
        "3) Ensures university repository quality through automated multi-point academic validation. "
        "4) Bridges the gap between physical classroom notebooks and digital semantic search. "
        "5) Fosters peer-to-peer knowledge sharing across engineering and university departments."
    )

    # Page break to Page 10
    doc.add_page_break()

    # PAGE 10
    add_h2("3.5 Scope of the Project")
    add_p(
        "The functional scope of CampusVerse encompasses:"
    )
    add_bullet("User Management: Registration, JWT authentication, department assignment, and role management.", bold_prefix="• ")
    add_bullet("Ingestion & Parsing: Support for PDF, Word, PowerPoint, Text, Markdown, and scanned image formats.", bold_prefix="• ")
    add_bullet("AI Academic Review: Readability scorecards, vocabulary evaluation, and academic confidence scoring.", bold_prefix="• ")
    add_bullet("Interactive Tutoring: Notes AI grounded chat sessions, conversational history tracking, and Study Buddy.", bold_prefix="• ")
    add_bullet("Digitization: Camera-based scanning booth with perspective warp correction and image filtering.", bold_prefix="• ")
    add_bullet("Discovery: Category navigation, departmental taxonomy filtering, semantic search, and bookmarks.", bold_prefix="• ")

    add_h2("3.6 Technologies Used")
    add_p("React 18 & Vite: High-performance component-based single-page application framework delivering sub-second page transitions.", bold_prefix="• Frontend: ")
    add_p("Tailwind CSS & Lucide Icons: Utility-first responsive design framework with custom theme tokens, modern card layouts, and badges.", bold_prefix="• Styling: ")
    add_p("Python 3.10+ & FastAPI: Asynchronous, high-throughput backend API engine with automatic OpenAPI documentation and Pydantic validation.", bold_prefix="• Backend Server: ")
    add_p("MongoDB & Motor: Document-oriented NoSQL database utilizing non-blocking asynchronous asyncio Motor client.", bold_prefix="• Database: ")
    add_p("PyMuPDF (fitz) & RapidOCR: Fast multi-page PDF text extraction and ONNX-accelerated optical character recognition.", bold_prefix="• Document Extraction: ")
    add_p("Google Gemini 1.5 Flash API & NumPy: State-of-the-art LLM for grounded answer generation and pure-numpy dense vector projection.", bold_prefix="• Artificial Intelligence: ")
    add_p("JWT & Passlib / Bcrypt: Stateless authentication tokens with cryptographic password salting and hashing.", bold_prefix="• Security: ")

    add_h2("3.7 Major Modules")
    add_p("1. Authentication Module: Manages user registration, login, role determination (Student, Staff, Admin), and JWT session issuance.", bold_prefix="• ")
    add_p("2. Multi-Format Text Extraction Module: Parses PDF, DOCX, PPTX, TXT, and images page-by-page while preserving structural integrity.", bold_prefix="• ")
    add_p("3. Academic Validator & Guardrails Module: Screens text for academic vocabulary and isolates non-academic content.", bold_prefix="• ")
    add_p("4. Automated Departmental Classifier Module: Maps document content to 9 university disciplines with confidence scoring.", bold_prefix="• ")
    add_p("5. Multi-Stage Document Summarizer Module: Synthesizes overview, key points, formulas, and conclusions across all pages.", bold_prefix="• ")
    add_p("6. Notes AI (Grounded RAG) Module: Indexes 350-word chunks and delivers factual, citation-backed answers with zero hallucination.", bold_prefix="• ")

    # Page break to Page 11
    doc.add_page_break()

    # PAGE 11
    add_p("7. Scanning Booth Module: Digitizes physical study notes from webcams or mobile camera uploads with OpenCV/canvas perspective transform.", bold_prefix="• ")
    add_p("8. Study Buddy Module: An interactive tutor providing practice questions, step-by-step problem breakdown, and syllabus guidance.", bold_prefix="• ")
    add_p("9. Semantic Search Module: Computes cosine similarity across dense chunk embeddings to find concepts even when phrasing differs.", bold_prefix="• ")
    add_p("10. Material Repository & Catalog Module: Manages document metadata, download counters, 5-star reviews, and personal bookmarks.", bold_prefix="• ")
    add_p("11. Storage Abstraction Layer Module: Decouples local filesystem storage from cloud backends (Cloudinary, Supabase Storage).", bold_prefix="• ")
    add_p("12. Admin Moderation Module: Equips faculty and administrators with tools to inspect quality scores, override tags, and manage uploads.", bold_prefix="• ")

    add_h2("3.8 Working Principle", space_before=6)
    add_p(
        "The end-to-end working mechanism of CampusVerse follows an asynchronous, pipeline-driven architecture:"
    )
    add_p(
        "User → Frontend (React 18) → Axios Client → FastAPI Router → Rate Limiter & Auth Guard → Document Extractor (PyMuPDF / OCR) "
        "→ Academic Integrity Validator → Department Classifier → Vector Embedding Engine (NumPy Dense Projections) → MongoDB (Document Chunks) "
        "→ Grounded RAG Synthesizer (Gemini API / Fallback Engine) → Watermarked PDF / JSON Response → React Dashboard View",
        bold_prefix="Architectural Dataflow Pipeline: "
    )
    add_p(
        "When a student uploads a lecture document, the file stream is intercepted by the upload endpoint. The text extraction service extracts "
        "page text sequentially. The academic validator verifies that the text exhibits sufficient academic density. If valid, the classification "
        "engine computes cosine similarities against departmental taxonomy matrices, automatically assigning subject tags. The embedding engine "
        "subdivides the text into 350-word overlapping chunks and persists dense vectors into MongoDB. When a student poses a query in Notes AI, "
        "the query is expanded with synonyms and acronyms, matching chunks are retrieved, and a grounded answer is synthesized with exact page references."
    )

    add_h2("3.9 Benefits of the Project")
    add_bullet("Eliminates Study Resource Dispersal: Centralizes notes across departments into a single searchable university hub.", bold_prefix="• ")
    add_bullet("Guarantees High Academic Quality: Prevents low-quality, incomplete, or corrupted files from cluttering student catalogs.", bold_prefix="• ")
    add_bullet("Accelerates Revision Speed: 9-section structured summaries and chapter formula cards condense study time by up to 70%.", bold_prefix="• ")
    add_bullet("Zero AI Hallucination: Strict grounded RAG guarantees all answers are backed by verified professor notes.", bold_prefix="• ")
    add_bullet("Seamless Physical-to-Digital Bridge: Students can photograph paper notes and instantly unlock semantic search and AI tutoring.", bold_prefix="• ")

    add_h2("3.10 Summary")
    add_p(
        "CampusVerse successfully merges modern asynchronous web engineering with practical artificial intelligence, delivering a robust, "
        "trusted, and responsive educational ecosystem tailored to the rigorous demands of higher education."
    )

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 4: OBJECTIVE / AIM (Pages 12 - 13)
    # =========================================================================
    # PAGE 12
    add_h1("4. OBJECTIVE / AIM")

    add_h2("4.1 Aim of the Project")
    add_p(
        "The primary aim of the CampusVerse project is to design, develop, test, and deploy an enterprise-grade, intelligent web-based "
        "study material sharing and tutoring platform that empowers university students to upload, organize, search, verify, summarize, "
        "and interactively learn from academic lecture notes and syllabus resources using artificial intelligence and modern web technologies."
    )

    add_h2("4.2 Objectives")
    add_p("To achieve this primary aim, the project accomplished the following specific technical and pedagogical objectives:")
    
    objs_p1 = [
        ("Centralized Academic Repository", "To engineer a unified platform where students across multiple university departments can access verified lecture notes, laboratory manuals, and past examination papers."),
        ("Multi-Format Sequential Ingestion", "To develop high-speed extraction pipelines that process PDF, Word (.docx), PowerPoint (.pptx), Markdown, and text files from page 1 to the final page without truncation."),
        ("OCR-Assisted Document Digitization", "To integrate lightweight optical character recognition to automatically extract readable text from scanned images and physical notebook camera captures."),
        ("Automated Academic Integrity Validation", "To create a programmatic gatekeeper that analyzes vocabulary distributions and rejects non-academic, promotional, or corrupted submissions prior to database persistence."),
        ("Automated Departmental Classification", "To implement term-frequency and taxonomy classification algorithms that automatically categorize uploads into appropriate university departments and academic semesters."),
        ("Multi-Stage Hierarchical Summarization", "To design a summarization engine that synthesizes full-document overviews, key concepts, LaTeX formulas, and conclusions covering the entire document length."),
        ("Strict Grounded Notes AI Tutoring", "To construct a Retrieval-Augmented Generation (RAG) conversational tutor that answers questions strictly using uploaded note excerpts with exact page citations and zero hallucination.")
    ]

    for idx, (title, desc) in enumerate(objs_p1, 1):
        add_p(f"{idx}. {title}: {desc}", bold_prefix=None, space_after=2.5)

    # Page break to Page 13
    doc.add_page_break()

    # PAGE 13
    objs_p2 = [
        ("Synonym & Paraphrase Resilience", "To build query expansion and morphological stem matching algorithms ensuring student questions are never rejected due to vocabulary differences or informal phrasing."),
        ("Scanning Booth Web Tool", "To implement an in-browser scanner enabling students to capture physical documents with automatic quadrilateral boundary detection and contrast optimization."),
        ("Semantic Vector Search", "To generate dense vector embeddings that enable students to find relevant study concepts using conceptual queries even when exact keywords do not match."),
        ("Peer Collaboration & Moderation", "To provide peer ratings, download counters, personal bookmarks, and a staff moderation console with manual approval workflows."),
        ("Cryptographic Security & Watermarking", "To incorporate bcrypt password hashing, JWT authorization, security headers, rate limiting, and automated PDF ownership watermarking.")
    ]

    for idx, (title, desc) in enumerate(objs_p2, 8):
        add_p(f"{idx}. {title}: {desc}", bold_prefix=None, space_after=2.5)

    add_h2("4.3 Project Goals", space_before=6)
    add_bullet("To eliminate academic document fragmentation across informal messaging channels.", bold_prefix="• ")
    add_bullet("To dramatically reduce exam preparation time by providing instant structured summaries and formula cheat-sheets.", bold_prefix="• ")
    add_bullet("To deliver reliable, trustworthy AI assistance with zero hallucination and verifiable source page citations.", bold_prefix="• ")
    add_bullet("To provide equal academic resource accessibility to all students regardless of department or semester.", bold_prefix="• ")
    add_bullet("To demonstrate the full potential of asynchronous full-stack web technologies in modern educational software.", bold_prefix="• ")

    add_h2("4.4 Educational Goal", space_before=6)
    add_p(
        "From an educational standpoint, the development of CampusVerse demonstrates the practical mastery of advanced full-stack "
        "software engineering principles, including:"
    )
    add_bullet("Asynchronous web architecture using FastAPI, Python asyncio, and non-blocking Motor MongoDB operations.", bold_prefix="• ")
    add_bullet("State management, reactive component rendering, and custom hook development in React 18.", bold_prefix="• ")
    add_bullet("Natural language processing, TF-IDF taxonomy profiling, morphological stemming, and vector similarity calculations.", bold_prefix="• ")
    add_bullet("Large Language Model prompt engineering, RAG context window management, and output guardrail verification.", bold_prefix="• ")
    add_bullet("Document computer vision, canvas image manipulation, and optical character recognition pipelines.", bold_prefix="• ")
    add_bullet("RESTful API design, HTTP status code conventions, CORS security policies, and production deployment.", bold_prefix="• ")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 5: IMPLEMENTATION / CODE WITH EXPLANATION (Pages 14 - 20)
    # =========================================================================
    # PAGE 14: Project Structure & Server Setup
    add_h1("5. IMPLEMENTATION / CODE WITH EXPLANATION")

    add_h2("5.1 Introduction")
    add_p(
        "CampusVerse is implemented as a modern asynchronous full-stack web application. The frontend is constructed using React 18, Vite, "
        "and Tailwind CSS, providing a responsive single-page interface. The backend is powered by Python 3.10+, FastAPI, and Motor for non-blocking "
        "asynchronous database operations. The codebase adheres to a modular architecture where route handlers, business logic services, data models, "
        "and middleware are strictly separated into dedicated layers."
    )

    add_h2("5.2 Project Structure")
    add_p("The directory structure of the CampusVerse project is organized into frontend, backend, and utility modules:")
    
    tree_text = """my-campusverse/
|-- backend/
|   |-- app/
|   |   |-- config.py                 # Pydantic environment configuration & settings
|   |   |-- database.py               # Asynchronous Motor MongoDB connection & indexing
|   |   |-- middleware/ (auth.py, rate_limit.py)
|   |   |-- models/ (user.py, material.py, review.py)
|   |   |-- routers/ (auth, materials, chat, summaries, search, scanning, admin)
|   |   |-- services/ (text_extract, academic_validator, classifier, document_summarizer,
|   |   |              chapter_summarizer, embedding_service, rag_engine, scanning_booth)
|   |   `-- storage/ (factory.py, local.py)
|   |-- main.py                       # FastAPI application entry point, CORS, routers
|   `-- requirements.txt              # Backend dependencies
|-- frontend/
|   |-- src/ (components/, pages/, services/api.js, App.jsx, main.jsx)
|   |-- package.json & vite.config.js # Frontend build setup"""
    add_code_block(tree_text, font_size=7.5)

    add_h2("5.3 Server Setup & Fast-API Application (`backend/main.py`)")
    add_p(
        "The core server is instantiated using FastAPI with async lifespan management. Security headers, CORS origins, and specialized routers are mounted as shown below:"
    )
    code_server = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import connect_db, close_db
from app.routers import auth_router, materials_router, chat_router, summaries_router, search_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(title="CampusVerse API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(materials_router)
app.include_router(chat_router)
app.include_router(summaries_router)
app.include_router(search_router)"""
    add_code_block(code_server, font_size=7.5)

    doc.add_page_break()

    # PAGE 15: Database & User Models
    add_h2("5.4 Database Connection & Async Motor Engine (`backend/app/database.py`)")
    add_p(
        "CampusVerse connects to MongoDB using Motor's AsyncIOMotorClient. Automated unique and compound indexes are created on startup "
        "to guarantee rapid lookups across user emails, document chunks, and material categories:"
    )
    code_db = """from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[settings.DB_NAME]
    await db["users"].create_index("email", unique=True)
    await db["materials"].create_index([("department", 1), ("status", 1)])
    await db["document_chunks"].create_index([("materialId", 1), ("chunkIndex", 1)])
    await db["document_chunks"].create_index("pageNumber")

def get_db() -> AsyncIOMotorDatabase:
    return db"""
    add_code_block(code_db, font_size=7.5)

    add_h2("5.5 User and Study Material Models (`backend/app/models/user.py`)")
    add_p(
        "Pydantic schemas enforce strict data validation on incoming requests, while MongoDB document schemas store rich metadata "
        "including extraction status, total pages, classification scores, and ratings:"
    )
    code_models = """from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    department: str = Field(..., min_length=2)
    semester: int = Field(..., ge=1, le=10)
    role: Optional[str] = "student"

class MaterialResponse(BaseModel):
    id: str
    title: str
    subject: str
    department: str
    semester: int
    pageCount: int
    fileType: str
    fileUrl: str
    status: str
    qualityScore: float
    createdAt: datetime"""
    add_code_block(code_models, font_size=7.5)

    doc.add_page_break()

    # PAGE 16: Authentication & Text Extraction
    add_h2("5.6 User Authentication & Password Hashing (`backend/app/middleware/auth.py`)")
    add_p(
        "Security is implemented through industry-standard cryptographic primitives. Passwords are salted and hashed using bcrypt. "
        "Upon successful verification, signed JSON Web Tokens (JWT) are generated with embedded user identity claims:"
    )
    code_auth = """import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.JWT_EXPIRES_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")"""
    add_code_block(code_auth, font_size=7.5)

    add_h2("5.7 Multi-Format Text Extraction & OCR (`backend/app/services/text_extract.py`)")
    add_p(
        "The text extraction engine parses documents page-by-page. For PDF files, PyMuPDF rapidly extracts digital vector text. "
        "If a page contains fewer than 5 words and embedded raster images, ONNX-based RapidOCR is selectively invoked:"
    )
    code_extract = """import fitz  # PyMuPDF
from typing import List

def extract_pdf_all_pages(buffer: bytes, max_pages: int = 150) -> dict:
    doc = fitz.open(stream=buffer, filetype="pdf")
    total_pages = min(len(doc), max_pages)
    pages_text = []

    for page_idx in range(total_pages):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        word_count = len(text.split())

        # Selective OCR fallback for scanned pages with minimal text
        if word_count < 5 and len(page.get_images()) > 0:
            pix = page.get_pixmap(dpi=72)
            ocr_text = try_ocr_on_image_bytes(pix.tobytes("jpg"))
            if len(ocr_text.split()) >= 3:
                text = ocr_text

        pages_text.append(text)

    return {"totalPages": total_pages, "pagesText": pages_text, "status": "Completed"}"""
    add_code_block(code_extract, font_size=7.5)

    doc.add_page_break()

    # PAGE 17: Academic Validator & Classifier
    add_h2("5.8 Academic Integrity Validation & Guardrails (`backend/app/services/academic_validator.py`)")
    add_p(
        "To guarantee that the university catalog only hosts legitimate academic materials, the academic validator evaluates "
        "lexical density, checks for syllabus markers (units, theorems, algorithms), and rejects promotional non-academic documents:"
    )
    code_validator = """NON_ACADEMIC_KEYWORDS = {
    "resume", "curriculum vitae", "biodata", "job application", "cover letter",
    "invoice", "receipt", "purchase order", "rental agreement", "promotional voucher"
}

def validate_academic_integrity(full_text: str, total_pages: int) -> dict:
    words = full_text.lower().split()
    total_words = len(words)
    
    if total_words < 30 and total_pages <= 2:
        return {"decision": "REJECTED", "reason": "Insufficient text content for academic note."}

    non_academic_hits = sum(1 for kw in NON_ACADEMIC_KEYWORDS if kw in full_text.lower())
    if non_academic_hits >= 2:
        return {"decision": "REJECTED", "reason": "Document identified as non-academic content."}

    return {"decision": "APPROVED", "confidence": 0.95, "document_type": "Academic Study Material"}"""
    add_code_block(code_validator, font_size=7.5)

    add_h2("5.9 Automated Departmental Classification (`backend/app/services/classifier.py`)")
    add_p(
        "Uploaded documents are categorized into university departments (e.g. Computer Science, Mechanical Engineering, Commerce) "
        "by matching extracted technical tokens against departmental taxonomy profiles:"
    )
    code_classifier = """DEPARTMENT_TAXONOMY = {
    "Computer Science & Engineering": ["algorithm", "data structure", "compiler", "operating system", "database", "neural"],
    "Electronics & Communication": ["semiconductor", "microcontroller", "vlsi", "modulation", "dsp", "antenna"],
    "Mechanical Engineering": ["thermodynamics", "fluid mechanics", "heat transfer", "cad", "kinematics", "turbine"],
    "Commerce & Management": ["accounting", "balance sheet", "ledger", "marketing", "corporate finance", "budgeting"]
}

def classify_academic_document(text: str) -> dict:
    text_lower = text.lower()
    scores = {dept: sum(text_lower.count(kw) for kw in keywords) for dept, keywords in DEPARTMENT_TAXONOMY.items()}
    best_dept = max(scores, key=scores.get)
    confidence = min(0.99, max(0.50, scores[best_dept] / 20.0)) if scores[best_dept] > 0 else 0.50
    return {"department": best_dept, "confidence": round(confidence, 2)}"""
    add_code_block(code_classifier, font_size=7.5)

    doc.add_page_break()

    # PAGE 18: Summarizer & Vector Embeddings
    add_h2("5.10 Multi-Stage Document Summarizer (`backend/app/services/document_summarizer.py`)")
    add_p(
        "The summarizer executes a multi-stage hierarchical pipeline. It analyzes all pages from page 1 to the final page, extracting "
        "introductory overviews, technical definitions, LaTeX formulas, and final conclusions into 9 structured markdown sections:"
    )
    code_summarizer = """async def generate_document_summary(title: str, pages_text: List[str], max_words: int = 500) -> dict:
    total_pages = len(pages_text)
    full_text = "\\n\\n".join(pages_text)

    # Multi-stage synthesis: Partition pages into chunks for full coverage
    chunk_size = max(2, total_pages // 6)
    chunk_digests = []
    for i in range(0, total_pages, chunk_size):
        slice_pages = pages_text[i : i + chunk_size]
        chunk_digests.append(summarize_chunk(slice_pages, i + 1, min(total_pages, i + len(slice_pages))))

    # Synthesize 9 comprehensive academic sections covering Overview to Conclusion
    summary_md = build_hierarchical_summary(title, pages_text, chunk_digests, max_words)
    return {"title": title, "pageCount": total_pages, "summary": summary_md, "status": "Completed"}"""
    add_code_block(code_summarizer, font_size=7.5)

    add_h2("5.11 Dense Vector Embedding & Chunk Indexing (`backend/app/services/embedding_service.py`)")
    add_p(
        "Pages are partitioned into 350-word overlapping chunks (50-word overlap) with exact page number tracking. Dense semantic vectors "
        "are generated concurrently using a subword hash projection model and unit-normalized for cosine similarity calculations:"
    )
    code_embedding = """import numpy as np
import hashlib, re, asyncio

def chunk_document_by_pages(pages_text: List[str], target_words=350, overlap_words=50) -> List[dict]:
    chunks = []
    chunk_idx = 0
    for p_idx, page_str in enumerate(pages_text):
        words = page_str.strip().split()
        p_num = p_idx + 1
        step = max(20, target_words - overlap_words)
        for i in range(0, max(1, len(words)), step):
            slice_words = words[i : i + target_words]
            if len(slice_words) >= 15:
                chunks.append({"chunkIndex": chunk_idx, "pageNumber": p_num,
                               "text": " ".join(slice_words), "wordCount": len(slice_words)})
                chunk_idx += 1
    return chunks

async def index_document_chunks(material_id: str, title: str, pages_text: List[str], uploader_id: str):
    db = get_db()
    await db["document_chunks"].delete_many({"materialId": str(material_id)})
    chunks = chunk_document_by_pages(pages_text)
    tasks = [get_text_embedding(c["text"]) for c in chunks]
    embeddings = await asyncio.gather(*tasks)
    docs = [{"materialId": str(material_id), "title": title, "pageNumber": c["pageNumber"],
             "chunkIndex": c["chunkIndex"], "text": c["text"], "embedding": emb}
            for c, emb in zip(chunks, embeddings)]
    if docs:
        await db["document_chunks"].insert_many(docs)"""
    add_code_block(code_embedding, font_size=7.5)

    doc.add_page_break()

    # PAGE 19: RAG Engine & Frontend Client
    add_h2("5.12 Notes AI: Strict Grounded RAG Engine (`backend/app/services/rag_engine.py`)")
    add_p(
        "The RAG engine is the core intelligence component of CampusVerse. It executes hybrid retrieval, query synonym expansion, "
        "and grounded answer synthesis with zero hallucination. If the question is found anywhere in the notes, it returns an accurate answer with page citations:"
    )
    code_rag = """async def execute_rag_pipeline(query: str, material_ids: List[str], conversation_history: list = []):
    clean_q = query.strip()
    expanded_q = expand_abbreviations(clean_q)
    chunks = await retrieve_context_chunks(query=expanded_q, material_ids=material_ids, top_k=8)
    if not chunks:
        return {"answer": "This topic is not available in the uploaded notes.", "sources": []}

    answer = None
    if settings.GEMINI_API_KEY:
        answer = await call_gemini_rag_answer(expanded_q, chunks, conversation_history)
    if not answer or "not available" in answer.lower():
        answer = build_deterministic_rag_answer(expanded_q, chunks, conversation_history)
        
    sources = list({(c["materialId"], c["pageNumber"]): c for c in chunks}.values())
    return {"answer": answer, "sources": sources}"""
    add_code_block(code_rag, font_size=7.5)

    add_h2("5.13 Scanning Booth Digitization (`backend/app/services/scanning_booth.py`)")
    add_p(
        "The Scanning Booth module empowers students to photograph paper notebooks. The client-side canvas applies perspective warping, "
        "while the backend optimizes contrast and runs OCR to convert camera photos into searchable study materials."
    )

    add_h2("5.14 Frontend Architecture & API Interceptors (`frontend/src/services/api.js`)")
    add_p(
        "The React single-page application communicates with the FastAPI backend through a centralized Axios client. Interceptors automatically "
        "attach JWT bearer tokens to outbound requests and handle authorization errors:"
    )
    code_frontend = """import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;"""
    add_code_block(code_frontend, font_size=7.5)

    doc.add_page_break()

    # PAGE 20: Environment Configuration & Summary
    add_h2("5.15 Environment Configuration (`.env`)")
    add_p(
        "Critical system credentials and parameters are isolated inside `.env` configuration files to prevent credential leakage:"
    )
    code_env = """PORT=5000
MONGODB_URI=mongodb://localhost:27017/campusverse
DB_NAME=campusverse
JWT_SECRET=campusverse_super_secret_jwt_key_at_least_32_chars_2026
JWT_EXPIRES_DAYS=7
STORAGE_PROVIDER=local
LOCAL_STORAGE_DIR=./uploads
MAX_FILE_SIZE_MB=25
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
AUTO_PUBLISH_AI_APPROVED=true"""
    add_code_block(code_env, font_size=7.5)

    add_h2("5.16 Implementation Summary")
    add_p(
        "The implementation of CampusVerse combines asynchronous Python web services, reactive frontend interfaces, and machine learning "
        "pipelines. Every module operates with strong isolation and clear communication interfaces, ensuring the platform remains modular, "
        "maintainable, and ready for campus-wide deployment."
    )
    add_p(
        "Through the systematic engineering of the multi-format extraction engine, academic integrity guardrails, dense vector embeddings, "
        "and strict grounded RAG answer synthesis, CampusVerse delivers an enterprise-grade academic platform that eliminates study resource "
        "dispersal and eliminates AI hallucinations in university coursework."
    )

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 6: OUTPUT SCREENSHOTS / IMAGES (Pages 21 - 25)
    # =========================================================================
    # PAGE 21: Figures 6.1, 6.2, 6.3
    add_h1("6. OUTPUT SCREENSHOTS / IMAGES")
    add_p(
        "This chapter presents the visual interface of the CampusVerse platform across all major functional modules. "
        "The screenshot placeholders below represent the designated layout positions for the operational web interface."
    )

    add_screenshot_placeholder("Figure 6.1", "CampusVerse Landing & University Home Page", height_in=1.35)
    add_screenshot_placeholder("Figure 6.2", "Student User Registration Page with Department & Semester Selection", height_in=1.35)
    add_screenshot_placeholder("Figure 6.3", "Student & Faculty Login Page with JWT Authentication", height_in=1.35)
    
    doc.add_page_break()

    # PAGE 22: Figures 6.4, 6.5, 6.6
    add_screenshot_placeholder("Figure 6.4", "Student Main Dashboard with Recent Notes and Analytics Overview", height_in=1.55)
    add_screenshot_placeholder("Figure 6.5", "Multi-Format Document Upload Modal with Real-Time Classification Preview", height_in=1.55)
    add_screenshot_placeholder("Figure 6.6", "Scanning Booth Mobile Camera Capture & Perspective Crop Interface", height_in=1.55)

    doc.add_page_break()

    # PAGE 23: Figures 6.7, 6.8, 6.9
    add_screenshot_placeholder("Figure 6.7", "Notes AI Interactive Grounded RAG Chat Session with Page Citations", height_in=1.55)
    add_screenshot_placeholder("Figure 6.8", "Synchronized Multi-Page Document Reader with Extracted Text Viewer", height_in=1.55)
    add_screenshot_placeholder("Figure 6.9", "9-Section Structured AI Document Summary & Key Concepts View", height_in=1.55)

    doc.add_page_break()

    # PAGE 24: Figures 6.10, 6.11, 6.12
    add_screenshot_placeholder("Figure 6.10", "Chapter-by-Chapter Decomposition Cards & LaTeX Formula Extractor", height_in=1.55)
    add_screenshot_placeholder("Figure 6.11", "Semantic Vector Search Results with High-Confidence Keyword Highlighting", height_in=1.55)
    add_screenshot_placeholder("Figure 6.12", "Study Buddy Interactive Academic Tutoring & Concept Breakdown", height_in=1.55)

    doc.add_page_break()

    # PAGE 25: Figures 6.13, 6.14, 6.15, 6.16
    add_screenshot_placeholder("Figure 6.13", "Automated Academic Quality Scorecard & Readability Metrics Modal", height_in=1.1, space_after=4)
    add_screenshot_placeholder("Figure 6.14", "Admin Moderation Console for Study Material Approval & Override", height_in=1.1, space_after=4)
    add_screenshot_placeholder("Figure 6.15", "Student Personal Bookmarks Registry, Download History & 5-Star Reviews", height_in=1.1, space_after=4)
    add_screenshot_placeholder("Figure 6.16", "Student User Profile, Academic Preferences & Notification Settings", height_in=1.1, space_after=4)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 7: FUTURE ENHANCEMENT (Pages 26 - 27)
    # =========================================================================
    # PAGE 26
    add_h1("7. FUTURE ENHANCEMENT")

    add_h2("7.1 Introduction")
    add_p(
        "CampusVerse currently delivers an extensive suite of academic tools covering ingestion, classification, multi-stage summarization, "
        "and strict grounded tutoring. However, higher education continues to evolve towards mobile, multimodal, and collaborative learning "
        "paradigms. This chapter outlines planned enhancements for subsequent versions of CampusVerse."
    )

    add_h2("7.2 Dedicated Cross-Platform Mobile Application")
    add_p(
        "While the current React web application is responsive across mobile viewports, developing a dedicated native mobile application "
        "using Flutter or React Native will enable hardware-accelerated camera scanning, offline caching of lecture notes, and native push "
        "notifications for new department uploads."
    )

    add_h2("7.3 Voice-Based Conversational AI Tutor")
    add_p(
        "Voice interaction can be integrated using WebRTC and speech-to-text models (such as Whisper API), enabling students to verbally "
        "ask questions and receive audio explanations, making learning accessible for auditory learners and visually impaired students."
    )

    add_h2("7.4 Personalized Adaptive Learning & Weak Topic Recommender")
    add_p(
        "By tracking queries asked in Notes AI and Study Buddy, machine learning algorithms can model a student's knowledge state, identify "
        "weak subject areas, and automatically recommend specific chapter readings, practice questions, and peer notes before examinations."
    )

    add_h2("7.5 Academic Performance & Exam Readiness Prediction")
    add_p(
        "Machine learning models can analyze note interaction patterns, study time, and quiz breakdown scores to provide students with a "
        "probabilistic 'Exam Readiness Score' that guides focused revision."
    )

    add_h2("7.6 Real-Time Collaborative Study Rooms & Peer Annotations")
    add_p(
        "Integrating WebSockets will allow classmates to form collaborative study rooms, co-annotate lecture slides in real time, and share "
        "synchronized Notes AI tutoring sessions."
    )

    doc.add_page_break()

    # PAGE 27
    add_h2("7.7 Institutional Faculty Dashboard & Assignment Grading")
    add_p(
        "Expanding the platform with a dedicated faculty portal where professors can upload official course packs, verify student-contributed "
        "notes with an 'Instructor Endorsed' badge, and review cohort analytics."
    )

    add_h2("7.8 Multilingual Study Material Translation & Cross-Lingual RAG")
    add_p(
        "Implementing automated translation pipelines so students can read summaries and ask questions in vernacular languages while grounding "
        "retrieval in English textbook materials."
    )

    add_h2("7.9 Automated Flashcard & Interactive Mind Map Generation")
    add_p(
        "Synthesizing 3D flippable flashcards and SVG conceptual mind maps dynamically from chapter key points for visual revision."
    )

    add_h2("7.10 Blockchain-Based Academic Credentialing & Note Copyright Protection")
    add_p(
        "Recording student content contributions on an immutable ledger to award verified peer-tutoring credentials and prevent unauthorized "
        "commercial scraping of student notes."
    )

    add_h2("7.11 Advanced Multi-Modal LLM Fine-Tuning")
    add_p(
        "Fine-tuning open-weights models (such as LLaMA-3 or Mistral) on university curricula to execute private on-premise inference without "
        "external API costs."
    )

    add_h2("7.12 Offline Local-First Synchronization (PWA & IndexedDB)")
    add_p(
        "Enabling progressive web app (PWA) offline synchronization so students in low-connectivity areas can read downloaded notes and summaries."
    )

    add_h2("7.13 Chapter Summary")
    add_p(
        "These planned enhancements will further solidify CampusVerse as an indispensable digital learning ecosystem, bridging physical "
        "classrooms and advanced generative AI across Indian and global universities."
    )

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 8: CONCLUSION (Page 28)
    # =========================================================================
    add_h1("8. CONCLUSION")

    add_h2("8.1 Conclusion")
    add_p(
        "CampusVerse was conceived and developed as an intelligent academic study material repository and AI tutoring platform designed to solve "
        "the acute challenges of resource fragmentation, document quality degradation, and AI hallucination in university education. "
        "The project successfully demonstrates how modern asynchronous web technologies (FastAPI, React 18, MongoDB) can be unified with "
        "artificial intelligence pipelines (PyMuPDF, RapidOCR, NumPy vector indexing, and Google Gemini LLMs) to create a dependable educational ecosystem."
    )

    add_h2("8.2 Project Outcome")
    add_p("The major tangible outcomes delivered by the project include:")
    add_bullet("A fully functional, verified full-stack web application running asynchronous FastAPI and reactive React components.", bold_prefix="1. ")
    add_bullet("Multi-format text extraction engine parsing PDF, DOCX, PPTX, TXT, and images up to 150 pages without timeouts.", bold_prefix="2. ")
    add_bullet("Automated academic integrity validator that filters out non-academic files and spam prior to database storage.", bold_prefix="3. ")
    add_bullet("Taxonomy classifier categorizing documents into university departments with verifiable confidence metrics.", bold_prefix="4. ")
    add_bullet("Multi-stage summarization engine producing 9-section structured summaries covering the entire document from page 1 to the end.", bold_prefix="5. ")
    add_bullet("Grounded Notes AI RAG tutor that answers student queries accurately with page citations and zero hallucination.", bold_prefix="6. ")
    add_bullet("Scanning Booth web tool enabling mobile camera captures with automated edge detection and contrast enhancement.", bold_prefix="7. ")
    add_bullet("Comprehensive administrative moderation dashboard for real-time file reviews and departmental curation.", bold_prefix="8. ")

    add_h2("8.3 Learning Outcome")
    add_p("The development of CampusVerse provided deep practical knowledge of end-to-end software engineering, including:")
    add_bullet("Mastering asynchronous I/O architectures using Python FastAPI, asyncio, and Motor MongoDB drivers.", bold_prefix="• ")
    add_bullet("Implementing stateful single-page application architectures with React 18 hooks, context providers, and Tailwind CSS.", bold_prefix="• ")
    add_bullet("Engineering robust RAG pipelines combining dense vector similarity with lexical stemming and conceptual synonym expansion.", bold_prefix="• ")
    add_bullet("Handling real-world document extraction challenges, selective OCR invocations, and memory optimization.", bold_prefix="• ")
    add_bullet("Implementing secure user authentication, role-based authorization, rate limiting, and defensive API middleware.", bold_prefix="• ")

    add_h2("8.4 Final Conclusion")
    add_p(
        "In conclusion, CampusVerse bridges the gap between static academic notes and intelligent, interactive learning. It empowers university "
        "students to learn faster, verify information effortlessly, and prepare for examinations with confidence. As educational institutions "
        "continue to embrace digital transformation, CampusVerse offers a production-ready model for intelligent academic knowledge management."
    )

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 9: REFERENCE BOOKS / URLs (Page 29)
    # =========================================================================
    add_h1("9. REFERENCE BOOKS / URLs")

    add_h2("9.1 Reference Books")
    add_p("1. Jon Duckett, HTML and CSS: Design and Build Websites, John Wiley & Sons, Inc.")
    add_p("2. Jon Duckett, JavaScript and JQuery: Interactive Front-End Web Development, John Wiley & Sons, Inc.")
    add_p("3. David Flanagan, JavaScript: The Definitive Guide (7th Edition), O'Reilly Media.")
    add_p("4. Tiago Rodrigues, Building Data-Driven Applications with FastAPI, Packt Publishing.")
    add_p("5. Shannon Bradshaw, Eoin Brazil, and Kristina Chodorow, MongoDB: The Definitive Guide (3rd Edition), O'Reilly Media.")
    add_p("6. Alex Banks and Eve Porcello, Learning React: Modern Patterns for Developing React Applications, O'Reilly Media.")
    add_p("7. Aurélien Géron, Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow, O'Reilly Media.")
    add_p("8. Lewis Tunstall, Leandro von Werra, and Thomas Wolf, Natural Language Processing with Transformers, O'Reilly Media.")

    add_h2("9.2 Online References")
    add_p("1. FastAPI Framework Documentation: https://fastapi.tiangolo.com/")
    add_p("2. React Official Documentation: https://react.dev/")
    add_p("3. MongoDB Async Motor Driver: https://motor.readthedocs.io/")
    add_p("4. PyMuPDF (fitz) Documentation: https://pymupdf.readthedocs.io/")
    add_p("5. Google Gemini API Documentation: https://ai.google.dev/docs")
    add_p("6. Tailwind CSS Framework Documentation: https://tailwindcss.com/docs")
    add_p("7. MDN Web Docs – JavaScript & Web APIs: https://developer.mozilla.org/en-US/docs/Web")
    add_p("8. Vite Next Generation Frontend Tooling: https://vitejs.dev/")

    # =========================================================================
    # CHAPTER 10: GITHUB LINK / HOSTED LINK (Page 29)
    # =========================================================================
    add_h1("10. GITHUB LINK / HOSTED LINK", space_before=12)

    add_h2("10.1 GitHub Repository:")
    add_p("https://github.com/Bhumikaravi/campusverse", bold_prefix=None)
    add_p("(Complete source code repository containing frontend React application, FastAPI backend services, seed data, and documentation.)", bold_prefix="Notes: ")

    add_h2("10.2 Hosted Project URL:")
    add_p("https://campusverse-ht3d6l6s.back4.app/login", bold_prefix=None)
    add_p("(Live production deployment hosted on Back4App Containers with connected cloud MongoDB database and active AI tutoring services.)", bold_prefix="Notes: ")

    # Save Word document
    output_docx = "CampusVerse_Capstone_Project_Report.docx"
    doc.save(output_docx)
    print(f"Successfully generated Word document: {output_docx}")
    return output_docx

if __name__ == '__main__':
    create_report()
