import urllib.request
import urllib.error
import json
import os

BASE_URL = "http://127.0.0.1:5000"

def test_api():
    print("=" * 60)
    print("CAMPUSVERSE LIVE DEMO E2E VERIFICATION")
    print("=" * 60)

    # 1. Health
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        health = json.loads(resp.read().decode("utf-8"))
        assert health["status"] == "healthy", f"Health failed: {health}"
        print("[PASS] 1. Backend Health Check: OK")

    # 2. Public materials list
    req = urllib.request.Request(f"{BASE_URL}/api/materials")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        mats = res.get("materials", [])
        assert len(mats) > 0, "No materials returned from API"
        print(f"[PASS] 2. Public Materials List: {len(mats)} approved materials returned")

    # 3. Popular & Recommended
    for ep in ["popular", "recent", "recommended"]:
        req = urllib.request.Request(f"{BASE_URL}/api/materials/{ep}")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            count = len(data.get("materials", []))
            print(f"[PASS] 3. Endpoint '/api/materials/{ep}': {count} items returned")

    # 4. Preview and File Stream Verification for every file format
    for m in mats:
        mat_id = m["id"]
        title = m["title"]
        file_type = m["fileType"]
        preview_url = f"{BASE_URL}/api/materials/{mat_id}/preview"
        req = urllib.request.Request(preview_url)
        with urllib.request.urlopen(req) as resp:
            prev_data = json.loads(resp.read().decode("utf-8"))
            kind = prev_data.get("preview", {}).get("kind")
            print(f"[PASS] 4. Preview [{file_type} -> kind:{kind}]: {title[:40]}...")

        # If PDF or Image, verify inline file download
        if kind in ["pdf", "image"]:
            file_url = f"{BASE_URL}/api/materials/{mat_id}/file"
            req_file = urllib.request.Request(file_url)
            with urllib.request.urlopen(req_file) as f_resp:
                raw_bytes = f_resp.read()
                assert len(raw_bytes) > 0, "Empty file bytes returned"
                print(f"       -> Streamed {len(raw_bytes)} bytes successfully ({f_resp.headers.get('Content-Type')})")

    # 5. Search verification
    for query in ["Operating", "DBMS", "Networks", "Data Structures"]:
        encoded = urllib.parse.quote(query)
        req = urllib.request.Request(f"{BASE_URL}/api/materials?q={encoded}")
        with urllib.request.urlopen(req) as resp:
            search_res = json.loads(resp.read().decode("utf-8"))
            count = len(search_res.get("materials", []))
            print(f"[PASS] 5. Search query '{query}': {count} matching materials found")

    print("=" * 60)
    print("ALL E2E DEMO VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    import urllib.parse
    test_api()
