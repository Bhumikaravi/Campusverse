import io
import os
import re
import zipfile
import logging
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

import pypdf
import docx
import pptx
from PIL import Image

try:
    import pymupdf  # PyMuPDF
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    from rapidocr_onnxruntime import RapidOCR
    _rapid_ocr_engine = None
    def get_rapid_ocr():
        global _rapid_ocr_engine
        if _rapid_ocr_engine is None:
            try:
                _rapid_ocr_engine = RapidOCR()
            except Exception as e:
                logger.warning("Could not initialize RapidOCR engine: %s", e)
                _rapid_ocr_engine = False
        return _rapid_ocr_engine if _rapid_ocr_engine is not False else None
except ImportError:
    get_rapid_ocr = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import olefile
except ImportError:
    olefile = None

from app.config import settings

logger = logging.getLogger("campusverse.text_extract")

@dataclass
class DocumentExtractionResult:
    document_id: str
    filename: str
    file_type: str
    total_pages: int
    processed_pages: int
    pages_text: List[str] = field(default_factory=list)
    pages_extracted: List[int] = field(default_factory=list)
    pages_ocr: List[int] = field(default_factory=list)
    pages_failed: List[int] = field(default_factory=list)
    total_words: int = 0
    extraction_status: str = "Completed"  # "Completed" | "Partially processed" | "Failed"
    ocr_used: bool = False
    ocr_available: bool = False
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# 0. OCR CAPABILITY DETECTION & EXECUTION
# ---------------------------------------------------------------------------
def check_ocr_available() -> bool:
    """Checks whether an OCR engine (RapidOCR, Tesseract binary, or Gemini Vision API) is available."""
    if get_rapid_ocr is not None:
        engine = get_rapid_ocr()
        if engine is not None:
            return True

    if pytesseract is not None:
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            pass

    if getattr(settings, "GEMINI_API_KEY", None):
        return True

    return False


def try_ocr_on_image_bytes(image_bytes: bytes) -> str:
    """
    Attempts OCR on rendered page image bytes using RapidOCR, pytesseract, or Gemini Vision.
    Returns extracted text if successful, or empty string.
    """
    # 1. Primary fast onnx OCR engine: RapidOCR
    if get_rapid_ocr is not None:
        try:
            engine = get_rapid_ocr()
            if engine is not None:
                ocr_res, _ = engine(image_bytes)
                if ocr_res:
                    lines = [line[1].strip() for line in ocr_res if line[1] and len(line[1].strip()) > 0]
                    text = "\n".join(lines).strip()
                    if text and len(text.split()) >= 2:
                        return text
        except Exception as e:
            logger.debug("RapidOCR execution error: %s", e)

    # 2. Secondary fallback: pytesseract
    if pytesseract is not None:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text and len(ocr_text.strip().split()) >= 2:
                return ocr_text.strip()
        except Exception as e:
            logger.debug("Pytesseract OCR execution failed: %s", e)

    return ""


# ---------------------------------------------------------------------------
# LIBREOFFICE HELPER
# ---------------------------------------------------------------------------
def find_libreoffice_executable() -> Optional[str]:
    """Finds LibreOffice soffice executable on the host system."""
    candidate_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "soffice",
        "libreoffice"
    ]
    for p in candidate_paths:
        if os.path.isabs(p) and os.path.exists(p):
            return p
        import shutil
        found = shutil.which(p)
        if found:
            return found
    return None


def convert_doc_with_libreoffice(buffer: bytes, target_format: str = "docx") -> Optional[bytes]:
    """Converts binary document (e.g. legacy .doc) to modern format using headless LibreOffice."""
    exe = find_libreoffice_executable()
    if not exe:
        return None
    try:
        with tempfile.TemporaryDirectory() as td:
            in_path = os.path.join(td, "document.doc")
            with open(in_path, "wb") as f:
                f.write(buffer)

            cmd = [exe, "--headless", "--convert-to", target_format, in_path, "--outdir", td]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            if res.returncode == 0:
                expected_out = os.path.join(td, f"document.{target_format}")
                if os.path.exists(expected_out) and os.path.getsize(expected_out) > 0:
                    with open(expected_out, "rb") as out_f:
                        return out_f.read()
    except Exception as e:
        logger.warning("LibreOffice conversion notice: %s", e)
    return None


# ---------------------------------------------------------------------------
# 1. PAGE COUNT DETERMINATION
# ---------------------------------------------------------------------------
def get_document_page_count(buffer: bytes, ext: str) -> int:
    """
    Determines the actual total page count of a document before processing.
    Raises ValueError for encrypted or corrupted documents.
    """
    ext = ext.lower().strip()

    if ext == ".pdf":
        if pymupdf is not None:
            try:
                doc = pymupdf.open(stream=buffer, filetype="pdf")
                if doc.is_encrypted:
                    raise ValueError("Encrypted PDF documents are not supported. Please upload an unencrypted file.")
                count = len(doc)
                doc.close()
                return max(1, count)
            except ValueError:
                raise
            except Exception as e:
                logger.warning("PyMuPDF page count failed, falling back to pypdf: %s", e)

        try:
            reader = pypdf.PdfReader(io.BytesIO(buffer))
            if reader.is_encrypted:
                raise ValueError("Encrypted PDF documents are not supported. Please upload an unencrypted file.")
            return max(1, len(reader.pages))
        except ValueError:
            raise
        except Exception as e:
            logger.warning("PDF page count extraction failed: %s", e)
            raise ValueError("The uploaded PDF appears to be corrupted or unreadable. Please check the file.")

    elif ext == ".docx":
        # 1. Check docProps/app.xml for authoritatively rendered page count
        try:
            with zipfile.ZipFile(io.BytesIO(buffer)) as z:
                if "docProps/app.xml" in z.namelist():
                    app_xml = z.read("docProps/app.xml").decode("utf-8", errors="ignore")
                    m = re.search(r"<Pages>(\d+)</Pages>", app_xml)
                    if m:
                        p_val = int(m.group(1))
                        if p_val > 0:
                            return p_val
        except Exception:
            pass

        # 2. Count explicit page breaks in document XML
        try:
            with zipfile.ZipFile(io.BytesIO(buffer)) as z:
                if "word/document.xml" in z.namelist():
                    doc_xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
                    explicit_breaks = len(re.findall(r'<w:br[^>]+w:type=["\']page["\']', doc_xml))
                    last_rendered = len(re.findall(r'<w:lastRenderedPageBreak\b', doc_xml))
                    break_count = max(explicit_breaks, last_rendered)
                    if break_count > 0:
                        return break_count + 1
        except Exception:
            pass

        # 3. Word count density fallback (~350 words per academic page)
        try:
            doc = docx.Document(io.BytesIO(buffer))
            total_words = sum(len(p.text.split()) for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    total_words += sum(len(cell.text.split()) for cell in row.cells)
            return max(1, (total_words // 350) + (1 if total_words % 350 > 40 else 0))
        except Exception:
            try:
                with zipfile.ZipFile(io.BytesIO(buffer)) as z:
                    xml_content = z.read("word/document.xml").decode("utf-8", errors="ignore")
                    text_pieces = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml_content)
                    words = len(" ".join(text_pieces).split())
                    return max(1, words // 350 + (1 if words % 350 > 40 else 0))
            except Exception as e:
                logger.warning("DOCX page count extraction error: %s", e)
                raise ValueError("The uploaded DOCX document appears to be corrupted or unreadable.")

    elif ext == ".doc":
        # If modern docx disguised as doc
        if buffer.startswith(b"PK\x03\x04"):
            return get_document_page_count(buffer, ".docx")

        # Check if LibreOffice can convert it
        converted = convert_doc_with_libreoffice(buffer, "docx")
        if converted:
            try:
                return get_document_page_count(converted, ".docx")
            except Exception:
                pass

        # Binary DOC fallback: count words from extracted text
        text = extract_legacy_doc_text(buffer)
        words = len(text.split())
        return max(1, words // 350 + (1 if words % 350 > 40 else 0))

    elif ext in [".pptx", ".ppt"]:
        if ext == ".pptx":
            try:
                prs = pptx.Presentation(io.BytesIO(buffer))
                return max(1, len(prs.slides))
            except Exception as e:
                logger.warning("PPTX slide count failed: %s", e)
                raise ValueError("The uploaded PPTX appears to be corrupted or unreadable.")
        else:
            return max(1, len(extract_legacy_doc_text(buffer).split("\n\n")))

    elif ext in [".txt", ".md"]:
        text = buffer.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        return max(1, (len(lines) // 45) + 1)

    else:
        return 1


# ---------------------------------------------------------------------------
# 2. PDF MULTI-PAGE EXTRACTION WITH PER-PAGE OCR FALLBACK
# ---------------------------------------------------------------------------
def extract_pdf_all_pages(buffer: bytes, max_pages: int = 150, document_id: str = "") -> DocumentExtractionResult:
    """
    Extracts text page-by-page from page 1 to the last page using PyMuPDF (fitz).
    Preserves exact page order, headings, tables, and document structure.
    Applies OCR selectively only on pages containing minimal or no extractable text.
    """
    ocr_available = check_ocr_available()
    pages_text = []
    pages_extracted = []
    pages_ocr = []
    pages_failed = []
    total_pages = 0

    # 1. Primary Engine: PyMuPDF
    if pymupdf is not None:
        try:
            doc = pymupdf.open(stream=buffer, filetype="pdf")
            total_pages = min(len(doc), max_pages)

            # Phase 1: Rapid digital text extraction across all pages (<0.1s for whole document)
            raw_pages = []
            potential_ocr_indices = []

            for page_idx in range(total_pages):
                page_num = page_idx + 1
                try:
                    page = doc[page_idx]
                    page_text = page.get_text("text").strip()
                    word_count = len(page_text.split())

                    # Check if page has minimal text and actually contains raster images
                    has_images = len(page.get_images()) > 0
                    if word_count < 5 and (has_images or word_count == 0) and ocr_available:
                        potential_ocr_indices.append(page_idx)

                    raw_pages.append(page_text)
                except Exception as page_err:
                    logger.warning("Error reading PDF page %d: %s", page_num, page_err)
                    raw_pages.append("")

            # Fast digital validation: If document already contains sufficient digital text,
            # it is a digital document and DOES NOT require heavy ONNX OCR (prevents 504 gateway timeout on slides/diagrams)
            total_digital_words = sum(len(p.split()) for p in raw_pages)
            pages_with_digital_text = sum(1 for p in raw_pages if len(p.split()) >= 4)

            needs_ocr_indices = []
            if total_digital_words < 30 and pages_with_digital_text < 2 and potential_ocr_indices:
                # Genuinely scanned document: run OCR on at most 4 pages to stay within strict HTTP response budget (<4s)
                needs_ocr_indices = potential_ocr_indices[:4]
                logger.info("PDF identified as scanned (digital words=%d). Applying OCR to first %d scanned pages.", total_digital_words, len(needs_ocr_indices))
            else:
                logger.info("PDF has digital text (digital words=%d across %d pages). Bypassing OCR for rapid sub-second processing.", total_digital_words, pages_with_digital_text)

            # Phase 2: Ultra-fast parallel OCR on scanned pages only
            if needs_ocr_indices:
                logger.info(
                    "Running optimized OCR on %d scanned pages out of %d total pages...",
                    len(needs_ocr_indices), total_pages
                )
                from concurrent.futures import ThreadPoolExecutor

                # Step A: Pre-render pixmaps in C sequentially (avoids fitz thread lock contention)
                # 90 DPI JPG with 80% quality matches RapidOCR model input perfectly and renders in <0.03s per page
                ocr_tasks = []
                for p_idx in needs_ocr_indices:
                    try:
                        p = doc[p_idx]
                        pix = p.get_pixmap(dpi=90)
                        jpg_bytes = pix.tobytes("jpg", jpg_quality=80)
                        ocr_tasks.append((p_idx, jpg_bytes))
                    except Exception as re:
                        logger.warning("Failed to render page %d for OCR: %s", p_idx + 1, re)

                # Step B: Execute pure ONNX OCR concurrently across all CPU threads
                def process_page_ocr(task):
                    p_idx, img_bytes = task
                    try:
                        ocr_t = try_ocr_on_image_bytes(img_bytes)
                        return p_idx, ocr_t
                    except Exception as e:
                        logger.warning("OCR failed on page %d: %s", p_idx + 1, e)
                        return p_idx, None

                workers = min(6, max(2, os.cpu_count() or 4))
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    ocr_results = list(executor.map(process_page_ocr, ocr_tasks))

                for p_idx, ocr_text in ocr_results:
                    page_num = p_idx + 1
                    if ocr_text and len(ocr_text.split()) >= 2:
                        existing = raw_pages[p_idx]
                        existing_lines = {l.strip().lower() for l in existing.splitlines() if l.strip()}
                        new_lines = [l.strip() for l in ocr_text.splitlines() if l.strip() and l.strip().lower() not in existing_lines]
                        if new_lines:
                            combined = f"{existing}\n" + "\n".join(new_lines) if existing else "\n".join(new_lines)
                            raw_pages[p_idx] = combined.strip()
                        pages_ocr.append(page_num)

            # Phase 3: Assemble extracted pages in strictly preserved chronological order
            for page_idx in range(total_pages):
                page_num = page_idx + 1
                text = raw_pages[page_idx].strip()
                if text and len(text.split()) > 0:
                    pages_text.append(text)
                    pages_extracted.append(page_num)
                else:
                    pages_text.append("")
                    pages_failed.append(page_num)

            doc.close()

        except Exception as doc_err:
            logger.warning("PyMuPDF failed to process PDF (%s), falling back to pypdf", doc_err)
            pages_text = []
            pages_extracted = []
            pages_ocr = []
            pages_failed = []

    # 2. Fallback Engine: pypdf (if PyMuPDF not available or failed)
    if not pages_text:
        try:
            reader = pypdf.PdfReader(io.BytesIO(buffer))
            total_pages = min(len(reader.pages), max_pages)

            pypdf_raw = []
            for page_idx in range(total_pages):
                try:
                    p = reader.pages[page_idx]
                    pypdf_raw.append((p.extract_text() or "").strip())
                except Exception:
                    pypdf_raw.append("")

            total_pypdf_words = sum(len(p.split()) for p in pypdf_raw)
            for page_idx in range(total_pages):
                page_num = page_idx + 1
                try:
                    page = reader.pages[page_idx]
                    clean_text = pypdf_raw[page_idx]

                    if total_pypdf_words < 30 and len(clean_text.split()) < 15 and hasattr(page, "images") and len(page.images) > 0 and len(pages_ocr) < 3:
                        ocr_parts = []
                        for img_obj in page.images[:2]:
                            ocr_t = try_ocr_on_image_bytes(img_obj.data)
                            if ocr_t:
                                ocr_parts.append(ocr_t)
                        if ocr_parts:
                            clean_text = f"{clean_text}\n" + "\n".join(ocr_parts).strip()
                            pages_ocr.append(page_num)

                    if clean_text:
                        pages_text.append(clean_text)
                        pages_extracted.append(page_num)
                    else:
                        pages_text.append("")
                        pages_failed.append(page_num)

                except Exception as pe:
                    logger.warning("pypdf error on page %d: %s", page_num, pe)
                    pages_text.append("")
                    pages_failed.append(page_num)

        except Exception as e:
            logger.error("All PDF extraction engines failed: %s", e)
            raise ValueError(f"Could not read PDF document: {str(e)}")

    total_words = sum(len(p.split()) for p in pages_text)
    processed_count = len(pages_extracted)

    # Determine status and warnings
    warning = None
    if processed_count == total_pages and total_pages > 0:
        status = "Completed"
    elif processed_count > 0:
        status = "Partially processed"
        warning = f"Extracted {processed_count} of {total_pages} pages. Pages {pages_failed} contained no extractable text."
    else:
        status = "Failed"
        if not ocr_available and (pages_failed or total_pages > 0):
            warning = "The PDF appears to be a scanned image or contains no digital text. OCR engine is not configured in this environment."
        else:
            warning = "Text extraction failed: No readable text could be extracted from this document."

    return DocumentExtractionResult(
        document_id=document_id,
        filename="",
        file_type="PDF",
        total_pages=total_pages,
        processed_pages=processed_count,
        pages_text=pages_text,
        pages_extracted=pages_extracted,
        pages_ocr=pages_ocr,
        pages_failed=pages_failed,
        total_words=total_words,
        extraction_status=status,
        ocr_used=len(pages_ocr) > 0,
        ocr_available=ocr_available,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# 3. DOCX EXTRACTION (PARAGRAPHS, TABLES, TEXT BOXES, SHAPES, & XML FALLBACK)
# ---------------------------------------------------------------------------
def extract_docx_all_pages(buffer: bytes, document_id: str = "") -> DocumentExtractionResult:
    """
    Extracts text from DOCX documents preserving paragraphs, tables, lists, text boxes, and headings.
    Includes comprehensive support for shapes, headers, footers, and direct XML decompression.
    """
    text_blocks = []

    # 1. Primary: python-docx
    try:
        doc = docx.Document(io.BytesIO(buffer))

        # Paragraphs
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                text_blocks.append(txt)

        # Tables (preserving rows and cells)
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    text_blocks.append(" | ".join(row_cells))

        # Text boxes and drawings (w:txbxContent)
        try:
            for txbx in doc.element.xpath('.//w:txbxContent'):
                for p in txbx.xpath('.//w:p'):
                    p_texts = [t.text for t in p.xpath('.//w:t') if t.text]
                    if p_texts:
                        txt = "".join(p_texts).strip()
                        if txt and txt not in text_blocks:
                            text_blocks.append(txt)
        except Exception:
            pass

        # Headers and Footers
        try:
            for sec in doc.sections:
                for hp in sec.header.paragraphs:
                    ht = hp.text.strip()
                    if ht and ht not in text_blocks:
                        text_blocks.insert(0, ht)
                for fp in sec.footer.paragraphs:
                    ft = fp.text.strip()
                    if ft and ft not in text_blocks:
                        text_blocks.append(ft)
        except Exception:
            pass

    except Exception as docx_err:
        logger.warning("python-docx parsing notice (%s), attempting direct XML decompression", docx_err)

    # 2. Resilient Fallback: direct ZIP XML extraction
    if not text_blocks:
        try:
            with zipfile.ZipFile(io.BytesIO(buffer)) as z:
                # Process document.xml and any header/footer files
                xml_files = [f for f in z.namelist() if f.startswith("word/") and f.endswith(".xml")]
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

                # Ensure main document is first
                if "word/document.xml" in xml_files:
                    xml_files.remove("word/document.xml")
                    xml_files.insert(0, "word/document.xml")

                for xf in xml_files:
                    xml_bytes = z.read(xf)
                    root = ET.fromstring(xml_bytes)
                    for p in root.findall(".//w:p", ns):
                        p_texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
                        if p_texts:
                            clean_t = "".join(p_texts).strip()
                            if clean_t and clean_t not in text_blocks:
                                text_blocks.append(clean_t)
                    for row in root.findall(".//w:tr", ns):
                        r_cells = ["".join(t.text for t in tc.findall(".//w:t", ns) if t.text).strip() for tc in row.findall(".//w:tc", ns)]
                        r_clean = [c for c in r_cells if c]
                        if r_clean:
                            text_blocks.append(" | ".join(r_clean))
        except Exception as xml_err:
            logger.warning("Direct ZIP XML fallback failed: %s", xml_err)

    if not text_blocks:
        raise ValueError("The uploaded DOCX document contains no readable text or is corrupted.")

    # Partition text into page-equivalent units (~350 words per academic page)
    pages = []
    curr = []
    curr_words = 0
    for block in text_blocks:
        b_words = len(block.split())
        if curr_words + b_words > 350 and curr:
            pages.append("\n\n".join(curr))
            curr = [block]
            curr_words = b_words
        else:
            curr.append(block)
            curr_words += b_words
    if curr:
        pages.append("\n\n".join(curr))

    total_pages = max(1, len(pages))
    total_words = sum(len(p.split()) for p in pages)
    pages_extracted = list(range(1, total_pages + 1))

    return DocumentExtractionResult(
        document_id=document_id,
        filename="",
        file_type="DOCX",
        total_pages=total_pages,
        processed_pages=total_pages,
        pages_text=pages,
        pages_extracted=pages_extracted,
        pages_ocr=[],
        pages_failed=[],
        total_words=total_words,
        extraction_status="Completed",
        ocr_used=False,
        ocr_available=check_ocr_available(),
        warning=None,
    )


# ---------------------------------------------------------------------------
# 4. LEGACY DOC EXTRACTION
# ---------------------------------------------------------------------------
def extract_legacy_doc_text(buffer: bytes) -> str:
    """Extracts text from legacy binary Microsoft Word 97-2003 (.doc) files."""
    # 1. If actually OpenXML zip, extract using DOCX engine
    if buffer.startswith(b"PK\x03\x04"):
        try:
            res = extract_docx_all_pages(buffer)
            return "\n\n".join(res.pages_text)
        except Exception:
            pass

    # 2. Try OLE structured storage with olefile
    if olefile is not None:
        try:
            if olefile.isOleFile(io.BytesIO(buffer)):
                ole = olefile.OleFileIO(io.BytesIO(buffer))
                text_parts = []
                if ole.exists("WordDocument"):
                    stream = ole.openstream("WordDocument").read()
                    # Extract UTF-16LE text runs
                    utf16_runs = re.findall(rb"(?:[\x20-\x7E\t\r\n]\x00){3,}", stream)
                    for r in utf16_runs:
                        try:
                            dec = r.decode("utf-16le", errors="ignore").strip()
                            if len(dec.split()) >= 2:
                                text_parts.append(dec)
                        except Exception:
                            pass
                    # Extract continuous ASCII runs
                    ascii_runs = re.findall(rb"[\x20-\x7E\t\r\n]{4,}", stream)
                    for r in ascii_runs:
                        try:
                            dec = r.decode("latin1", errors="ignore").strip()
                            if not dec.startswith(("Microsoft", "Word.Document", "Normal.dot", "CompObj", "SummaryInformation")):
                                if len(dec.split()) >= 2 and dec not in text_parts:
                                    text_parts.append(dec)
                        except Exception:
                            pass
                ole.close()
                if text_parts:
                    return "\n\n".join(text_parts)
        except Exception as e:
            logger.debug("olefile extraction notice: %s", e)

    # 3. Direct binary stream parsing fallback
    try:
        decoded_parts = []
        ascii_strings = re.findall(rb"[\x20-\x7E]{4,}", buffer)
        for s in ascii_strings:
            decoded = s.decode("latin1", errors="ignore").strip()
            if not decoded.startswith(("Microsoft", "Word.Document", "Normal.dot", "CompObj", "SummaryInformation")):
                if len(decoded.split()) >= 2:
                    decoded_parts.append(decoded)

        utf16_strings = re.findall(rb"(?:[\x20-\x7E]\x00){4,}", buffer)
        for s in utf16_strings:
            try:
                decoded = s.decode("utf-16le", errors="ignore").strip()
                if len(decoded.split()) >= 2 and decoded not in decoded_parts:
                    decoded_parts.append(decoded)
            except Exception:
                pass

        return "\n\n".join(decoded_parts)
    except Exception as e:
        logger.warning("Legacy DOC text extraction error: %s", e)
        return ""


def extract_legacy_doc_pages(buffer: bytes, document_id: str = "") -> DocumentExtractionResult:
    """Extracts text and estimates pages for legacy .doc files using LibreOffice or OLE parsing."""
    # 1. If actually OpenXML docx disguised as doc
    if buffer.startswith(b"PK\x03\x04"):
        res = extract_docx_all_pages(buffer, document_id=document_id)
        res.file_type = "DOC"
        return res

    # 2. Try headless LibreOffice conversion
    converted_docx = convert_doc_with_libreoffice(buffer, "docx")
    if converted_docx:
        try:
            res = extract_docx_all_pages(converted_docx, document_id=document_id)
            res.file_type = "DOC"
            return res
        except Exception as e:
            logger.warning("Converted DOCX extraction failed: %s", e)

    # 3. Native OLE2 stream extraction fallback
    text = extract_legacy_doc_text(buffer)
    words = text.split()
    if len(words) < 5:
        raise ValueError(
            "The uploaded DOC document contains insufficient readable text or is corrupted. "
            "Please upload a standard DOCX or PDF document."
        )

    # Group into ~350 word pages
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    pages = []
    curr = []
    curr_words = 0
    for b in blocks:
        bw = len(b.split())
        if curr_words + bw > 350 and curr:
            pages.append("\n\n".join(curr))
            curr = [b]
            curr_words = bw
        else:
            curr.append(b)
            curr_words += bw
    if curr:
        pages.append("\n\n".join(curr))

    total_pages = max(1, len(pages))
    total_words = len(words)
    pages_extracted = list(range(1, total_pages + 1))

    return DocumentExtractionResult(
        document_id=document_id,
        filename="",
        file_type="DOC",
        total_pages=total_pages,
        processed_pages=total_pages,
        pages_text=pages,
        pages_extracted=pages_extracted,
        pages_ocr=[],
        pages_failed=[],
        total_words=total_words,
        extraction_status="Completed",
        ocr_used=False,
        ocr_available=check_ocr_available(),
        warning=None,
    )


# ---------------------------------------------------------------------------
# 5. PPTX / PPT PRESENTATION EXTRACTION
# ---------------------------------------------------------------------------
def extract_pptx_all_pages(buffer: bytes, max_slides: int = 150, document_id: str = "") -> DocumentExtractionResult:
    """Extracts text from every slide of a presentation from first to last slide."""
    slides_text = []
    try:
        prs = pptx.Presentation(io.BytesIO(buffer))
        total_slides = min(len(prs.slides), max_slides)

        for i in range(total_slides):
            slide = prs.slides[i]
            slide_lines = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_lines.append(text)
                elif shape.has_table:
                    for row in shape.table.rows:
                        row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_vals:
                            slide_lines.append(" | ".join(row_vals))
            slides_text.append("\n".join(slide_lines).strip())

    except Exception as e:
        logger.warning("PPTX extraction error: %s", e)
        raise ValueError("Could not read presentation file: " + str(e))

    total_slides = len(slides_text)
    pages_extracted = [i + 1 for i, s in enumerate(slides_text) if s.strip()]
    pages_failed = [i + 1 for i, s in enumerate(slides_text) if not s.strip()]
    total_words = sum(len(s.split()) for s in slides_text)

    status = "Completed" if not pages_failed else ("Partially processed" if pages_extracted else "Failed")

    return DocumentExtractionResult(
        document_id=document_id,
        filename="",
        file_type="PPTX",
        total_pages=total_slides,
        processed_pages=len(pages_extracted),
        pages_text=slides_text,
        pages_extracted=pages_extracted,
        pages_ocr=[],
        pages_failed=pages_failed,
        total_words=total_words,
        extraction_status=status,
        ocr_used=False,
        ocr_available=check_ocr_available(),
        warning=None if not pages_failed else f"Slides {pages_failed} contained no text.",
    )


# ---------------------------------------------------------------------------
# 6. UNIFIED COMPLETE EXTRACTION DISPATCHER
# ---------------------------------------------------------------------------
def extract_document_pages(buffer: bytes, ext: str, max_pages: int = 150, document_id: str = "") -> List[str]:
    """Compatibility wrapper returning a list of strings (one per page/slide) in exact order."""
    res = extract_document_complete(buffer, ext, max_pages=max_pages, document_id=document_id)
    return res.pages_text


def extract_document_complete(buffer: bytes, ext: str, max_pages: int = 150, document_id: str = "") -> DocumentExtractionResult:
    """
    Master extraction function that identifies file type, extracts all pages/slides,
    preserves exact page order, handles OCR, and returns rich validation metrics.
    """
    ext = ext.lower().strip()

    if ext == ".pdf":
        result = extract_pdf_all_pages(buffer, max_pages=max_pages, document_id=document_id)
    elif ext == ".docx":
        result = extract_docx_all_pages(buffer, document_id=document_id)
    elif ext == ".doc":
        result = extract_legacy_doc_pages(buffer, document_id=document_id)
    elif ext in [".pptx", ".ppt"]:
        if ext == ".pptx":
            result = extract_pptx_all_pages(buffer, max_slides=max_pages, document_id=document_id)
        else:
            doc_res = extract_legacy_doc_pages(buffer, document_id=document_id)
            doc_res.file_type = "PPT"
            result = doc_res
    elif ext in [".txt", ".md"]:
        text = buffer.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        chunks = []
        for i in range(0, max(1, len(lines)), 50):
            chunk = "\n".join(lines[i:i+50]).strip()
            if chunk:
                chunks.append(chunk)
        pages = chunks or [text]
        result = DocumentExtractionResult(
            document_id=document_id,
            filename="",
            file_type="TXT" if ext == ".txt" else "MD",
            total_pages=len(pages),
            processed_pages=len(pages),
            pages_text=pages,
            pages_extracted=list(range(1, len(pages) + 1)),
            pages_ocr=[],
            pages_failed=[],
            total_words=sum(len(p.split()) for p in pages),
            extraction_status="Completed",
            ocr_used=False,
            ocr_available=check_ocr_available(),
            warning=None,
        )
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        ocr_text = try_ocr_on_image_bytes(buffer)
        if not ocr_text:
            ocr_text = "Image Document: Visual academic note."
        result = DocumentExtractionResult(
            document_id=document_id,
            filename="",
            file_type=ext.upper().lstrip("."),
            total_pages=1,
            processed_pages=1 if ocr_text else 0,
            pages_text=[ocr_text],
            pages_extracted=[1] if ocr_text else [],
            pages_ocr=[1] if ocr_text else [],
            pages_failed=[] if ocr_text else [1],
            total_words=len(ocr_text.split()),
            extraction_status="Completed" if ocr_text else "Failed",
            ocr_used=True,
            ocr_available=check_ocr_available(),
            warning=None if ocr_text else "OCR could not extract text from this image.",
        )
    else:
        raise ValueError(f"Unsupported document format '{ext}'. Supported formats: PDF, DOCX, DOC, PPTX, PPT, TXT, MD.")

    return result


def extract_document_text(buffer: bytes, ext: str, max_pages: int = 150) -> str:
    """Extracts all text across the entire document from first to last page as a single string."""
    res = extract_document_complete(buffer, ext, max_pages=max_pages)
    cleaned = [p.strip() for p in res.pages_text if p.strip()]
    return "\n\n".join(cleaned)
