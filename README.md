# CampusVerse — Study Material Sharing, Previews & AI Moderation

CampusVerse is an academic material-sharing platform built with a **React + Vite + Tailwind CSS** frontend and a high-performance **Python FastAPI** backend powered by **MongoDB**, **Cloud/Local File Storage**, and **AI-Powered Content Screening**.

---

## 🚀 Quick Start Guide (How to Run)

To run the full stack locally, open **two terminal tabs** in VS Code:

### Terminal 1: FastAPI Backend

```powershell
# 1. Navigate to the backend directory
cd backend

# 2. (Optional if already installed) Install Python dependencies
pip install -r requirements.txt

# 3. Start the FastAPI server (runs on http://localhost:5000)
uvicorn main:app --reload --port 5000
```
> **FastAPI Interactive Docs**: View and test APIs at [http://localhost:5000/docs](http://localhost:5000/docs)  
> **MongoDB Status**: Local MongoDB server is supported out-of-the-box (`mongodb://localhost:27017/campusverse`), or configure MongoDB Atlas in `backend/.env`.

---

### Terminal 2: React Frontend

```powershell
# In the root workspace directory:
npm run dev
```
> **Frontend App**: Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 👑 How to Create an Admin / Moderator

1. Register an account through the frontend at [http://localhost:5173/register](http://localhost:5173/register) (e.g. `admin@campusverse.edu`).
2. In your backend terminal, promote your account to `admin` or `moderator`:
```powershell
cd backend
python -m app.scripts.set_role admin@campusverse.edu admin
```
3. Log in to access the **Admin Console** at [http://localhost:5173/admin](http://localhost:5173/admin).

---

## 🌟 Key Features Implemented

1. **Academic File Upload**:
   - Supports **PDF**, **PPT/PPTX**, **DOC/DOCX**, and **Images (PNG, JPG, WEBP)**.
   - **Mandatory Description with Live 25-Word Counter**: Strictly prevents submissions with empty descriptions or descriptions exceeding 25 words.
   - Validates file extensions, size limits (up to 25MB), and binary magic signatures.
   - Computes SHA-256 hashes to block duplicate uploads.

2. **Study Material Previews & Downloads**:
   - Every card has instant **Preview** and **Download** buttons.
   - Opens an interactive **Preview Modal** (`MaterialPreviewModal`) without page reload:
     - **PDFs**: Inline PDF viewer with Zoom In/Out, Reset, Fullscreen mode, and New Tab opening.
     - **DOC/DOCX**: Formatted sanitized HTML viewer.
     - **PPT/PPTX**: Slide-by-slide text viewer with Next/Prev navigation.
     - **Images**: High-resolution zoomable image viewer.
     - **Unsupported Formats**: Fallback card with document details and direct download.
   - Secure authenticated downloads via cloud signed URLs or streamed response.

3. **MongoDB Database**:
   - Stores users, material metadata, file references, review scores, downloads, bookmarks, and ratings.
   - Indexes on search queries, statuses, departments, semesters, and uploader IDs.
   - Passwords securely hashed using `bcrypt` (12 rounds).
   - Never exposes password hashes or internal storage keys.

4. **Free Cloud Storage Providers**:
   - **Local Storage (`./uploads`)**: Instant zero-config local storage for development.
   - **Supabase Storage**: Private bucket support with time-limited signed URLs (`STORAGE_PROVIDER=supabase`).
   - **Cloudinary**: Authenticated media asset management (`STORAGE_PROVIDER=cloudinary`).

5. **AI-Powered Material Moderation**:
   - Extracts readable document text using `pypdf`, `python-docx`, and `python-pptx`.
   - **Google Gemini API** (`gemini-1.5-flash`) analyzes academic relevance, subject match, spam, and suspicious URLs.
   - **Rule-Based Fallback**: Deterministic heuristic checks run automatically if no API key is provided or quota is exceeded.
   - Workflow statuses:
     - `PENDING`
     - `AI_APPROVED`
     - `NEEDS_REVIEW`
     - `REJECTED`
     - `ADMIN_APPROVED` (Public listing default)
     - `ADMIN_REJECTED`

6. **Moderator & Admin Dashboard (`/admin`)**:
   - Tabs for **Pending Uploads**, **Flagged Content & Duplicates**, **Moderation History**, and **Users Directory**.
   - Inspect AI explanation, confidence meter, and flags before deciding.
   - Single-click **Approve & Publish** or **Reject with Reason**.

7. **Student Dashboard & Tracking (`/my-uploads`)**:
   - Live status badges (`Published Live`, `Queued for Staff`, `Manual Review Needed`, etc.).
   - Displays AI feedback reasons and moderator notes.

---

## 🧠 Advanced AI-Powered Features (Faculty Requirements)

CampusVerse includes 5 enterprise-grade AI features designed for automated academic intelligence, quality assurance, and semantic retrieval:

### 1. Automatic Branch & Subject Classification
- **Instant Pre-Upload & Post-Upload Classification**: When notes are selected or uploaded, document text is extracted and analyzed against university departmental taxonomy profiles.
- **Confidence Scores & Topics**: Predicts academic branch (e.g. `Computer Science & Engineering`), suggested subject (e.g. `Operating Systems`), and detected subtopics with numerical confidence.
- **Honest Fallback**: If a document lacks sufficient academic content or is ambiguous, it returns `"Unable to classify"` instead of hallucinating subjects.
- **User & Admin Correction**: Students and moderators can adjust classifications anytime using the interactive `ClassificationCorrectionModal`.
- **Endpoints**: `POST /api/classifier/predict`, `PATCH /api/classifier/materials/{id}/classification`.

### 2. AI Quality Analysis Before Admin Approval
- **5-Dimension Inspection**:
  1. **Blank Pages**: Identifies pages without meaningful text; checks OCR status before flagging.
  2. **Duplicate Pages**: Normalizes text and compares MD5 page hashes to identify duplicate or repeated pages.
  3. **PDF Readability & Corruption**: Detects corrupted PDFs, missing text layers, and scanned documents requiring OCR.
  4. **Subject Relevance**: Quantifies semantic alignment between document text and selected/predicted subject with clear explanations.
  5. **Completeness Assessment**: Flags unusually short documents or unreadable page subsets without making unsupported claims.
- **Admin Approval Workflow**: Statuses include `Pending Review`, `Quality Check Passed`, `Needs Correction`, `Approved`, and `Rejected`. Admin retains final authority with the `QualityReportModal`.
- **Endpoint**: `GET /api/admin/materials/{id}/quality-report`.

### 3. Automatic Chapter-Wise Summaries & Key Concepts
- **Boundary Detection**: Identifies chapter, unit, and module headings (e.g., `Chapter 1`, `Unit II`, `Module 3`). If headings are absent, automatically partitions into logical semantic sections.
- **Structured Insights**: For each chapter, extracts:
  - Concise bullet-point summaries
  - Key technical concepts
  - Important definitions (`term` -> `definition`)
  - Mathematical formulas and numerical examples
- **Document Details Integration**: Displayed inside `ChapterSummarySection` on the material details page with single-click regeneration.
- **Endpoints**: `GET /api/materials/{id}/chapter-summaries`, `POST /api/materials/{id}/chapter-summaries/regenerate`.

### 4. AI Semantic Search, Duplicate Detection & Plagiarism Check
- **Natural-Language Semantic Search (`/search`)**: Users can search using conceptual questions (e.g., *"Explain CPU scheduling turnaround time"*, *"Where is database normalization explained?"*).
- **Dense Embeddings & Cosine Similarity**: 128-dimensional dense vector embeddings generated with pure NumPy (and optional Gemini embeddings). Vector index stored in `document_chunks` collection with page anchors.
- **Exact Duplicate Detection**: SHA-256 binary hash validation blocks identical file re-uploads.
- **Plagiarism & Similarity Analysis**: Compares uploaded document chunks against authorized existing documents, reporting percentage match, similar passages, and matching document citations in `SimilarityReportModal`.
- **Endpoints**: `GET /api/search/semantic`, `GET /api/similarity/materials/{id}/report`, `POST /api/similarity/materials/{id}/check`.

### 5. Chat With Notes (RAG Architecture) (`/chat`)
- **Multi-Document Context**: Students can select one or more approved study materials as their dedicated conversational context.
- **Strictly Grounded RAG Answers**: Retrieves top cosine-similarity chunks and synthesizes clear answers cited with source document title and exact page numbers.
- **Honest Missing-Information Handling**: When notes lack information on a query, the assistant explicitly states the answer could not be found in the uploaded notes.
- **Conversational History**: Multi-turn sessions persisted in `chat_sessions` and `chat_messages` collections in MongoDB.
- **Endpoints**: `GET /api/chat/materials`, `POST /api/chat/sessions`, `POST /api/chat/sessions/{id}/message`.
