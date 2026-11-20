-- ==============================================================================
-- CampusVerse — Complete Supabase Setup (Schema + RLS + Seed Data)
-- Copy and paste this entire script into your Supabase SQL Editor and click "Run"
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. User Profiles Table (Synchronized with auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'moderator', 'admin')),
    department TEXT,
    course TEXT DEFAULT 'Computer Science and Engineering',
    academic_year TEXT DEFAULT '3rd Year',
    batch TEXT DEFAULT 'Batch 2023-2027',
    semester INT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);

-- 3. Automatic User Profile Trigger on Signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    user_name TEXT;
    user_role TEXT;
    user_dept TEXT;
BEGIN
    user_name := COALESCE(
        new.raw_user_meta_data->>'full_name',
        new.raw_user_meta_data->>'name',
        split_part(new.email, '@', 1)
    );
    user_role := COALESCE(new.raw_user_meta_data->>'role', 'student');
    user_dept := new.raw_user_meta_data->>'department';

    IF user_role NOT IN ('student', 'moderator', 'admin') THEN
        user_role := 'student';
    END IF;

    IF new.email = 'admin@campusverse.edu' THEN
        user_role := 'admin';
    END IF;

    INSERT INTO public.profiles (
        id, email, name, full_name, role, department,
        course, academic_year, batch, semester, created_at, updated_at
    ) VALUES (
        new.id,
        new.email,
        user_name,
        user_name,
        user_role,
        user_dept,
        COALESCE(new.raw_user_meta_data->>'course', 'Computer Science and Engineering'),
        COALESCE(new.raw_user_meta_data->>'academicYear', '3rd Year'),
        COALESCE(new.raw_user_meta_data->>'batch', 'Batch 2023-2027'),
        (new.raw_user_meta_data->>'semester')::INT,
        NOW(),
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        name = EXCLUDED.name,
        full_name = EXCLUDED.full_name,
        updated_at = NOW();

    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 4. Study Materials Table
CREATE TABLE IF NOT EXISTS public.study_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    summary TEXT,
    summary_word_count INT DEFAULT 0,
    max_summary_words INT DEFAULT 500,
    processing_status TEXT DEFAULT 'Completed',
    extraction_status TEXT DEFAULT 'Completed',
    page_count INT DEFAULT 1,
    total_page_count INT DEFAULT 1,
    processed_page_count INT DEFAULT 1,
    pages_extracted JSONB DEFAULT '[]'::jsonb,
    pages_ocr JSONB DEFAULT '[]'::jsonb,
    pages_failed JSONB DEFAULT '[]'::jsonb,
    uploader_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    uploader_name TEXT DEFAULT 'Student',
    academic_category TEXT DEFAULT 'Engineering',
    main_category TEXT DEFAULT 'Engineering',
    subcategory TEXT,
    topic TEXT,
    department TEXT DEFAULT 'Engineering',
    course TEXT DEFAULT 'Computer Science and Engineering',
    academic_year TEXT DEFAULT '3rd Year',
    batch TEXT DEFAULT 'Batch 2023-2027',
    semester INT DEFAULT 1,
    subject TEXT DEFAULT 'Engineering',
    category TEXT DEFAULT 'notes',
    file_url TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    storage_provider TEXT DEFAULT 'supabase',
    original_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    extension TEXT NOT NULL,
    size BIGINT DEFAULT 0,
    file_hash TEXT NOT NULL,
    text_hash TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (
        status IN (
            'PENDING', 'AI_APPROVED', 'NEEDS_REVIEW', 'REJECTED',
            'ADMIN_APPROVED', 'ADMIN_REJECTED', 'QUALITY_CHECK_PASSED', 'NEEDS_CORRECTION'
        )
    ),
    ai_review JSONB,
    classification JSONB,
    quality_report JSONB,
    similarity_report JSONB,
    scan_report JSONB,
    has_chapter_summaries BOOLEAN DEFAULT FALSE,
    moderation JSONB,
    duplicate_of UUID REFERENCES public.study_materials(id) ON DELETE SET NULL,
    downloads INT DEFAULT 0,
    rating NUMERIC(3,2) DEFAULT 5.0,
    rating_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_materials_status_created ON public.study_materials(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_materials_dept_sem ON public.study_materials(department, semester, subject);
CREATE INDEX IF NOT EXISTS idx_materials_uploader ON public.study_materials(uploader_id);
CREATE INDEX IF NOT EXISTS idx_materials_file_hash ON public.study_materials(file_hash);
CREATE INDEX IF NOT EXISTS idx_materials_doc_id ON public.study_materials(document_id);

CREATE INDEX IF NOT EXISTS idx_materials_fts ON public.study_materials USING GIN (
    to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(subject, ''))
);

-- 5. Document Chunks (for RAG & Semantic Vector Search with pgvector)
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES public.study_materials(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    page_number INT NOT NULL DEFAULT 1,
    chunk_index INT NOT NULL DEFAULT 0,
    heading TEXT,
    text TEXT NOT NULL,
    embedding vector(768),
    token_count INT DEFAULT 0,
    keywords TEXT[] DEFAULT '{}'::text[],
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_material ON public.document_chunks(material_id);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON public.document_chunks(material_id, page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON public.document_chunks USING hnsw (embedding vector_cosine_ops);

-- 6. Ratings & Reviews
CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES public.study_materials(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    rating NUMERIC(2,1) NOT NULL CHECK (rating >= 1.0 AND rating <= 5.0),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (material_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_material ON public.reviews(material_id);

-- 7. Bookmarks
CREATE TABLE IF NOT EXISTS public.bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES public.study_materials(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, material_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON public.bookmarks(user_id);

-- 8. Download History
CREATE TABLE IF NOT EXISTS public.downloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES public.study_materials(id) ON DELETE CASCADE,
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_downloads_user ON public.downloads(user_id, downloaded_at DESC);

-- 9. Chapter Summaries
CREATE TABLE IF NOT EXISTS public.chapter_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES public.study_materials(id) ON DELETE CASCADE UNIQUE,
    title TEXT NOT NULL,
    chapters JSONB NOT NULL DEFAULT '[]'::jsonb,
    revision_summary TEXT,
    definitions JSONB DEFAULT '[]'::jsonb,
    practice_qa JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Chat Sessions & Messages (RAG Chat with Notes)
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    material_ids TEXT[] NOT NULL DEFAULT '{}'::text[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON public.chat_sessions(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON public.chat_messages(session_id, created_at ASC);

-- 11. Study Buddy Sessions
CREATE TABLE IF NOT EXISTS public.study_buddy_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    file_type TEXT DEFAULT 'PDF',
    file_size TEXT,
    char_count INT DEFAULT 0,
    notes JSONB NOT NULL DEFAULT '{}'::jsonb,
    history JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. Scanning Booth Records
CREATE TABLE IF NOT EXISTS public.scanning_booth_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id TEXT UNIQUE NOT NULL,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    report JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'SCANNED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. Categories Table
CREATE TABLE IF NOT EXISTS public.categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    count INT DEFAULT 0,
    description TEXT,
    subcategories JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. System Settings & AI Benchmarks
CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.ai_benchmark_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    report JSONB NOT NULL
);

-- 15. Admin Audit Logs
CREATE TABLE IF NOT EXISTS public.admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    admin_email TEXT,
    action TEXT NOT NULL,
    target_id TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==============================================================================
-- Row Level Security (RLS) Configuration
-- ==============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.downloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chapter_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_buddy_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scanning_booth_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_benchmark_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.is_staff(user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = user_id AND role IN ('admin', 'moderator')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Profiles Policies
DROP POLICY IF EXISTS "Public profiles are viewable by everyone" ON public.profiles;
CREATE POLICY "Public profiles are viewable by everyone" ON public.profiles
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can insert their own profile" ON public.profiles;
CREATE POLICY "Users can insert their own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id OR public.is_staff(auth.uid()));

-- Study Materials Policies
DROP POLICY IF EXISTS "Approved study materials are publicly viewable" ON public.study_materials;
CREATE POLICY "Approved study materials are publicly viewable" ON public.study_materials
    FOR SELECT USING (
        status IN ('AI_APPROVED', 'ADMIN_APPROVED', 'QUALITY_CHECK_PASSED')
        OR auth.uid() = uploader_id
        OR public.is_staff(auth.uid())
    );

DROP POLICY IF EXISTS "Authenticated users can upload study materials" ON public.study_materials;
CREATE POLICY "Authenticated users can upload study materials" ON public.study_materials
    FOR INSERT WITH CHECK (auth.uid() = uploader_id OR auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Uploaders and staff can update study materials" ON public.study_materials;
CREATE POLICY "Uploaders and staff can update study materials" ON public.study_materials
    FOR UPDATE USING (auth.uid() = uploader_id OR public.is_staff(auth.uid()));

DROP POLICY IF EXISTS "Uploaders and staff can delete study materials" ON public.study_materials;
CREATE POLICY "Uploaders and staff can delete study materials" ON public.study_materials
    FOR DELETE USING (auth.uid() = uploader_id OR public.is_staff(auth.uid()));

-- Document Chunks Policies
DROP POLICY IF EXISTS "Chunks are viewable by readers of the material" ON public.document_chunks;
CREATE POLICY "Chunks are viewable by readers of the material" ON public.document_chunks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.study_materials m
            WHERE m.id = material_id AND (
                m.status IN ('AI_APPROVED', 'ADMIN_APPROVED', 'QUALITY_CHECK_PASSED')
                OR auth.uid() = m.uploader_id
                OR public.is_staff(auth.uid())
            )
        )
    );

DROP POLICY IF EXISTS "Service role and staff can manage chunks" ON public.document_chunks;
CREATE POLICY "Service role and staff can manage chunks" ON public.document_chunks
    FOR ALL USING (auth.uid() IS NOT NULL);

-- Reviews Policies
DROP POLICY IF EXISTS "Reviews viewable by everyone" ON public.reviews;
CREATE POLICY "Reviews viewable by everyone" ON public.reviews
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can rate materials" ON public.reviews;
CREATE POLICY "Users can rate materials" ON public.reviews
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own rating" ON public.reviews;
CREATE POLICY "Users can update their own rating" ON public.reviews
    FOR UPDATE USING (auth.uid() = user_id);

-- Bookmarks Policies
DROP POLICY IF EXISTS "Users can view their own bookmarks" ON public.bookmarks;
CREATE POLICY "Users can view their own bookmarks" ON public.bookmarks
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own bookmarks" ON public.bookmarks;
CREATE POLICY "Users can insert their own bookmarks" ON public.bookmarks
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own bookmarks" ON public.bookmarks;
CREATE POLICY "Users can delete their own bookmarks" ON public.bookmarks
    FOR DELETE USING (auth.uid() = user_id);

-- Downloads Policies
DROP POLICY IF EXISTS "Users can view their own downloads" ON public.downloads;
CREATE POLICY "Users can view their own downloads" ON public.downloads
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can record downloads" ON public.downloads;
CREATE POLICY "Users can record downloads" ON public.downloads
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Chapter Summaries Policies
DROP POLICY IF EXISTS "Chapter summaries viewable by everyone" ON public.chapter_summaries;
CREATE POLICY "Chapter summaries viewable by everyone" ON public.chapter_summaries
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Chapter summaries managed by authenticated users" ON public.chapter_summaries;
CREATE POLICY "Chapter summaries managed by authenticated users" ON public.chapter_summaries
    FOR ALL USING (auth.uid() IS NOT NULL);

-- Chat Sessions & Messages Policies
DROP POLICY IF EXISTS "Users can view their own chat sessions" ON public.chat_sessions;
CREATE POLICY "Users can view their own chat sessions" ON public.chat_sessions
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage their own chat sessions" ON public.chat_sessions;
CREATE POLICY "Users can manage their own chat sessions" ON public.chat_sessions
    FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view messages of their chat sessions" ON public.chat_messages;
CREATE POLICY "Users can view messages of their chat sessions" ON public.chat_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions s
            WHERE s.id = session_id AND s.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can send messages to their chat sessions" ON public.chat_messages;
CREATE POLICY "Users can send messages to their chat sessions" ON public.chat_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.chat_sessions s
            WHERE s.id = session_id AND s.user_id = auth.uid()
        )
    );

-- Study Buddy Sessions Policies
DROP POLICY IF EXISTS "Users manage their study buddy sessions" ON public.study_buddy_sessions;
CREATE POLICY "Users manage their study buddy sessions" ON public.study_buddy_sessions
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- Scanning Booth Policies
DROP POLICY IF EXISTS "Scanning records access" ON public.scanning_booth_records;
CREATE POLICY "Scanning records access" ON public.scanning_booth_records
    FOR ALL USING (auth.uid() = user_id OR public.is_staff(auth.uid()) OR user_id IS NULL);

-- Categories Policies
DROP POLICY IF EXISTS "Categories viewable by all" ON public.categories;
CREATE POLICY "Categories viewable by all" ON public.categories
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Categories manageable by staff" ON public.categories;
CREATE POLICY "Categories manageable by staff" ON public.categories
    FOR ALL USING (public.is_staff(auth.uid()));

-- System settings & Benchmarks Policies
DROP POLICY IF EXISTS "Settings readable by everyone" ON public.system_settings;
CREATE POLICY "Settings readable by everyone" ON public.system_settings
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Settings manageable by staff" ON public.system_settings;
CREATE POLICY "Settings manageable by staff" ON public.system_settings
    FOR ALL USING (public.is_staff(auth.uid()));

DROP POLICY IF EXISTS "Benchmarks readable by all" ON public.ai_benchmark_runs;
CREATE POLICY "Benchmarks readable by all" ON public.ai_benchmark_runs
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Benchmarks insertable by authenticated" ON public.ai_benchmark_runs;
CREATE POLICY "Benchmarks insertable by authenticated" ON public.ai_benchmark_runs
    FOR ALL USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Audit logs manageable by staff" ON public.admin_audit_logs;
CREATE POLICY "Audit logs manageable by staff" ON public.admin_audit_logs
    FOR ALL USING (public.is_staff(auth.uid()));

-- Storage Policies for Bucket 'study-materials'
DROP POLICY IF EXISTS "Allow authenticated users to upload to study-materials" ON storage.objects;
CREATE POLICY "Allow authenticated users to upload to study-materials"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'study-materials');

DROP POLICY IF EXISTS "Allow authenticated and service role to read study-materials" ON storage.objects;
CREATE POLICY "Allow authenticated and service role to read study-materials"
ON storage.objects FOR SELECT
TO authenticated, anon
USING (bucket_id = 'study-materials');

DROP POLICY IF EXISTS "Allow users to delete their own study materials" ON storage.objects;
CREATE POLICY "Allow users to delete their own study materials"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'study-materials' AND (storage.foldername(name))[1] = auth.uid()::text);

-- ==============================================================================
-- 16. Seed Data (Initial Categories and Settings)
-- ==============================================================================

INSERT INTO public.categories (id, name, icon, count, description, subcategories)
VALUES
(
    'computer-applications',
    'Computer Applications',
    'Cpu',
    4,
    'Artificial Intelligence, Machine Learning, Data Science, and Web Development.',
    '[
        {"id": "ai", "name": "Artificial Intelligence", "count": 2, "subtopics": ["Neural Networks", "NLP", "Computer Vision"]},
        {"id": "ml", "name": "Machine Learning", "count": 2, "subtopics": ["Supervised Learning", "Unsupervised Learning", "Model Evaluation"]},
        {"id": "ds", "name": "Data Science", "count": 1, "subtopics": ["Data Wrangling", "Statistical Inference", "Big Data Analytics"]},
        {"id": "web", "name": "Web Development", "count": 1, "subtopics": ["Frontend Frameworks", "REST APIs", "Full Stack Architecture"]}
    ]'::jsonb
),
(
    'engineering',
    'Engineering',
    'Settings',
    8,
    'Computer Science, Civil Engineering, Mechanical Engineering, and Electrical Engineering.',
    '[
        {"id": "eng-cs", "name": "Computer Science", "count": 4, "subtopics": ["Operating Systems", "DBMS", "Data Structures", "Computer Networks"]},
        {"id": "eng-civil", "name": "Civil Engineering", "count": 2, "subtopics": ["Structural Analysis", "RCC Beam Design", "Soil Mechanics"]},
        {"id": "eng-mech", "name": "Mechanical Engineering", "count": 2, "subtopics": ["Thermodynamics", "Fluid Mechanics", "Machine Design"]},
        {"id": "eng-eee", "name": "Electrical Engineering", "count": 2, "subtopics": ["Power Systems", "Electrical Machines", "Circuit Theory"]}
    ]'::jsonb
),
(
    'medical-sciences',
    'Medical Sciences',
    'Stethoscope',
    6,
    'General Medicine, Anatomy, Physiology, and Pharmacology clinical study notes.',
    '[
        {"id": "med-gen", "name": "General Medicine", "count": 2, "subtopics": ["Clinical Diagnosis", "Vital Signs Assessment", "Internal Medicine"]},
        {"id": "med-anat", "name": "Anatomy", "count": 1, "subtopics": ["Gross Anatomy", "Neuroanatomy", "Histology"]},
        {"id": "med-phys", "name": "Physiology", "count": 1, "subtopics": ["Cardiovascular System", "Respiratory Physiology", "Renal System"]},
        {"id": "med-pharm", "name": "Pharmacology", "count": 1, "subtopics": ["Pharmacokinetics", "Antihypertensives", "Antibiotics"]}
    ]'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    icon = EXCLUDED.icon,
    count = EXCLUDED.count,
    description = EXCLUDED.description,
    subcategories = EXCLUDED.subcategories;

INSERT INTO public.system_settings (key, value, updated_at)
VALUES
(
    'scanning_booth',
    '{
        "ocrMinConfidence": 0.70,
        "autoDeskew": true,
        "adaptiveBinarization": true,
        "maxPagesPerScan": 50,
        "supportedFormats": ["pdf", "png", "jpg", "jpeg", "webp"]
    }'::jsonb,
    NOW()
),
(
    'academic_validation',
    '{
        "minWordCount": 50,
        "maxWordCount": 500,
        "spamThreshold": 0.85,
        "relevanceThreshold": 0.75,
        "autoApproveConfidence": 0.90
    }'::jsonb,
    NOW()
)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();
