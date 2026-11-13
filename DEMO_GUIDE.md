# CampusVerse — Second Project Review Demonstration Guide 🎓

Welcome to the live demonstration guide for **CampusVerse** (Full-Stack Academic Study Material & AI Moderation Platform). This guide provides everything you need to execute a flawless, confident, and professional live review on Saturday.

---

## 1. Quick Launch Instructions

You can start both the FastAPI backend and Vite frontend with a single click:

### Option A: One-Click Startup (Recommended for Presentation)
Double-click `start-dev.bat` in the project root, or in PowerShell run:
```powershell
.\start-dev.bat
```
This automatically launches:
- **FastAPI Backend**: `http://localhost:5000` (API Docs: `http://localhost:5000/docs`)
- **Vite React Frontend**: `http://localhost:5173`

### Option B: Manual Command Line
In Terminal 1 (Backend):
```powershell
cd backend
python -m uvicorn main:app --reload --port 5000
```
In Terminal 2 (Frontend):
```powershell
npm run dev
```

---

## 2. One-Click Demo Reset / Re-Seeding

To reset the demonstration state to a fresh, clean baseline at any time before or after your presentation, run:
```powershell
npm run seed:demo
```
Or directly:
```powershell
python backend/seed_demo_materials.py
```
To verify all APIs and file stream endpoints end-to-end:
```powershell
npm run test:demo
```

---

## 3. Demo Credentials

| Role | Email | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Student** | `bhumikaravi2006@gmail.com` | *(Existing Session / Logged in)* | Uploading notes, viewing dashboard, bookmarks, and downloads |
| **Administrator** | `admin@campusverse.edu` | `Admin@123` | Demonstrating the live Moderator Approval Queue and AI review analysis |

---

## 4. Inventory of Sample Files (`sample_files/`)

All demo materials are located in the dedicated `sample_files/` directory and also served via `public/sample_files/`:

| Filename | Format | Complexity | Subject & Department | Purpose in Live Review |
| :--- | :--- | :--- | :--- | :--- |
| **`01_os_cpu_scheduling.pdf`** | PDF (3.2 KB) | Medium | OS (CSE - Sem 4) | Tests PDF text parsing, inline PDF viewer modal, zoom & rotation controls. |
| **`02_dbms_sql_normalization.docx`** | DOCX (36.3 KB) | Medium | DBMS (CSE - Sem 4) | Tests OpenXML parsing, table extraction, and clean HTML in-browser rendering. |
| **`03_machine_learning_lab_manual.pdf`** | PDF (3.1 KB) | Complex | ML & AI (AI&DS - Sem 6) | Tests AI moderation pipeline; currently set to `PENDING` to demo Admin review. |
| **`04_computer_networks_cheatsheet.png`** | Image/PNG (26.5 KB) | Small | Computer Networks (IT - Sem 5) | Tests image magic-byte security scanning and inline responsive image preview. |
| **`05_data_structures_past_paper.pdf`** | PDF (2.9 KB) | Medium | DSA (CSE - Sem 3) | Demonstrates Past Papers category, examination mark schemes, and download tracking. |
| **`06_embedded_systems_slides.pptx`** | PPTX (30.5 KB) | Medium | Embedded Systems (ECE - Sem 5) | Tests slide presentation deck parser with interactive Next/Previous slide viewer. |
| **`syllabus_cse_2026.json`** | JSON | Structured | Academic Curriculum | Demonstrates structured syllabus schema. |
| **`study_plan_guide.md`** | Markdown | Text | Exam Preparation | General student revision guide. |
| **`algorithms_reference.py`** | Python | Code | DSA Implementations | Reference code implementation for binary search & mergesort. |

---

## 5. Step-by-Step Live Demonstration Script

Follow these 5 steps to showcase the full depth of your engineering project:

### Step 1: Homepage & Interactive Search
1. Open `http://localhost:5173`.
2. Notice the live metrics counter (Uploads, Verified, Active Students).
3. **Show Example Queries**:
   - Under the search bar, click on any ready-to-use query chip:
     - Click **`Data Structures`** (Beginner)
     - Click **`Operating Systems`** (Intermediate)
     - Click **`DBMS Normalization`** (Intermediate)
     - Click **`Machine Learning`** (Advanced)
4. Show that clicking a query instantly filters matching academic materials.

### Step 2: Instant Document Preview & Multi-Format Viewer
1. Scroll down to **Popular this week** or **Recently added**.
2. Click **Quick Preview** on **Operating Systems Notes**:
   - The document preview modal opens with the actual multi-page PDF loaded into the embedded inline viewer.
   - Demonstrate the Zoom In (+), Zoom Out (-), Reset, and Open in New Tab controls.
3. Click **Quick Preview** on **DBMS Normalization Guide (DOCX)**:
   - Notice how the Word `.docx` file is automatically transformed into clean, formatted HTML with styled tables.
4. Click **Quick Preview** on **Embedded Systems Slides (PPTX)**:
   - Click **Next Slide** and **Previous Slide** to demonstrate interactive presentation slide navigation.
5. Click **Quick Preview** on **Computer Networks Cheatsheet (PNG)**:
   - Demonstrates visual diagram preview.
6. Click **Download** on any material to demonstrate the live download counter incrementing.

### Step 3: Browse by Department & Categories
1. In the top navbar, click **Categories**.
2. Explain how students can filter materials by department (Computer Science, Information Technology, AI & Data Science, Electronics).
3. Click **Computer Science & Engineering**:
   - Shows all verified notes for that department.
   - Click **← Back to all categories** to return to the full department overview.

### Step 4: 1-Click Upload with AI Moderation Screening
1. In the top navbar, click your avatar or click **Upload Material** (`http://localhost:5173/upload`).
2. Show the **"Try Demo Sample Materials"** toolbar at the top of the form:
   - Click **`+ OS Notes (PDF)`** or **`+ ML Lab Manual (PDF)`**.
   - Notice how all fields (Title, Subject, Department, Semester, Category, Description) and the real sample file are instantly attached.
   - Point out the **25-word live counter** ensuring concise, professional summaries.
3. Click **Submit for review**:
   - The file is securely uploaded to the backend.
   - Backend scans file magic bytes, checks for malicious scripts/executables, calculates SHA-256 duplicate hash, and queues it for AI moderation.
   - The user is redirected to **My Uploads** (`/my-uploads`) where they see their document with status `PENDING` or `AI_APPROVED`.

### Step 5: Administrator Portal & Moderation Queue
1. Log in as Administrator:
   - Go to `http://localhost:5173/admin/login` (or `/login`).
   - Email: `admin@campusverse.edu`
   - Password: `Admin@123`
2. In the Admin Dashboard (`/admin`):
   - Show the **Pending Approvals Queue** (`Machine Learning & AI - Complete Practical Lab Manual`).
   - Review the **AI Moderation Card**: Confidence score (e.g. `88%`), detected flags (`CODE_SNIPPETS_DETECTED`), and AI summary.
   - Click **Quick Preview** to inspect the document before approving.
   - Click **Approve Material**: enter an optional moderator note (e.g., *"Approved for Sem 6 syllabus"*).
3. The material is instantly approved and promoted to public visibility across Homepage and Categories!

---

## 6. Expected Behavior & Security Controls

- **Magic Byte Verification**: Files with altered extensions (e.g., `.exe` renamed to `.pdf`) are rejected with `415 Unsupported Media Type`.
- **Duplicate Prevention**: Re-uploading an identical file generates a `409 Conflict: An identical document has already been uploaded`.
- **Word Limit Enforcement**: Descriptions over 25 words trigger a client-side warning and backend `400 Bad Request`.
- **Safe Fallbacks**: If external AI APIs are offline, the system seamlessly uses its built-in rule-based academic moderation heuristics.

---

## 7. Presentation Summary Checklist

- [x] Backend running on `http://localhost:5000` (FastAPI + MongoDB).
- [x] Frontend running on `http://localhost:5173` (Vite + React).
- [x] Realistic study materials seeded with physical files in `uploads/`.
- [x] Multi-format document previews verified (PDF, DOCX, PPTX, PNG).
- [x] 1-Click demo preset toolbar active on Upload page.
- [x] Example query chips active on Homepage and Categories.
- [x] All "Explore" references removed cleanly across frontend and backend.
- [x] `npm run test:demo` passes 100% of test cases.
