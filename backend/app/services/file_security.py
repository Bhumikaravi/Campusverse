import re
import hashlib
import zipfile
import io
from typing import Tuple, Dict, Any
from fastapi import HTTPException, status
from app.config import settings

ALLOWED_EXTENSIONS: Dict[str, Dict[str, Any]] = {
    ".pdf": {
        "mime": "application/pdf",
        "kind": "pdf",
        "magic": [b"%PDF"],
    },
    ".png": {
        "mime": "image/png",
        "kind": "image",
        "magic": [b"\x89PNG\r\n\x1a\n"],
    },
    ".jpg": {
        "mime": "image/jpeg",
        "kind": "image",
        "magic": [b"\xff\xd8\xff"],
    },
    ".jpeg": {
        "mime": "image/jpeg",
        "kind": "image",
        "magic": [b"\xff\xd8\xff"],
    },
    ".webp": {
        "mime": "image/webp",
        "kind": "image",
        "magic": [b"RIFF"],
    },
    ".docx": {
        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "kind": "docx",
        "magic": [b"PK\x03\x04"],
    },
    ".pptx": {
        "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "kind": "pptx",
        "magic": [b"PK\x03\x04"],
    },
    ".doc": {
        "mime": "application/msword",
        "kind": "doc",
        "magic": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"PK\x03\x04", b"{\\rtf"],
    },
    ".ppt": {
        "mime": "application/vnd.ms-powerpoint",
        "kind": "ppt",
        "magic": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"PK\x03\x04"],
    },
    ".txt": {
        "mime": "text/plain",
        "kind": "text",
        "magic": [],
    },
    ".md": {
        "mime": "text/markdown",
        "kind": "text",
        "magic": [],
    },
}

def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sanitize_filename(filename: str) -> str:
    clean = re.sub(r"[^\w.\- ]", "_", filename)
    clean = re.sub(r"\.{2,}", ".", clean).strip(" ._")
    if len(clean) > 100:
        parts = clean.rsplit(".", 1)
        ext = f".{parts[1]}" if len(parts) > 1 else ""
        clean = parts[0][: (100 - len(ext))] + ext
    return clean or "document.bin"

def scan_file_security(buffer: bytes, ext: str, kind: str):
    # 1. Reject Windows MZ or Linux ELF executable headers
    if buffer.startswith(b"MZ") or buffer.startswith(b"\x7fELF"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Executable files or binary payloads are strictly prohibited."
        )

    # 2. PDF active script / embedded executable checks
    if kind == "pdf":
        sample = buffer[:200_000] + buffer[-200_000:] if len(buffer) > 400_000 else buffer
        # Block only explicit external launch actions targeting system executables or shell binaries.
        # Harmless PDF dictionaries (like /EmbeddedFiles for fonts or innocent JS tags) are permitted.
        if re.search(rb"/Launch\s*<<[^>]*\.(?:exe|bat|cmd|vbs|ps1|sh)", sample, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF contains active launch macros targeting external executables, which is prohibited."
            )

    # 3. Zip file safety for OpenXML (.docx, .pptx)
    if ext in [".docx", ".pptx"]:
        try:
            with zipfile.ZipFile(io.BytesIO(buffer)) as zf:
                total_uncompressed = 0
                for info in zf.infolist():
                    # Check for dangerous embedded files or macro binaries
                    name_lower = info.filename.lower()
                    if name_lower.endswith(".exe") or name_lower.endswith(".bat") or "vbaproject.bin" in name_lower:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Office document contains macros or executable payloads which are not permitted."
                        )
                    total_uncompressed += info.file_size
                    
                # Zip bomb prevention: compression ratio check
                if len(buffer) > 0 and (total_uncompressed / len(buffer)) > 100:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File compression ratio is suspiciously high (potential zip bomb)."
                    )
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted Office document file."
            )

def validate_and_scan_file(buffer: bytes, original_filename: str) -> Tuple[str, str, str]:
    """
    Validates file extension, size, magic bytes signature, and security payload.
    Returns: (normalized_extension, mime_type, kind)
    """
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(buffer) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    if len(buffer) < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty or corrupted."
        )

    dot_idx = original_filename.rfind(".")
    if dot_idx == -1:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File has no extension. Please upload a PDF, Word, PowerPoint, or Image file."
        )

    ext = original_filename[dot_idx:].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extension '{ext}' is not supported. Supported: .pdf, .docx, .doc, .pptx, .ppt, .png, .jpg, .jpeg, .webp"
        )

    type_info = ALLOWED_EXTENSIONS[ext]
    expected_magics = type_info["magic"]
    
    # Verify magic bytes header
    if not expected_magics:
        matched = True
    else:
        matched = False
        for magic in expected_magics:
            if ext == ".webp":
                if buffer.startswith(b"RIFF") and buffer[8:12] == b"WEBP":
                    matched = True
                    break
            elif buffer.startswith(magic):
                matched = True
                break

    if not matched:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File signature does not match its '{ext}' extension. Upload a genuine academic document."
        )

    # Perform security scanning
    scan_file_security(buffer, ext, type_info["kind"])

    return ext, type_info["mime"], type_info["kind"]
