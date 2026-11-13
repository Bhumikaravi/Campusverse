# CampusVerse FastAPI Backend

Python 3.10+ / 3.14+ FastAPI backend with async MongoDB (Motor), JWT authentication, cloud & local file storage, and AI-assisted moderation.

---

## 1. Quick Setup & Run

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Configure Environment
Copy `.env.example` to `.env` (it is already pre-configured for local development with your running MongoDB server):
```powershell
copy .env.example .env
```

### Step 3: Start the Backend Server
```powershell
uvicorn main:app --reload --port 5000
```
- API Base: `http://localhost:5000/api`
- Interactive Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

---

## 2. Make an Admin or Moderator

1. Register an account on the frontend or via API:
```bash
POST /api/auth/register
{
  "name": "Bhumika Ravi",
  "email": "bhumika@campusverse.edu",
  "password": "Password123"
}
```

2. Run the role CLI command in your backend directory:
```powershell
python -m app.scripts.set_role bhumika@campusverse.edu admin
# Or for a moderator:
python -m app.scripts.set_role teacher@campusverse.edu moderator
```

---

## 3. Free-Tier Cloud Storage Evaluation

| Provider | Storage | Bandwidth | File Size Limit | Expiration Policy | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Local Storage (`./uploads`)** | Disk space | Unlimited local | Configurable (25MB) | Never expires | **Default for local development & zero-setup testing** |
| **Supabase Storage** | 1 GB Free | 2-5 GB / month | 50 MB / file | Pauses after 7-14 days inactivity | **Best for academic PDFs & Office documents (Private buckets + 60s signed URLs)** |
| **Cloudinary** | 25 Credits (~25GB) | ~25 GB / month | 10 MB for non-image raw files | Never expires | Excellent for images, but strict limits on raw academic files |

To enable **Supabase**:
1. Create a project at [supabase.com](https://supabase.com).
2. Create a private bucket named `study-materials`.
3. In `backend/.env`:
   ```env
   STORAGE_PROVIDER=supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   SUPABASE_BUCKET=study-materials
   ```

---

## 4. AI-Powered Moderation Architecture

```
Upload Document
      ↓
File Validation & Security Check (Signatures, size, macros, zip bomb check)
      ↓
SHA-256 Binary Duplicate Check (Re-uploads rejected with 409 Conflict)
      ↓
Store in Cloud/Local Storage & Save MongoDB Record (status: PENDING)
      ↓
Background Async Pipeline:
  1. Extract Text (pypdf, python-docx, python-pptx)
  2. Rule-Based Pre-check (Spam regex, link analyzer, keyword overlap)
  3. Google Gemini 1.5 Flash API (Isolated untrusted user prompt)
  4. Code-Determined Verdict:
     → AI_APPROVED | NEEDS_REVIEW | REJECTED
      ↓
Moderator Dashboard:
  Approve (ADMIN_APPROVED) → Live in public listings
  Reject with reason (ADMIN_REJECTED)
```

---

## 5. REST API Endpoints

### Authentication
- `POST /api/auth/register` — Create student account.
- `POST /api/auth/login` — Sign in (returns JWT token and sets `cv_token` cookie).
- `POST /api/auth/logout` — Sign out (clears cookie).
- `GET /api/auth/me` — Current authenticated user profile.

### Study Materials
- `POST /api/materials` — Multipart upload (`file`, `title`, `description` [1-25 words], `department`, `semester`, `subject`).
- `GET /api/materials` — Search, filter (`department`, `semester`, `subject`, `category`), and paginate approved materials.
- `GET /api/materials/mine` — Materials uploaded by current user with AI moderation status and reasons.
- `GET /api/materials/{id}` — Material details.
- `GET /api/materials/{id}/preview` — Detailed preview descriptor (PDF, image, DOCX HTML, PPTX slides, or unsupported).
- `GET /api/materials/{id}/file` — Inline binary stream for PDFs and images.
- `GET /api/materials/{id}/download` — Redirects to signed cloud URL or streams download.
- `PUT /api/materials/{id}` — Update material metadata.
- `DELETE /api/materials/{id}` — Remove material and cloud storage binary.

### Moderation (Staff Only)
- `GET /api/admin/materials/pending` — Queue of materials awaiting moderator approval.
- `GET /api/admin/materials/flagged` — Content flagged by AI or suspected duplicates.
- `GET /api/admin/materials` — Full material history with filter parameters.
- `GET /api/admin/materials/{id}` — Complete review dossier.
- `PATCH /api/admin/materials/{id}/approve` — Approve and publish live.
- `PATCH /api/admin/materials/{id}/reject` — Reject with required feedback message.
- `GET /api/admin/stats` — Platform counts (materials, users, downloads, pending queue).
- `GET /api/admin/users` — Directory of registered accounts.
