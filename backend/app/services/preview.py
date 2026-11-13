import html
import io
from typing import Dict, Any, Callable, Awaitable
import docx
import pptx

def docx_to_clean_html(buffer: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(buffer))
        html_parts = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            escaped = html.escape(text)
            style_name = (p.style.name if p.style and hasattr(p.style, "name") and p.style.name else "")
            if style_name.startswith("Heading 1"):
                html_parts.append(f"<h2 class='text-xl font-bold text-gray-900 mt-5 mb-2.5 pb-1.5 border-b border-gray-100'>{escaped}</h2>")
            elif style_name.startswith("Heading"):
                html_parts.append(f"<h3 class='text-lg font-semibold text-gray-800 mt-4 mb-2'>{escaped}</h3>")
            elif style_name.startswith("List") or text.startswith(("•", "-", "*", "1.", "2.", "3.", "4.", "5.")):
                html_parts.append(f"<div class='flex items-start gap-2 text-sm text-gray-700 leading-relaxed mb-1.5 ml-2'><span class='text-brand-600 font-bold shrink-0'>•</span><span>{escaped}</span></div>")
            else:
                html_parts.append(f"<p class='text-sm text-gray-700 leading-relaxed mb-3'>{escaped}</p>")

        for table in doc.tables:
            html_parts.append("<div class='overflow-x-auto my-4'><table class='w-full text-xs border border-gray-200'>")
            for row in table.rows:
                html_parts.append("<tr class='border-b border-gray-100'>")
                for cell in row.cells:
                    html_parts.append(f"<td class='p-2 border border-gray-200'>{html.escape(cell.text.strip())}</td>")
                html_parts.append("</tr>")
            html_parts.append("</table></div>")

        if html_parts:
            return "".join(html_parts)

        # Fallback to text_extract if docx has text in shapes or text boxes
        from app.services.text_extract import extract_docx_all_pages
        extracted_res = extract_docx_all_pages(buffer)
        if extracted_res and extracted_res.pages_text:
            fallback_parts = []
            for page in extracted_res.pages_text:
                for line in page.splitlines():
                    cl = line.strip()
                    if cl:
                        fallback_parts.append(f"<p class='text-sm text-gray-700 leading-relaxed mb-3'>{html.escape(cl)}</p>")
            if fallback_parts:
                return "".join(fallback_parts)

        return "<p class='text-sm text-gray-500'>Document contains no readable text paragraphs.</p>"
    except Exception as e:
        # Graceful fallback: try extracting raw text from OpenXML / text_extract
        try:
            from app.services.text_extract import extract_docx_all_pages
            extracted_res = extract_docx_all_pages(buffer)
            if extracted_res and extracted_res.pages_text:
                fallback_parts = []
                for page in extracted_res.pages_text:
                    for line in page.splitlines():
                        cl = line.strip()
                        if cl:
                            fallback_parts.append(f"<p class='text-sm text-gray-700 leading-relaxed mb-3'>{html.escape(cl)}</p>")
                if fallback_parts:
                    return "".join(fallback_parts)
        except Exception:
            pass

        return f"<p class='text-sm text-red-500'>Could not generate document preview: {html.escape(str(e))}</p>"

def pptx_to_slides(buffer: bytes) -> list:
    try:
        prs = pptx.Presentation(io.BytesIO(buffer))
        slides = []
        for i, slide in enumerate(prs.slides):
            lines = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        txt = paragraph.text.strip()
                        if txt:
                            lines.append(txt)
            slides.append({
                "index": i + 1,
                "text": "\n".join(lines) or "Visual slide diagram."
            })
        return slides
    except Exception:
        return []

async def build_material_preview(material: dict, load_bytes_fn: Callable[[], Awaitable[bytes]]) -> Dict[str, Any]:
    ext = material.get("extension", "").lower()
    file_url = material.get("fileUrl", f"/api/materials/{material.get('id', material.get('_id'))}/file")
    mime_type = material.get("mimeType", "application/octet-stream")

    if ext == ".pdf":
        return {
            "kind": "pdf",
            "fileUrl": file_url,
            "mimeType": "application/pdf"
        }

    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return {
            "kind": "image",
            "fileUrl": file_url,
            "mimeType": mime_type
        }

    if ext in [".docx", ".doc"]:
        buffer = await load_bytes_fn()
        if ext == ".doc":
            from app.services.text_extract import convert_doc_with_libreoffice, extract_legacy_doc_text
            converted = convert_doc_with_libreoffice(buffer, "docx")
            if converted:
                buffer = converted
            else:
                text = extract_legacy_doc_text(buffer)
                if text:
                    escaped = html.escape(text).replace("\n", "<br/>")
                    return {
                        "kind": "html",
                        "html": f"<div class='p-4 text-sm text-gray-800 leading-relaxed'>{escaped}</div>"
                    }
        rendered_html = docx_to_clean_html(buffer)
        return {
            "kind": "html",
            "html": rendered_html[:250_000]
        }

    if ext == ".pptx":
        buffer = await load_bytes_fn()
        slides = pptx_to_slides(buffer)
        return {
            "kind": "slides",
            "slides": slides[:100]
        }

    return {
        "kind": "unsupported",
        "reason": f"In-browser inline preview is not supported for '{ext}' files. Please click Download to view it with your desktop application."
    }
