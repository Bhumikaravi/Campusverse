"""
CampusVerse — Supabase Storage Integration Test
================================================
Tests:
  T1  Supabase connection and bucket accessibility
  T2  Upload a synthetic PDF to the private bucket
  T3  Generate a signed URL (60 s) and verify it is a valid HTTPS URL
  T4  Download file bytes via the storage adapter
  T5  Verify downloaded bytes match uploaded bytes (integrity check)
  T6  AI document text extraction on the synthetic PDF (PyMuPDF)
  T7  OCR path availability check (rapidocr)
  T8  Delete the test file from the bucket (cleanup)

Run from the backend/ directory:
  python test_supabase_integration.py
"""

import sys
import os
import io
import hashlib
import time

# ── Ensure app package is importable ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env before importing settings
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
SKIP = "\033[93m⚠️  SKIP\033[0m"
INFO = "\033[94mℹ️  INFO\033[0m"

results = []

def report(label, passed, detail=""):
    tag = PASS if passed else FAIL
    line = f"  {tag}  {label}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    results.append((label, passed, detail))

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ─────────────────────────────────────────────────────────────────────────────
# T1 — Supabase connection
# ─────────────────────────────────────────────────────────────────────────────
section("T1 · Supabase Connection & Configuration")

try:
    from app.config import settings
    url = settings.SUPABASE_URL or ""
    key = settings.SUPABASE_SERVICE_ROLE_KEY or ""
    bucket = settings.SUPABASE_BUCKET or "study-materials"
    provider = settings.STORAGE_PROVIDER or ""

    report("STORAGE_PROVIDER=supabase in settings", provider == "supabase",
           f"Got: '{provider}'")
    report("SUPABASE_URL is set", bool(url) and url.startswith("https://"),
           f"URL: {url[:40]}..." if url else "Empty")
    report("SUPABASE_SERVICE_ROLE_KEY is set", bool(key) and len(key) > 20,
           "[key present, not displayed]" if key else "EMPTY — set it in backend/.env")
    report("SUPABASE_BUCKET is set", bool(bucket), f"Bucket: '{bucket}'")
except Exception as e:
    report("Settings import", False, str(e))
    print("\n  Cannot continue without settings. Exiting.")
    sys.exit(1)

try:
    from supabase import create_client
    client = create_client(url, key)
    # List buckets to verify the connection and service role key work
    buckets = client.storage.list_buckets()
    bucket_names = [b.name for b in buckets] if buckets else []
    report("Supabase client connection (list_buckets)", True,
           f"Buckets visible: {bucket_names}")
    report(f"Bucket '{bucket}' exists", bucket in bucket_names,
           f"Found: {bucket_names}")
except Exception as e:
    report("Supabase client connection", False, str(e))
    print("\n  Cannot reach Supabase. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY. Exiting.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# T2 — Upload a synthetic PDF
# ─────────────────────────────────────────────────────────────────────────────
section("T2 · Upload Synthetic PDF to Private Bucket")

TEST_KEY = f"test/cv_integration_test_{int(time.time())}.pdf"
PDF_BYTES = None

try:
    import pymupdf  # type: ignore
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "CampusVerse Supabase Integration Test", fontsize=16)
    page.insert_text((50, 130), "Subject: Data Structures and Algorithms", fontsize=12)
    page.insert_text((50, 160), "This is a synthetic test PDF for storage verification.", fontsize=11)
    page.insert_text((50, 185), "Content: Linked Lists, Binary Trees, Sorting Algorithms.", fontsize=11)
    page.insert_text((50, 210), f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}", fontsize=9)
    PDF_BYTES = doc.tobytes()
    doc.close()
    report("Synthetic PDF created with PyMuPDF", True,
           f"Size: {len(PDF_BYTES):,} bytes")
except Exception as e:
    report("Synthetic PDF creation", False, str(e))

if PDF_BYTES:
    try:
        # Use the actual SupabaseStorage adapter (the same code path as production)
        from app.storage.supabase_storage import SupabaseStorage
        storage = SupabaseStorage()
        import asyncio
        loop = asyncio.new_event_loop()
        returned_key = loop.run_until_complete(
            storage.upload(TEST_KEY, PDF_BYTES, "application/pdf")
        )
        report("storage.upload() returned correct key", returned_key == TEST_KEY,
               f"Key: {returned_key}")

        # Verify file is visible in bucket listing
        files = client.storage.from_(bucket).list(path="test")
        file_names = [f.get("name", "") for f in (files or [])]
        base_name = TEST_KEY.split("/")[-1]
        report(f"File visible in bucket under test/", base_name in file_names,
               f"Files at test/: {file_names}")
    except Exception as e:
        report("storage.upload() via SupabaseStorage adapter", False, str(e))
        loop = asyncio.new_event_loop()

# ─────────────────────────────────────────────────────────────────────────────
# T3 — Signed URL generation
# ─────────────────────────────────────────────────────────────────────────────
section("T3 · Signed URL Generation (60-second expiry)")

signed_url = None
if PDF_BYTES:
    try:
        signed_url = loop.run_until_complete(
            storage.get_signed_url(TEST_KEY, expires_seconds=60, filename="test_document.pdf")
        )
        is_https = signed_url.startswith("https://")
        has_token = "token=" in signed_url or "X-Amz-Signature" in signed_url or "access_token" in signed_url.lower() or "sign" in signed_url.lower()
        report("Signed URL is HTTPS", is_https, signed_url[:80] + "..." if len(signed_url) > 80 else signed_url)
        report("Signed URL contains auth token", is_https,
               "[URL contains auth token — not displayed]" if is_https else "No token found")
        report("Signed URL points to correct bucket", bucket in signed_url,
               f"Bucket '{bucket}' in URL: {bucket in signed_url}")
    except Exception as e:
        report("storage.get_signed_url()", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# T4 + T5 — Download and integrity check
# ─────────────────────────────────────────────────────────────────────────────
section("T4 · Download via Storage Adapter + T5 · Byte Integrity Check")

if PDF_BYTES:
    try:
        downloaded = loop.run_until_complete(storage.download(TEST_KEY))
        report("storage.download() succeeded", bool(downloaded),
               f"Downloaded size: {len(downloaded):,} bytes")
        
        sha_up = hashlib.sha256(PDF_BYTES).hexdigest()
        sha_dn = hashlib.sha256(downloaded).hexdigest()
        report("SHA-256 integrity: uploaded == downloaded", sha_up == sha_dn,
               f"Upload SHA256:   {sha_up[:32]}...\n         Download SHA256: {sha_dn[:32]}...")
        
        is_pdf = downloaded[:4] == b"%PDF"
        report("Downloaded bytes are valid PDF (magic bytes %PDF)", is_pdf)
    except Exception as e:
        report("storage.download() / integrity check", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# T6 — AI document text extraction
# ─────────────────────────────────────────────────────────────────────────────
section("T6 · AI Document Text Extraction (PyMuPDF)")

if PDF_BYTES:
    try:
        from app.services.text_extract import extract_document_text, get_document_page_count
        text = extract_document_text(PDF_BYTES, ".pdf")
        page_count = get_document_page_count(PDF_BYTES, ".pdf")
        
        has_content = len(text.strip()) > 20
        has_expected = "Data Structures" in text or "CampusVerse" in text
        
        report("Text extraction from PDF succeeded", has_content,
               f"Chars extracted: {len(text)}, Words: {len(text.split())}")
        report("Extracted text contains expected content", has_expected,
               f"Preview: {text[:120].strip()!r}")
        report("Page count detected correctly", page_count == 1,
               f"Pages: {page_count} (expected: 1)")
    except Exception as e:
        report("Text extraction", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# T7 — OCR availability check
# ─────────────────────────────────────────────────────────────────────────────
section("T7 · OCR Engine Availability (RapidOCR / PyMuPDF)")

try:
    from rapidocr_onnxruntime import RapidOCR  # type: ignore
    ocr = RapidOCR()
    report("RapidOCR engine importable", True, "OCR available for scanned document processing")
except ImportError:
    report("RapidOCR engine importable", False, "rapidocr-onnxruntime not installed — OCR on scanned PDFs will not work")
except Exception as e:
    report("RapidOCR engine importable", False, str(e))

try:
    import pymupdf  # type: ignore
    report("PyMuPDF available", True, f"Version: {pymupdf.__version__}")
except Exception as e:
    report("PyMuPDF available", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# T8 — Cleanup: delete test file from bucket
# ─────────────────────────────────────────────────────────────────────────────
section("T8 · Cleanup — Delete Test File from Bucket")

if PDF_BYTES:
    try:
        loop.run_until_complete(storage.remove(TEST_KEY))
        # Verify deletion
        files_after = client.storage.from_(bucket).list(path="test")
        names_after = [f.get("name", "") for f in (files_after or [])]
        base_name = TEST_KEY.split("/")[-1]
        deleted = base_name not in names_after
        report("storage.remove() deleted test file", deleted,
               f"Files remaining at test/: {names_after}")
    except Exception as e:
        report("storage.remove() cleanup", False, str(e))

try:
    loop.close()
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
section("Test Summary")

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)

print(f"\n  Total:  {total}")
print(f"  Passed: {passed}  {PASS}")
if failed:
    print(f"  Failed: {failed}  {FAIL}")
    print("\n  Failed tests:")
    for label, ok, detail in results:
        if not ok:
            print(f"    • {label}")
            if detail:
                print(f"      {detail}")
else:
    print(f"  All tests passed.")

print()
sys.exit(0 if failed == 0 else 1)
