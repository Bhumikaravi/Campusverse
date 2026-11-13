import os
import shutil
import hashlib
from datetime import datetime, timedelta, timezone
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

async def seed_materials():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["campusverse"]

    student = await db["users"].find_one({"email": "bhumikaravi2006@gmail.com"})
    if not student:
        student = await db["users"].find_one({"role": "student"})
    if not student:
        raise RuntimeError("No student user found in database.")

    student_id = str(student["_id"])
    uploader_name = student.get("full_name") or student.get("name") or "Bhumika Ravi"

    print(f"Seeding full demo materials catalog for student: {uploader_name} ({student_id})")

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(backend_dir, "uploads", "materials", student_id)
    os.makedirs(uploads_dir, exist_ok=True)

    sample_files_dir = os.path.abspath(os.path.join(backend_dir, "..", "sample_files"))

    demo_items = [
        # --- COMPUTER SCIENCE & ENGINEERING ---
        {
            "filename": "01_os_cpu_scheduling.pdf",
            "title": "Operating Systems - CPU Scheduling & Process Management",
            "subject": "Operating Systems",
            "department": "Computer Science & Engineering",
            "semester": 4,
            "category": "notes",
            "description": "Complete lecture notes on FCFS, SJF, Round Robin, and Priority CPU scheduling with solved numerical examples and Gantt charts.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 1420,
            "rating": 4.9,
            "ratingCount": 118,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.98, "reason": "High-quality academic operating systems notes.", "flags": [], "topics": ["Operating Systems", "CPU Scheduling"]}
        },
        {
            "filename": "02_dbms_sql_normalization.docx",
            "title": "Database Management Systems (DBMS) - SQL & Normalization Guide",
            "subject": "Database Management Systems",
            "department": "Computer Science & Engineering",
            "semester": 4,
            "category": "notes",
            "description": "Comprehensive reference covering functional dependencies, 1NF to BCNF decomposition rules, and practical multi-table SQL queries.",
            "extension": ".docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "downloads": 1280,
            "rating": 4.8,
            "ratingCount": 94,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.96, "reason": "Well-structured database theory and SQL queries.", "flags": [], "topics": ["DBMS", "Normalization"]}
        },
        {
            "filename": "05_data_structures_past_paper.pdf",
            "title": "Data Structures & Algorithms - Solved Mid-Term Question Paper",
            "subject": "Data Structures & Algorithms",
            "department": "Computer Science & Engineering",
            "semester": 3,
            "category": "past-papers",
            "description": "University examination question paper covering Big-O analysis, AVL tree rotations, Dijkstra shortest path, and 0/1 Knapsack problem.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 2100,
            "rating": 5.0,
            "ratingCount": 180,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.97, "reason": "Authentic academic examination questions with mark breakdowns.", "flags": [], "topics": ["DSA", "AVL Tree"]}
        },

        # --- INFORMATION TECHNOLOGY ---
        {
            "filename": "04_computer_networks_cheatsheet.png",
            "title": "Computer Networks - OSI vs TCP/IP Protocol Stack Cheatsheet",
            "subject": "Computer Networks",
            "department": "Information Technology",
            "semester": 5,
            "category": "notes",
            "description": "High-resolution reference diagram comparing the 7 layers of OSI with TCP/IP architecture, mapping protocols and data units.",
            "extension": ".png",
            "mimeType": "image/png",
            "downloads": 1640,
            "rating": 4.9,
            "ratingCount": 152,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.99, "reason": "Clear and verified academic networking diagram.", "flags": [], "topics": ["Computer Networks", "OSI Model"]}
        },
        {
            "filename": "11_it_cloud_computing.pdf",
            "title": "Cloud Computing & Distributed Systems Architecture",
            "subject": "Cloud Computing",
            "department": "Information Technology",
            "semester": 6,
            "category": "notes",
            "description": "Detailed notes on IaaS, PaaS, SaaS, Docker containers, Kubernetes orchestration, and CAP theorem for distributed databases.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 980,
            "rating": 4.8,
            "ratingCount": 76,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.96, "reason": "Well-organized cloud and distributed systems notes.", "flags": [], "topics": ["Cloud Computing", "Kubernetes"]}
        },

        # --- ELECTRONICS & COMMUNICATION ---
        {
            "filename": "06_embedded_systems_slides.pptx",
            "title": "Embedded Systems & IoT Architecture - Lecture Slide Deck",
            "subject": "Embedded Systems",
            "department": "Electronics & Communication",
            "semester": 5,
            "category": "slides",
            "description": "Presentation slides covering Microcontroller vs Microprocessor architecture, ARM Cortex, and serial bus protocols (I2C, SPI, UART).",
            "extension": ".pptx",
            "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "downloads": 750,
            "rating": 4.7,
            "ratingCount": 42,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.95, "reason": "Verified lecture presentation slides on embedded hardware.", "flags": [], "topics": ["Embedded Systems", "ARM Cortex"]}
        },
        {
            "filename": "13_ece_digital_signals.pdf",
            "title": "Digital Signal Processing - Sampling, DFT & FFT Analysis",
            "subject": "Digital Signal Processing",
            "department": "Electronics & Communication",
            "semester": 5,
            "category": "notes",
            "description": "Comprehensive guide on Nyquist sampling, Cooley-Tukey Radix-2 FFT algorithm, and FIR vs IIR digital filter design.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 820,
            "rating": 4.8,
            "ratingCount": 61,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.97, "reason": "Accurate digital signal processing formulations.", "flags": [], "topics": ["DSP", "Fourier Transform"]}
        },

        # --- MECHANICAL ENGINEERING ---
        {
            "filename": "07_mechanical_thermodynamics.pdf",
            "title": "Engineering Thermodynamics - Laws, Power Cycles & Entropy",
            "subject": "Thermodynamics",
            "department": "Mechanical Engineering",
            "semester": 3,
            "category": "notes",
            "description": "In-depth notes on Zeroth, First, and Second Laws of Thermodynamics, Carnot efficiency, Otto cycle, and Rankine cycle.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 1150,
            "rating": 4.9,
            "ratingCount": 89,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.98, "reason": "Comprehensive thermodynamics course notes.", "flags": [], "topics": ["Thermodynamics", "Carnot Cycle"]}
        },
        {
            "filename": "14_mechanical_fluid_mechanics.pdf",
            "title": "Fluid Mechanics & Hydraulic Machinery Notes",
            "subject": "Fluid Mechanics",
            "department": "Mechanical Engineering",
            "semester": 4,
            "category": "notes",
            "description": "Covers fluid statics, Pascal principle, Bernoulli incompressible flow equation, and Prandtl boundary layer theory.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 890,
            "rating": 4.7,
            "ratingCount": 54,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.96, "reason": "Verified fluid dynamics study guide.", "flags": [], "topics": ["Fluid Mechanics", "Bernoulli"]}
        },

        # --- CIVIL ENGINEERING ---
        {
            "filename": "08_civil_structural_analysis.pdf",
            "title": "Structural Analysis & RCC Design Fundamentals",
            "subject": "Structural Analysis",
            "department": "Civil Engineering",
            "semester": 4,
            "category": "notes",
            "description": "Essential study guide covering Shear Force & Bending Moment Diagrams, IS 456 Limit State Design, and Terzaghi soil mechanics.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 940,
            "rating": 4.8,
            "ratingCount": 68,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.97, "reason": "Clear civil engineering structural concepts.", "flags": [], "topics": ["Structural Analysis", "RCC Design"]}
        },

        # --- ELECTRICAL ENGINEERING ---
        {
            "filename": "09_electrical_power_systems.pdf",
            "title": "Power Systems Analysis & Electrical Machines",
            "subject": "Power Systems",
            "department": "Electrical Engineering",
            "semester": 5,
            "category": "notes",
            "description": "Notes covering Transmission Line Pi/T models, Fortescue Symmetrical Fault Analysis, and Swing Equation for stability.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 1050,
            "rating": 4.8,
            "ratingCount": 73,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.96, "reason": "Detailed electrical power transmission formulations.", "flags": [], "topics": ["Power Systems", "Transmission Lines"]}
        },

        # --- AI & DATA SCIENCE ---
        {
            "filename": "12_aids_deep_learning_neural_nets.pdf",
            "title": "Deep Learning & Neural Network Architectures",
            "subject": "Deep Learning",
            "department": "AI & Data Science",
            "semester": 7,
            "category": "notes",
            "description": "Comprehensive notes covering Multilayer Perceptrons, Backpropagation calculus, CNN visual feature extraction, and Transformer self-attention.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 1560,
            "rating": 4.9,
            "ratingCount": 134,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.99, "reason": "Thorough and modern deep learning tutorial notes.", "flags": [], "topics": ["Deep Learning", "CNN", "Transformers"]}
        },
        {
            "filename": "03_machine_learning_lab_manual.pdf",
            "title": "Machine Learning & AI - Complete Practical Lab Manual",
            "subject": "Machine Learning",
            "department": "AI & Data Science",
            "semester": 6,
            "category": "lab-manuals",
            "description": "Lab experiments for Linear Regression, Gradient Descent, K-Means Clustering, and Evaluation Metrics with NumPy code snippets.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 890,
            "rating": 4.9,
            "ratingCount": 67,
            "status": "PENDING", # For demonstrating Admin approval queue!
            "aiReview": {
                "decision": "NEEDS_REVIEW",
                "confidence": 0.88,
                "reason": "Contains Python code implementations. Queued for moderator approval.",
                "flags": ["CODE_SNIPPETS_DETECTED"],
                "topics": ["Machine Learning", "Linear Regression", "K-Means"]
            }
        },

        # --- ENGINEERING MATHEMATICS ---
        {
            "filename": "10_engineering_math_calculus.pdf",
            "title": "Engineering Mathematics III - Fourier & Laplace Transforms",
            "subject": "Engineering Mathematics",
            "department": "Engineering Mathematics",
            "semester": 3,
            "category": "notes",
            "description": "Complete solved problems covering Fourier Series, Dirichlet conditions, Laplace Transforms of initial value problems, and PDEs.",
            "extension": ".pdf",
            "mimeType": "application/pdf",
            "downloads": 1720,
            "rating": 4.9,
            "ratingCount": 145,
            "status": "ADMIN_APPROVED",
            "aiReview": {"decision": "APPROVED", "confidence": 0.98, "reason": "Excellent mathematical proofs and solved differential equations.", "flags": [], "topics": ["Fourier Series", "Laplace Transforms"]}
        }
    ]

    await db["materials"].delete_many({})
    await db["bookmarks"].delete_many({})
    await db["reviews"].delete_many({})

    seeded_ids = []

    for item in demo_items:
        src_path = os.path.join(sample_files_dir, item["filename"])
        if not os.path.exists(src_path):
            print(f"Skipping {item['filename']} (file not found)")
            continue

        file_size = os.path.getsize(src_path)
        file_hash = get_sha256(src_path)

        storage_rel_key = f"materials/{student_id}/{item['filename']}"
        dest_path = os.path.join(uploads_dir, item["filename"])
        shutil.copyfile(src_path, dest_path)

        now = datetime.now(timezone.utc) - timedelta(days=len(seeded_ids) + 1)
        material_doc = {
            "title": item["title"],
            "description": item["description"],
            "department": item["department"],
            "semester": item["semester"],
            "subject": item["subject"],
            "category": item["category"],
            "uploader": student_id,
            "uploaderName": uploader_name,
            "storageKey": storage_rel_key,
            "storageProvider": "local",
            "originalName": item["filename"],
            "mimeType": item["mimeType"],
            "extension": item["extension"],
            "size": file_size,
            "fileHash": file_hash,
            "status": item["status"],
            "aiReview": item["aiReview"],
            "moderation": {
                "moderatedBy": "System Admin",
                "moderatedAt": now,
                "note": "Verified by department moderator for syllabus compliance."
            } if item["status"] == "ADMIN_APPROVED" else None,
            "downloads": item["downloads"],
            "rating": item["rating"],
            "ratingCount": item["ratingCount"],
            "createdAt": now,
            "updatedAt": now
        }

        res = await db["materials"].insert_one(material_doc)
        mat_id = str(res.inserted_id)
        await db["materials"].update_one(
            {"_id": res.inserted_id},
            {"$set": {"fileUrl": f"/api/materials/{mat_id}/file"}}
        )
        seeded_ids.append(mat_id)
        print(f"Seeded [{item['department']}]: {item['title']} ({item['status']})")

    if seeded_ids:
        await db["bookmarks"].insert_one({
            "userId": student_id,
            "materialId": seeded_ids[0],
            "createdAt": datetime.now(timezone.utc)
        })
        await db["reviews"].insert_one({
            "materialId": seeded_ids[0],
            "userId": student_id,
            "userName": uploader_name,
            "rating": 5,
            "comment": "Exceptionally clear Gantt chart explanations and practice problems!",
            "createdAt": datetime.now(timezone.utc)
        })

    print(f"\nSuccessfully seeded all {len(seeded_ids)} materials across all 8 academic departments!")

if __name__ == "__main__":
    asyncio.run(seed_materials())
