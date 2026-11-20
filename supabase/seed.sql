-- ==============================================================================
-- CampusVerse Supabase Seed Data
-- ==============================================================================

-- 1. Ensure Categories Table Exists
CREATE TABLE IF NOT EXISTS public.categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    count INT DEFAULT 0,
    description TEXT,
    subcategories JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Insert Initial System Categories
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

-- 3. Ensure System Settings Table Exists
CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. System Settings (Scanning Booth & Academic Validation)
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
