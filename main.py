import sys
import importlib.util
from pathlib import Path

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Explicitly load backend/main.py to prevent circular self-import of root main.py
backend_main_path = backend_dir / "main.py"
spec = importlib.util.spec_from_file_location("backend_main", backend_main_path)
backend_main = importlib.util.module_from_spec(spec)
sys.modules["backend_main"] = backend_main
spec.loader.exec_module(backend_main)

app = backend_main.app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    print("=" * 60)
    print("  Starting CampusVerse FastAPI Backend on http://localhost:5000")
    print("  API Docs: http://localhost:5000/docs")
    print("=" * 60)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        reload_excludes=["*.pyc", "*node_modules*", "*.log", "uploads/*"]
    )

