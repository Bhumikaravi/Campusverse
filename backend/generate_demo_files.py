import os
import io
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import docx
from pptx import Presentation
from pptx.util import Inches, Pt
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAMPLE_DIRS = [
    os.path.join(ROOT_DIR, "sample_files"),
    os.path.join(ROOT_DIR, "public", "sample_files"),
]

for d in SAMPLE_DIRS:
    os.makedirs(d, exist_ok=True)

def copy_to_all(src_path, filename):
    for d in SAMPLE_DIRS:
        dst = os.path.join(d, filename)
        if os.path.abspath(src_path) != os.path.abspath(dst):
            shutil.copyfile(src_path, dst)

# ==============================================================================
# 1. OS CPU Scheduling Notes (PDF)
# ==============================================================================
def create_os_pdf():
    filename = "01_os_cpu_scheduling.pdf"
    target_path = os.path.join(SAMPLE_DIRS[0], filename)
    doc = SimpleDocTemplate(target_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=10
    )
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#34495E"),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=6
    )

    story = [
        Paragraph("Operating Systems: CPU Scheduling & Process Management", title_style),
        Paragraph("<b>Department:</b> Computer Science & Engineering | <b>Semester:</b> 4 | <b>Subject Code:</b> CS402", body_style),
        Paragraph("<b>Instructor:</b> Department of Computer Engineering | <b>Source:</b> CampusVerse Study Bank", body_style),
        Spacer(1, 12),
        Paragraph("1. Introduction to CPU Scheduling", h2_style),
        Paragraph(
            "CPU scheduling is the process by which the operating system decides which of the processes in the ready queue "
            "is to be allocated the CPU processing core. The goal of CPU scheduling is to maximize CPU utilization, throughput, "
            "and minimize turnaround time, waiting time, and response time.",
            body_style
        ),
        Spacer(1, 8),
        Paragraph("2. Comparative Analysis of Scheduling Algorithms", h2_style),
    ]

    table_data = [
        ["Algorithm", "Preemptive?", "Pros", "Cons / Drawbacks"],
        ["First-Come, First-Served (FCFS)", "No", "Simple to implement, fair order", "Convoy Effect, high average wait time"],
        ["Shortest Job First (SJF)", "Optional", "Optimal minimum average wait time", "Starvation of long jobs, CPU burst prediction difficult"],
        ["Round Robin (RR)", "Yes", "Fair CPU sharing, responsive for time-sharing", "High context-switching overhead if quantum is too small"],
        ["Priority Scheduling", "Optional", "Prioritizes mission-critical tasks", "Indefinite blocking / starvation (resolved via Aging)"]
    ]
    t = Table(table_data, colWidths=[130, 70, 150, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#34495E")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F8F9FA")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BDC3C7")),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("3. Solved Numerical Example: Round Robin (Time Quantum = 2ms)", h2_style))
    story.append(Paragraph(
        "Consider three processes: P1 (Burst Time = 5ms), P2 (Burst Time = 3ms), P3 (Burst Time = 1ms). All arrive at time 0.<br/>"
        "<b>Gantt Chart Execution:</b> [0-2: P1] -> [2-4: P2] -> [4-5: P3] -> [5-7: P1] -> [7-8: P2] -> [8-9: P1]<br/>"
        "<b>Completion Times:</b> P1 = 9ms, P2 = 8ms, P3 = 5ms.<br/>"
        "<b>Average Turnaround Time:</b> (9 + 8 + 5) / 3 = 7.33 ms.<br/>"
        "<b>Average Waiting Time:</b> [(9-5) + (8-3) + (5-1)] / 3 = (4 + 5 + 4) / 3 = 4.33 ms.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Exam Tips:</b> Always draw the Gantt chart clearly with accurate timestamps before computing completion, turnaround, and waiting times.", body_style))

    doc.build(story)
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

# ==============================================================================
# 2. DBMS SQL & Normalization (DOCX)
# ==============================================================================
def create_dbms_docx():
    filename = "02_dbms_sql_normalization.docx"
    target_path = os.path.join(SAMPLE_DIRS[0], filename)
    doc = docx.Document()

    doc.add_heading('Database Management Systems: SQL & Normalization Guide', 0)
    p = doc.add_paragraph()
    p.add_run('Department: Computer Science & Engineering | Semester: 4 | Subject: DBMS (CS403)\n').bold = True
    p.add_run('Author: Academic Study Circle | CampusVerse Verified Resource')

    doc.add_heading('1. Purpose of Database Normalization', level=1)
    doc.add_paragraph(
        'Normalization is the systematic approach of decomposing tables to eliminate data redundancy '
        'and undesirable insertion, update, and deletion anomalies. It guarantees data integrity through functional dependencies.'
    )

    doc.add_heading('2. Summary of Normal Forms', level=2)
    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Normal Form'
    hdr_cells[1].text = 'Primary Requirement'
    hdr_cells[2].text = 'Anomalies Eliminated'

    nf_data = [
        ('1NF (First Normal Form)', 'Atomic attribute values; no repeating groups or multivalued columns.', 'Basic storage inconsistencies.'),
        ('2NF (Second Normal Form)', 'Must be in 1NF and no partial dependencies (every non-prime attribute fully depends on candidate key).', 'Redundant data across composite keys.'),
        ('3NF (Third Normal Form)', 'Must be in 2NF and no transitive dependencies (non-prime cannot determine another non-prime).', 'Update and deletion anomalies.'),
        ('BCNF (Boyce-Codd)', 'Every functional dependency X -> Y requires X to be a superkey.', 'Redundancy from overlapping candidate keys.')
    ]
    for nf, req, rem in nf_data:
        row_cells = table.add_row().cells
        row_cells[0].text = nf
        row_cells[1].text = req
        row_cells[2].text = rem

    doc.add_heading('3. Essential SQL Queries for Semester Practicals', level=1)
    doc.add_paragraph('Query 1: Inner Join with Group By and Aggregate Functions')
    doc.add_paragraph(
        'SELECT d.dept_name, COUNT(s.student_id) AS total_students, AVG(s.gpa) AS avg_gpa\n'
        'FROM departments d\n'
        'LEFT JOIN students s ON d.dept_id = s.dept_id\n'
        'GROUP BY d.dept_name\n'
        'HAVING COUNT(s.student_id) > 5\n'
        'ORDER BY avg_gpa DESC;'
    )

    doc.save(target_path)
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

# ==============================================================================
# 3. Machine Learning Lab Manual (PDF)
# ==============================================================================
def create_ml_pdf():
    filename = "03_machine_learning_lab_manual.pdf"
    target_path = os.path.join(SAMPLE_DIRS[0], filename)
    doc = SimpleDocTemplate(target_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'MLTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=10
    )
    h2_style = ParagraphStyle(
        'MLHeading2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=12,
        spaceAfter=6
    )
    code_style = ParagraphStyle(
        'MLCode',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1F2937"),
        backColor=colors.HexColor("#F3F4F6"),
        spaceBefore=4,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'MLBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=5
    )

    story = [
        Paragraph("Machine Learning & AI Laboratory Manual", title_style),
        Paragraph("<b>Department:</b> AI & Data Science | <b>Semester:</b> 6 | <b>Course Code:</b> AD601L", body_style),
        Paragraph("<b>Academic Year:</b> 2026-2027 | <b>University Autonomous Syllabus</b>", body_style),
        Spacer(1, 10),
        Paragraph("Experiment 1: Linear Regression & Gradient Descent Optimization", h2_style),
        Paragraph(
            "<b>Objective:</b> Implement univariate linear regression from scratch using NumPy and visualize the cost function convergence.",
            body_style
        ),
        Paragraph(
            "<b>Mathematical Formulation:</b><br/>"
            "Hypothesis: h_theta(x) = theta_0 + theta_1 * x<br/>"
            "Cost Function (MSE): J(theta) = (1 / 2m) * sum((h_theta(x_i) - y_i)^2)<br/>"
            "Weight Update: theta_j := theta_j - alpha * (1/m) * sum((h_theta(x_i) - y_i) * x_i_j)",
            body_style
        ),
        Paragraph(
            "# Python Implementation snippet:<br/>"
            "import numpy as np<br/>"
            "def gradient_descent(X, y, lr=0.01, epochs=1000):<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;m, n = X.shape<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;theta = np.zeros(n)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;for _ in range(epochs):<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;errors = np.dot(X, theta) - y<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;theta -= (lr / m) * np.dot(X.T, errors)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;return theta",
            code_style
        ),
        Spacer(1, 8),
        Paragraph("Experiment 2: K-Means Clustering for Customer Segmentation", h2_style),
        Paragraph(
            "<b>Algorithm Steps:</b><br/>"
            "1. Randomly initialize K centroids from the dataset.<br/>"
            "2. Assign each observation to the nearest centroid using Euclidean distance: d(x, c) = sqrt(sum((x_i - c_i)^2)).<br/>"
            "3. Recalculate centroids as the arithmetic mean of all points assigned to that cluster.<br/>"
            "4. Repeat until centroid movement drops below threshold epsilon.",
            body_style
        ),
        Spacer(1, 10),
        Paragraph("<b>Lab Viva Questions:</b><br/>"
                  "1. How does learning rate affect gradient descent convergence?<br/>"
                  "2. Explain the Elbow method for choosing the optimal value of K.<br/>"
                  "3. What is the difference between L1 (Lasso) and L2 (Ridge) regularization?", body_style)
    ]

    doc.build(story)
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

# ==============================================================================
# 4. Computer Networks Cheatsheet (PNG)
# ==============================================================================
def create_cn_png():
    filename = "04_computer_networks_cheatsheet.png"
    target_path = os.path.join(SAMPLE_DIRS[0], filename)

    width, height = 900, 600
    img = Image.new("RGB", (width, height), color="#FAF7F2")
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([(0, 0), (width, 80)], fill="#3E362E")
    draw.text((30, 25), "CAMPUSVERSE ACADEMIC CHEATSHEET: OSI vs TCP/IP", fill="#FFFFFF")

    layers = [
        ("7. Application Layer", "HTTP, HTTPS, FTP, DNS, SMTP", "#E74C3C"),
        ("6. Presentation Layer", "SSL/TLS, JPEG, ASCII, Encryption", "#E67E22"),
        ("5. Session Layer", "NetBIOS, RPC, Session Management", "#F1C40F"),
        ("4. Transport Layer", "TCP (Reliable, 3-way handshake), UDP", "#2ECC71"),
        ("3. Network Layer", "IP (IPv4, IPv6), ICMP, ARP, Routing", "#1ABC9C"),
        ("2. Data Link Layer", "Ethernet 802.3, MAC Addressing, Switches", "#3498DB"),
        ("1. Physical Layer", "Cables, Hubs, Bits, Modulation, Fiber", "#9B59B6"),
    ]

    y_start = 110
    box_height = 55
    spacing = 12

    for i, (name, protocols, color) in enumerate(layers):
        y = y_start + i * (box_height + spacing)
        # Colored badge
        draw.rounded_rectangle([(40, y), (360, y + box_height)], radius=8, fill=color)
        draw.text((60, y + 18), name, fill="#FFFFFF")
        # Description box
        draw.rounded_rectangle([(380, y), (860, y + box_height)], radius=8, fill="#FFFFFF", outline="#D5C7B7", width=2)
        draw.text((400, y + 18), protocols, fill="#3E362E")

    img.save(target_path, "PNG")
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

# ==============================================================================
# 5. Data Structures Question Bank / Past Paper (PDF)
# ==============================================================================
def create_dsa_exam_pdf():
    filename = "05_data_structures_past_paper.pdf"
    target_path = os.path.join(SAMPLE_DIRS[0], filename)
    doc = SimpleDocTemplate(target_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PaperTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        alignment=1, # Center
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=6
    )
    sub_style = ParagraphStyle(
        'PaperSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=12
    )
    body_style = ParagraphStyle(
        'PaperBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6
    )

    story = [
        Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING", title_style),
        Paragraph("B.Tech Degree Mid-Semester Examination — Semester III<br/><b>CS301: DATA STRUCTURES & ALGORITHMS</b><br/>Time: 3 Hours | Max Marks: 100", sub_style),
        Spacer(1, 8),
        Paragraph("<b>PART A (Answer all 10 questions — 10 x 2 = 20 Marks)</b>", body_style),
        Paragraph("1. Define Big-O notation and provide the tight upper bound of binary search.", body_style),
        Paragraph("2. Differentiate between an Array and a Singly Linked List in terms of random access.", body_style),
        Paragraph("3. Write the prefix form of the infix expression: (A + B) * (C - D) / E.", body_style),
        Paragraph("4. State the balance factor condition for an AVL Tree node.", body_style),
        Paragraph("5. What is the worst-case time complexity of QuickSort and how can it be avoided?", body_style),
        Spacer(1, 10),
        Paragraph("<b>PART B (Answer all 5 questions — 5 x 16 = 80 Marks)</b>", body_style),
        Paragraph("<b>11. (a)</b> Construct an AVL Tree by inserting the following sequence: 40, 20, 10, 25, 30, 22, 50. Show the LL, RR, LR, or RL rotations at every rebalancing step. <i>(16 Marks)</i>", body_style),
        Paragraph("<b>12. (a)</b> Explain Dijkstra's Shortest Path algorithm on a weighted directed graph with pseudocode and time complexity analysis using a priority queue (min-heap). <i>(16 Marks)</i>", body_style),
        Paragraph("<b>13. (a)</b> Describe the 0/1 Knapsack problem using Dynamic Programming. Tabulate the values for Capacity W=7 and items with weights [2, 3, 4] and values [3, 4, 5]. <i>(16 Marks)</i>", body_style),
        Spacer(1, 14),
        Paragraph("--- END OF QUESTION PAPER ---", sub_style)
    ]

    doc.build(story)
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

# ==============================================================================
# 6. Embedded Systems Slides (PPTX)
# ==============================================================================
def create_embedded_pptx():
    filename = "06_embedded_systems_slides.pptx"
    target_path = os.path.join(SAMPLE_DIRS[0], filename)
    prs = Presentation()

    # Slide 1: Title
    slide1 = prs.slides.add_slide(prs.slide_layouts[0])
    slide1.shapes.title.text = "Embedded Systems & IoT Architecture"
    slide1.placeholders[1].text = "Department of Electronics & Communication Engineering\nSemester 5 — EC504 Lecture Slides"

    # Slide 2: Microcontroller vs Microprocessor
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Microcontroller vs Microprocessor"
    tf2 = slide2.placeholders[1].text_frame
    tf2.text = "Key Architectural Differences:"
    p = tf2.add_paragraph()
    p.text = "• Microcontroller: Self-contained with CPU, RAM, ROM/Flash, Timers, and ADC on single chip."
    p = tf2.add_paragraph()
    p.text = "• Microprocessor: General-purpose compute core requiring external memory and peripherals."
    p = tf2.add_paragraph()
    p.text = "• ARM Cortex-M: Ideal for low-power deterministic embedded control applications."

    # Slide 3: Communication Protocols
    slide3 = prs.slides.add_slide(prs.slide_layouts[1])
    slide3.shapes.title.text = "Serial Bus Protocols: UART, I2C, and SPI"
    tf3 = slide3.placeholders[1].text_frame
    tf3.text = "Protocol Comparison for Sensor Interfacing:"
    p = tf3.add_paragraph()
    p.text = "• I2C (Inter-Integrated Circuit): 2-wire bus (SDA, SCL), synchronous, master-multi-slave addressing."
    p = tf3.add_paragraph()
    p.text = "• SPI (Serial Peripheral Interface): 4-wire bus (MOSI, MISO, SCK, CS), full duplex, high speed."
    p = tf3.add_paragraph()
    p.text = "• UART: Asynchronous point-to-point serial communication with configurable baud rate."

    prs.save(target_path)
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

# ==============================================================================
# 7. Additional study guides and schemas (JSON / Markdown / Code)
# ==============================================================================
def create_text_resources():
    # JSON syllabus
    json_path = os.path.join(SAMPLE_DIRS[0], "syllabus_cse_2026.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write('''{
  "department": "Computer Science & Engineering",
  "curriculum": "Autonomous 2026",
  "semesters": [
    {
      "semester": 3,
      "courses": ["Data Structures & Algorithms", "Engineering Mathematics III", "Digital Logic Design"]
    },
    {
      "semester": 4,
      "courses": ["Operating Systems", "Database Management Systems", "Design & Analysis of Algorithms"]
    },
    {
      "semester": 5,
      "courses": ["Computer Networks", "Software Engineering", "Theory of Computation"]
    },
    {
      "semester": 6,
      "courses": ["Artificial Intelligence & Machine Learning", "Compiler Design", "Cloud Computing"]
    }
  ]
}''')
    copy_to_all(json_path, "syllabus_cse_2026.json")

    # Markdown study guide
    md_path = os.path.join(SAMPLE_DIRS[0], "study_plan_guide.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write('''# CampusVerse Student Study Plan Guide

## Effective 4-Week Exam Preparation
1. **Week 1 (Concept Mapping)**: Review verified lecture slides and core textbooks.
2. **Week 2 (Practical Application)**: Complete lab manual code exercises and SQL queries.
3. **Week 3 (Past Papers)**: Solve previous semester question banks under timed conditions.
4. **Week 4 (Revision & Flashcards)**: Focus on cheatsheets, formulas, and high-yield topics.
''')
    copy_to_all(md_path, "study_plan_guide.md")

    # Python reference
    py_path = os.path.join(SAMPLE_DIRS[0], "algorithms_reference.py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write('''"""
CampusVerse Code Reference: Binary Search and MergeSort Implementation
"""
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1

def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    res, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            res.append(left[i])
            i += 1
        else:
            res.append(right[j])
            j += 1
    res.extend(left[i:])
    res.extend(right[j:])
    return res
''')
    copy_to_all(py_path, "algorithms_reference.py")
    print("Generated text resources (JSON, MD, PY)")

if __name__ == "__main__":
    create_os_pdf()
    create_dbms_docx()
    create_ml_pdf()
    create_cn_png()
    create_dsa_exam_pdf()
    create_embedded_pptx()
    create_text_resources()
    print("All sample files generated successfully!")
