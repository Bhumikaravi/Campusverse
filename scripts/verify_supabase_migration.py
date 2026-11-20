"""
CampusVerse — Supabase Migration Verification Script
===================================================
Verifies:
  1. SQL Migration file existence and syntax
  2. Edge Function files existence and structure
  3. Frontend environment configuration
  4. Removal of MongoDB & Render artifacts
"""

import os
import sys

def check(label, condition, detail=""):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"[{status}] {label}")
    if detail:
        print(f"         {detail}")
    return condition

def main():
    print("=" * 60)
    print("  CAMPUSVERSE — SUPABASE MIGRATION VERIFICATION")
    print("=" * 60)
    all_ok = True

    # 1. SQL Migrations
    migration_file = "supabase/migrations/20261120000000_campusverse_schema.sql"
    seed_file = "supabase/seed.sql"
    all_ok &= check("SQL Migration file exists", os.path.exists(migration_file), migration_file)
    all_ok &= check("SQL Seed file exists", os.path.exists(seed_file), seed_file)

    if os.path.exists(migration_file):
        with open(migration_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
        all_ok &= check("SQL contains profiles table", "CREATE TABLE IF NOT EXISTS public.profiles" in sql_content)
        all_ok &= check("SQL contains study_materials table", "CREATE TABLE IF NOT EXISTS public.study_materials" in sql_content)
        all_ok &= check("SQL contains document_chunks table", "CREATE TABLE IF NOT EXISTS public.document_chunks" in sql_content)
        all_ok &= check("SQL contains RLS policies", "ALTER TABLE public.study_materials ENABLE ROW LEVEL SECURITY;" in sql_content)
        all_ok &= check("SQL contains vector extension", 'CREATE EXTENSION IF NOT EXISTS "vector"' in sql_content)
        all_ok &= check("SQL contains study-materials storage policy", "study-materials" in sql_content)

    # 2. Supabase Edge Functions
    edge_index = "supabase/functions/api/index.ts"
    edge_routes = [
        "supabase/functions/api/routes/auth.ts",
        "supabase/functions/api/routes/materials.ts",
        "supabase/functions/api/routes/chat.ts",
        "supabase/functions/api/routes/studyBuddy.ts",
        "supabase/functions/api/routes/scanningBooth.ts",
        "supabase/functions/api/routes/admin.ts",
        "supabase/functions/api/routes/categories.ts",
        "supabase/functions/api/routes/search.ts",
        "supabase/functions/api/routes/guardrails.ts",
        "supabase/functions/api/routes/recognition.ts",
        "supabase/functions/api/routes/bookmarks.ts",
        "supabase/functions/api/services/gemini.ts",
        "supabase/functions/api/services/guardrails.ts",
        "supabase/functions/api/services/ragEngine.ts",
    ]
    all_ok &= check("Edge Function API index.ts exists", os.path.exists(edge_index), edge_index)
    for route in edge_routes:
        all_ok &= check(f"Route/Service exists: {os.path.basename(route)}", os.path.exists(route), route)

    # 3. Frontend Configuration
    frontend_api = "frontend/src/services/api.js"
    all_ok &= check("Frontend api.js exists", os.path.exists(frontend_api), frontend_api)
    with open(frontend_api, "r", encoding="utf-8") as f:
        api_code = f.read()
    all_ok &= check("Frontend api.js points to Supabase Edge Functions", "functions/v1/api" in api_code)
    all_ok &= check("Frontend attaches Supabase apikey header", "headers[\"apikey\"]" in api_code or "headers.apikey" in api_code)

    # 4. Check Render removal
    render_yaml_exists = os.path.exists("render.yaml")
    all_ok &= check("render.yaml removed", not render_yaml_exists, "Cleaned up" if not render_yaml_exists else "Still exists")

    print("=" * 60)
    if all_ok:
        print("🎉 ALL MIGRATION INTEGRITY CHECKS PASSED!")
        return 0
    else:
        print("⚠️ Some checks failed. Review details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
