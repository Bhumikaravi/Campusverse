import os
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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

def build_pdf(filename, title, dept, sem, course_code, sections, table_data=None):
    target_path = os.path.join(SAMPLE_DIRS[0], filename)
    doc = SimpleDocTemplate(target_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    t_style = ParagraphStyle(
        'DocT',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=8
    )
    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#7F8C8D"),
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#34495E"),
        spaceBefore=12,
        spaceAfter=6
    )
    b_style = ParagraphStyle(
        'DocB',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=6
    )

    story = [
        Paragraph(title, t_style),
        Paragraph(f"<b>Department:</b> {dept} | <b>Semester:</b> {sem} | <b>Code:</b> {course_code}<br/>CampusVerse Peer-Reviewed Academic Document", sub_style),
        Spacer(1, 8)
    ]

    for sec_title, sec_content in sections:
        story.append(Paragraph(sec_title, h2_style))
        story.append(Paragraph(sec_content, b_style))
        story.append(Spacer(1, 6))

    if table_data:
        t = Table(table_data, colWidths=[120, 160, 220])
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
            ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ]))
        story.append(t)

    doc.build(story)
    copy_to_all(target_path, filename)
    print(f"Generated {filename}")

def generate_all():
    # 7. Mechanical Engineering - Thermodynamics
    build_pdf(
        filename="07_mechanical_thermodynamics.pdf",
        title="Engineering Thermodynamics - Laws, Cycles & Entropy",
        dept="Mechanical Engineering",
        sem=3,
        course_code="ME301",
        sections=[
            ("1. Zeroth and First Laws of Thermodynamics", "The First Law states that energy cannot be created or destroyed, only transformed: dQ = dU + dW. For a closed system undergoing a process, the net heat transfer equals the change in internal energy plus work done."),
            ("2. Second Law & Carnot Efficiency", "Kelvin-Planck and Clausius statements establish the directional nature of heat engines and refrigerators. The maximum theoretical efficiency is defined by the Carnot engine: eta = 1 - (T_cold / T_hot)."),
            ("3. Practical Power Cycles", "Otto cycle (petrol engines), Diesel cycle (compression-ignition engines), and Rankine cycle (steam power plants) form the backbone of modern power generation.")
        ],
        table_data=[
            ["Cycle Name", "Working Fluid", "Key Characteristics"],
            ["Carnot Cycle", "Ideal Gas", "Two reversible isothermals and two adiabatics; maximum efficiency"],
            ["Otto Cycle", "Air / Gas Mixture", "Constant volume heat addition; four-stroke IC engines"],
            ["Rankine Cycle", "Water / Steam", "Phase change during boiling and condensation; thermal power generation"]
        ]
    )

    # 8. Civil Engineering - Structural Analysis
    build_pdf(
        filename="08_civil_structural_analysis.pdf",
        title="Structural Analysis & RCC Design Fundamentals",
        dept="Civil Engineering",
        sem=4,
        course_code="CE402",
        sections=[
            ("1. Shear Force & Bending Moment Diagrams", "Shear force (V) is the algebraic sum of vertical forces acting on either side of a beam section. Bending moment (M) is the algebraic sum of moments of forces about that section: dM/dx = V."),
            ("2. Limit State Design for Concrete Structures", "According to IS 456:2000, structures must satisfy limit states of collapse (flexure, compression, shear, torsion) and serviceability (deflection, cracking)."),
            ("3. Soil Mechanics & Shallow Foundations", "Terzaghi's bearing capacity equation computes ultimate bearing capacity based on soil cohesion, surcharge depth, and unit weight.")
        ]
    )

    # 9. Electrical Engineering - Power Systems
    build_pdf(
        filename="09_electrical_power_systems.pdf",
        title="Power Systems Analysis & Electrical Machines",
        dept="Electrical Engineering",
        sem=5,
        course_code="EE501",
        sections=[
            ("1. Transmission Line Models & Performance", "Transmission lines are modeled as Short (<80 km), Medium (80-250 km, Nominal Pi/T models), and Long (>250 km, distributed parameters via wave propagation constants)."),
            ("2. Symmetrical Components & Fault Analysis", "Any unbalanced three-phase system can be decomposed into Positive (V1), Negative (V2), and Zero (V0) sequence symmetrical components using Fortescue's theorem."),
            ("3. Synchronous Machines & Stability", "Swing equation governs rotor dynamics during disturbances: (H / pi*f0) * (d^2 delta / dt^2) = P_mech - P_elec.")
        ]
    )

    # 10. Engineering Mathematics - Advanced Calculus
    build_pdf(
        filename="10_engineering_math_calculus.pdf",
        title="Engineering Mathematics III - Fourier & Laplace Transforms",
        dept="Engineering Mathematics",
        sem=3,
        course_code="MA301",
        sections=[
            ("1. Fourier Series & Dirichlet Conditions", "Any periodic function f(x) satisfying Dirichlet conditions can be represented as: f(x) = a0/2 + sum(an*cos(nx) + bn*sin(nx)). Used to decompose complex signals into harmonic constituents."),
            ("2. Laplace Transforms & Initial Value Problems", "Laplace transform converts differential equations in the time domain into algebraic equations in the s-domain: L{f(t)} = integral(0 to inf, e^(-st)*f(t) dt)."),
            ("3. Partial Differential Equations (Wave & Heat)", "One-dimensional wave equation (d^2 u/dt^2 = c^2 * d^2 u/dx^2) and Heat conduction equation solved using separation of variables.")
        ]
    )

    # 11. Information Technology - Cloud Computing
    build_pdf(
        filename="11_it_cloud_computing.pdf",
        title="Cloud Computing & Distributed Systems Architecture",
        dept="Information Technology",
        sem=6,
        course_code="IT603",
        sections=[
            ("1. Service Models (IaaS, PaaS, SaaS)", "IaaS provides virtualized hardware (AWS EC2), PaaS provides runtime platforms (Google App Engine), and SaaS provides ready applications (Google Workspace, Office 365)."),
            ("2. Microservices & Container Orchestration", "Docker containers decouple application code from host dependencies. Kubernetes orchestrates deployments, scaling, and rolling updates across container clusters."),
            ("3. CAP Theorem & Distributed Data Stores", "A distributed data store can guarantee at most two of three properties: Consistency, Availability, and Partition Tolerance.")
        ]
    )

    # 12. AI & Data Science - Deep Learning
    build_pdf(
        filename="12_aids_deep_learning_neural_nets.pdf",
        title="Deep Learning & Neural Network Architectures",
        dept="AI & Data Science",
        sem=7,
        course_code="AD702",
        sections=[
            ("1. Multilayer Perceptrons & Backpropagation", "Forward pass computes activations layer by layer: z^[l] = W^[l]*a^[l-1] + b^[l]. Backpropagation uses the chain rule to compute gradients of the loss with respect to weights."),
            ("2. Convolutional Neural Networks (CNNs)", "Convolutional layers apply spatial filters to extract translation-invariant visual features, followed by ReLU activations and max-pooling."),
            ("3. Recurrent Architectures & Transformers", "LSTMs and GRUs address vanishing gradients in sequential data. Transformers use multi-head self-attention mechanisms to process sequence tokens in parallel.")
        ]
    )

    # 13. Electronics & Communication - Digital Signals
    build_pdf(
        filename="13_ece_digital_signals.pdf",
        title="Digital Signal Processing - Sampling, DFT & FFT",
        dept="Electronics & Communication",
        sem=5,
        course_code="EC502",
        sections=[
            ("1. Nyquist-Shannon Sampling Theorem", "A continuous-time signal must be sampled at a rate fs >= 2*f_max to reconstruct the original signal without aliasing distortion."),
            ("2. Discrete Fourier Transform & Radix-2 FFT", "Cooley-Tukey Radix-2 FFT algorithm reduces computational complexity from O(N^2) to O(N log2 N) using divide-and-conquer twiddle factors."),
            ("3. Digital Filter Design (FIR vs IIR)", "FIR filters are inherently stable with linear phase characteristics; IIR filters achieve sharper cutoff responses with lower order polynomials.")
        ]
    )

    # 14. Mechanical Engineering - Fluid Mechanics
    build_pdf(
        filename="14_mechanical_fluid_mechanics.pdf",
        title="Fluid Mechanics & Hydraulic Machinery Notes",
        dept="Mechanical Engineering",
        sem=4,
        course_code="ME402",
        sections=[
            ("1. Fluid Statics & Pascal's Principle", "Pressure in a static fluid acts equally in all directions: P = rho * g * h. Buoyancy force equals the weight of the fluid displaced according to Archimedes."),
            ("2. Bernoulli's Equation for Incompressible Flow", "Conservation of mechanical energy along a streamline: P/rho + v^2/2 + g*z = constant. Applies to Venturi meters and Pitot tubes."),
            ("3. Boundary Layer Theory & Drag Force", "Prandtl's boundary layer concept explains friction drag and flow separation over aerofoils and immersed cylinders.")
        ]
    )

if __name__ == "__main__":
    generate_all()
    print("All additional department files generated successfully!")
