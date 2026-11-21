import html
import io
import base64
import logging
from typing import Dict, Any, Callable, Awaitable
import docx
import pptx

logger = logging.getLogger("campusverse.preview")

def docx_to_faithful_html(buffer: bytes) -> str:
    """
    Faithfully converts a DOCX document into rich, styled HTML preserving:
    - Exact sequential body order (headings, paragraphs, tables, images, page breaks)
    - Run-level typography (font family, font size, bold, italic, underline, text colors)
    - Paragraph alignments (left, center, right, justify)
    - Embedded images extracted as high-fidelity base64 data URLs
    - Formatted tables with headers, borders, cell backgrounds, and cell alignments
    - Visual page breaks
    """
    try:
        doc = docx.Document(io.BytesIO(buffer))
        parts = [
            '<div class="docx-document bg-white p-6 sm:p-12 max-w-4xl mx-auto shadow-sm rounded-xl border border-gray-200 font-sans text-gray-800">'
        ]

        for child in doc.element.body:
            tag = child.tag.split("}")[-1]

            # Paragraph or Heading
            if tag == "p":
                p = docx.text.paragraph.Paragraph(child, doc)
                text = p.text.strip()
                
                # Check for page breaks
                has_page_break = bool(p._p.xpath('.//w:br[@w:type="page"]') or (p.paragraph_format and p.paragraph_format.page_break_before))
                if has_page_break:
                    parts.append(
                        '<div class="docx-page-divider flex items-center my-8 select-none">'
                        '<hr class="flex-1 border-dashed border-gray-300"/>'
                        '<span class="px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider bg-gray-100 rounded-full border border-gray-200">Page Break</span>'
                        '<hr class="flex-1 border-dashed border-gray-300"/>'
                        '</div>'
                    )

                if not text and not p._p.xpath('.//a:blip'):
                    continue

                style_name = (p.style.name if p.style and hasattr(p.style, "name") else "") or ""
                
                # Paragraph alignment
                align_style = ""
                if p.alignment:
                    a_str = str(p.alignment).lower()
                    if "center" in a_str:
                        align_style = "text-align: center;"
                    elif "right" in a_str:
                        align_style = "text-align: right;"
                    elif "justify" in a_str:
                        align_style = "text-align: justify;"

                run_htmls = []
                for r in p.runs:
                    # Check for embedded images in this run
                    blips = r._r.xpath('.//a:blip/@r:embed')
                    if blips:
                        for r_id in blips:
                            if r_id in doc.part.related_parts:
                                img_part = doc.part.related_parts[r_id]
                                b64 = base64.b64encode(img_part.blob).decode("ascii")
                                mime = img_part.content_type
                                run_htmls.append(
                                    f'<div class="my-4 text-center">'
                                    f'<img src="data:{mime};base64,{b64}" class="max-w-full h-auto rounded-lg shadow-sm mx-auto border border-gray-200" alt="Document figure" />'
                                    f'</div>'
                                )

                    txt = html.escape(r.text)
                    if not txt:
                        continue

                    # Run-level styling
                    styles = []
                    if r.font.name:
                        styles.append(f'font-family: "{r.font.name}", sans-serif;')
                    if r.font.size and hasattr(r.font.size, "pt"):
                        styles.append(f'font-size: {r.font.size.pt}pt;')
                    if r.font.color and hasattr(r.font.color, "rgb") and r.font.color.rgb:
                        styles.append(f'color: #{r.font.color.rgb};')

                    style_attr = f' style="{" ".join(styles)}"' if styles else ""
                    r_content = f'<span{style_attr}>{txt}</span>' if styles else txt
                    if r.bold:
                        r_content = f'<strong>{r_content}</strong>'
                    if r.italic:
                        r_content = f'<em>{r_content}</em>'
                    if r.underline:
                        r_content = f'<u>{r_content}</u>'
                    run_htmls.append(r_content)

                inner = "".join(run_htmls)
                p_style = f' style="{align_style}"' if align_style else ""

                if style_name.startswith("Title"):
                    parts.append(
                        f'<h1 class="docx-title text-2xl sm:text-3xl font-extrabold text-gray-900 mb-3 pb-2 border-b border-gray-200"{p_style}>{inner}</h1>'
                    )
                elif style_name.startswith("Subtitle"):
                    parts.append(
                        f'<p class="docx-subtitle text-base sm:text-lg text-gray-600 italic mb-4"{p_style}>{inner}</p>'
                    )
                elif style_name.startswith("Heading 1"):
                    parts.append(
                        f'<h2 class="docx-h1 text-xl sm:text-2xl font-bold text-gray-900 mt-6 mb-2.5 pb-1 border-b border-gray-100"{p_style}>{inner}</h2>'
                    )
                elif style_name.startswith("Heading 2"):
                    parts.append(
                        f'<h3 class="docx-h2 text-lg sm:text-xl font-bold text-gray-800 mt-5 mb-2"{p_style}>{inner}</h3>'
                    )
                elif style_name.startswith("Heading 3"):
                    parts.append(
                        f'<h4 class="docx-h3 text-base sm:text-lg font-semibold text-gray-800 mt-4 mb-1.5"{p_style}>{inner}</h4>'
                    )
                elif "List" in style_name or text.startswith(("•", "-", "*")):
                    clean_text = inner.lstrip("•-* ").strip()
                    parts.append(
                        f'<div class="docx-list-item flex items-start gap-2 text-sm sm:text-base text-gray-800 my-1 ml-4">'
                        f'<span class="text-brand-600 font-bold shrink-0">•</span>'
                        f'<div>{clean_text}</div>'
                        f'</div>'
                    )
                else:
                    parts.append(
                        f'<p class="docx-p text-sm sm:text-base text-gray-800 leading-relaxed my-2"{p_style}>{inner}</p>'
                    )

            # Table
            elif tag == "tbl":
                t = docx.table.Table(child, doc)
                parts.append(
                    '<div class="docx-table-container overflow-x-auto my-5 rounded-xl border border-gray-200 shadow-2xs">'
                    '<table class="docx-table w-full text-xs sm:text-sm text-left border-collapse bg-white">'
                )
                for r_idx, row in enumerate(t.rows):
                    is_header = (r_idx == 0)
                    row_bg = (
                        'bg-gray-100/90 font-bold text-gray-900 border-b border-gray-300'
                        if is_header
                        else 'border-b border-gray-100 hover:bg-gray-50/60'
                    )
                    parts.append(f'<tr class="{row_bg}">')
                    for cell in row.cells:
                        tag_name = "th" if is_header else "td"
                        # Cell background shading
                        cell_bg_style = ""
                        shd = cell._tc.xpath('.//w:shd/@w:fill')
                        if shd and shd[0] and shd[0].lower() != "auto":
                            cell_bg_style = f' style="background-color: #{shd[0]};"'
                            
                        cell_text = html.escape(cell.text.strip()).replace("\n", "<br/>")
                        parts.append(
                            f'<{tag_name}{cell_bg_style} class="p-2.5 sm:p-3 border-r border-gray-200 last:border-r-0 leading-normal">'
                            f'{cell_text}'
                            f'</{tag_name}>'
                        )
                    parts.append('</tr>')
                parts.append('</table></div>')

        parts.append('</div>')
        return "".join(parts)
    except Exception as e:
        logger.error("Error in docx_to_faithful_html: %s", e)
        # Fallback to plain readable paragraphs
        try:
            doc = docx.Document(io.BytesIO(buffer))
            fallback_parts = ['<div class="p-6 bg-white rounded-xl shadow-sm text-gray-800 text-sm leading-relaxed">']
            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt:
                    fallback_parts.append(f'<p class="mb-3">{html.escape(txt)}</p>')
            fallback_parts.append('</div>')
            return "".join(fallback_parts)
        except Exception:
            return f'<div class="p-6 text-red-600 bg-red-50 rounded-xl">Could not render Word document preview: {html.escape(str(e))}</div>'


def pptx_to_faithful_slides(buffer: bytes) -> dict:
    """
    Faithfully parses PPTX presentation preserving:
    - Slide aspect ratio (16:9 or 4:3)
    - Slide background colors
    - Exact relative coordinates and bounding boxes of all shapes
    - Run-level formatting (font size, bold, italic, colors, bullet points)
    - Positioned tables and images
    """
    try:
        prs = pptx.Presentation(io.BytesIO(buffer))
        sw = prs.slide_width
        sh = prs.slide_height
        aspect_ratio = round(sw / sh, 4) if sh else 1.3333
        aspect_ratio_str = "16 / 9" if abs(aspect_ratio - 1.7778) < 0.15 else ("4 / 3" if abs(aspect_ratio - 1.3333) < 0.15 else f"{sw} / {sh}")

        slides_data = []

        for idx, slide in enumerate(prs.slides):
            slide_title = ""
            elements = []
            slide_text_lines = []

            # Check slide background
            bg_color = "#ffffff"
            try:
                background = slide.background
                fill = background.fill
                if fill.type == 1 and hasattr(fill, "fore_color") and hasattr(fill.fore_color, "rgb"):
                    bg_color = f"#{fill.fore_color.rgb}"
            except Exception:
                pass

            for shape in slide.shapes:
                left_pct = round((shape.left / sw) * 100, 2) if shape.left is not None else 0
                top_pct = round((shape.top / sh) * 100, 2) if shape.top is not None else 0
                width_pct = round((shape.width / sw) * 100, 2) if shape.width is not None else 100
                height_pct = round((shape.height / sh) * 100, 2) if shape.height is not None else 20

                # 1. Image Shape
                if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
                    try:
                        img_blob = shape.image.blob
                        img_mime = shape.image.content_type
                        b64 = base64.b64encode(img_blob).decode("ascii")
                        elements.append({
                            "type": "image",
                            "left": left_pct,
                            "top": top_pct,
                            "width": width_pct,
                            "height": height_pct,
                            "src": f"data:{img_mime};base64,{b64}",
                        })
                        continue
                    except Exception:
                        pass

                # 2. Table Shape
                if shape.has_table:
                    table_rows = []
                    for row in shape.table.rows:
                        row_cells = []
                        for cell in row.cells:
                            c_text = cell.text.strip()
                            cell_bg = None
                            try:
                                if cell.fill.type == 1 and hasattr(cell.fill.fore_color, "rgb"):
                                    cell_bg = f"#{cell.fill.fore_color.rgb}"
                            except Exception:
                                pass
                            row_cells.append({
                                "text": c_text,
                                "bgColor": cell_bg,
                            })
                        table_rows.append(row_cells)
                    elements.append({
                        "type": "table",
                        "left": left_pct,
                        "top": top_pct,
                        "width": width_pct,
                        "height": height_pct,
                        "rows": table_rows,
                    })
                    continue

                # 3. Text Frames
                if shape.has_text_frame:
                    paragraphs_data = []
                    is_title_shape = (
                        shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PLACEHOLDER
                        and hasattr(shape, "placeholder_format")
                        and shape.placeholder_format.type in [1, 3] # Title or Center Title
                    )

                    for p in shape.text_frame.paragraphs:
                        p_text = p.text.strip()
                        if not p_text:
                            continue

                        if not slide_title and (is_title_shape or len(p_text) < 80):
                            slide_title = p_text

                        slide_text_lines.append(p_text)

                        align = "left"
                        if p.alignment:
                            a_str = str(p.alignment).lower()
                            if "center" in a_str:
                                align = "center"
                            elif "right" in a_str:
                                align = "right"
                            elif "justify" in a_str:
                                align = "justify"

                        runs_data = []
                        for r in p.runs:
                            r_txt = r.text
                            if not r_txt:
                                continue
                            f_size = r.font.size.pt if (r.font.size and hasattr(r.font.size, "pt")) else None
                            f_color = None
                            try:
                                if r.font.color and hasattr(r.font.color, "rgb") and r.font.color.rgb:
                                    f_color = f"#{r.font.color.rgb}"
                            except Exception:
                                pass
                            runs_data.append({
                                "text": r_txt,
                                "bold": bool(r.font.bold),
                                "italic": bool(r.font.italic),
                                "underline": bool(r.font.underline),
                                "fontSize": f_size,
                                "fontColor": f_color,
                                "fontName": r.font.name or None,
                            })

                        paragraphs_data.append({
                            "text": p_text,
                            "align": align,
                            "level": p.level or 0,
                            "runs": runs_data if runs_data else [{"text": p_text}],
                        })

                    if paragraphs_data:
                        elements.append({
                            "type": "text",
                            "isTitle": is_title_shape,
                            "left": left_pct,
                            "top": top_pct,
                            "width": width_pct,
                            "height": height_pct,
                            "paragraphs": paragraphs_data,
                        })

            slides_data.append({
                "index": idx + 1,
                "title": slide_title or f"Slide {idx + 1}",
                "bgColor": bg_color,
                "elements": elements,
                "text": "\n".join(slide_text_lines) or "Slide content",
            })

        return {
            "aspectRatio": aspect_ratio_str,
            "totalSlides": len(slides_data),
            "slides": slides_data,
        }
    except Exception as e:
        logger.error("Error in pptx_to_faithful_slides: %s", e)
        return {
            "aspectRatio": "16 / 9",
            "totalSlides": 1,
            "slides": [{
                "index": 1,
                "title": "Presentation",
                "bgColor": "#ffffff",
                "elements": [],
                "text": f"Could not parse slides: {str(e)}",
            }],
        }


def extract_raw_text(buffer: bytes) -> str:
    """Safely decodes raw text file buffer into string without modifying any characters."""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return buffer.decode(enc)
        except UnicodeDecodeError:
            continue
    return buffer.decode("utf-8", errors="replace")


async def build_material_preview(material: dict, load_bytes_fn: Callable[[], Awaitable[bytes]]) -> Dict[str, Any]:
    """
    Builds faithful, unsummarized preview payload from original uploaded file.
    Does NOT use AI summaries, OCR snippets, or RAG chunks as preview content.
    """
    ext = (material.get("extension", "") or material.get("fileType", "") or "pdf").lower()
    if not ext.startswith("."):
        ext = f".{ext}"
        
    doc_id = str(material.get("id") or material.get("_id") or "")
    file_url = material.get("fileUrl") or f"/api/materials/{doc_id}/file"
    original_name = material.get("originalName") or f"{material.get('title', 'document')}{ext}"
    mime_type = material.get("mimeType", "application/octet-stream")

    # 1. PDF
    if ext == ".pdf":
        return {
            "kind": "pdf",
            "fileUrl": file_url,
            "fileName": original_name,
            "extension": "pdf",
            "mimeType": "application/pdf",
        }

    # 2. Image formats
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]:
        return {
            "kind": "image",
            "fileUrl": file_url,
            "fileName": original_name,
            "extension": ext.lstrip("."),
            "mimeType": mime_type or f"image/{ext.lstrip('.')}",
        }

    # 3. Plain Text and Code formats (TXT, MD, PY, JAVA, C, CPP, JSON, SQL, CSV)
    if ext in [".txt", ".md", ".json", ".py", ".java", ".c", ".cpp", ".sql", ".csv", ".log", ".rtf"]:
        buffer = await load_bytes_fn()
        raw_text = extract_raw_text(buffer)
        lines = raw_text.splitlines()
        words = raw_text.split()
        return {
            "kind": "text",
            "content": raw_text,
            "fileUrl": file_url,
            "fileName": original_name,
            "extension": ext.lstrip("."),
            "lineCount": len(lines),
            "wordCount": len(words),
            "charCount": len(raw_text),
            "mimeType": "text/plain",
        }

    # 4. Word Documents (DOCX, DOC)
    if ext in [".docx", ".doc"]:
        buffer = await load_bytes_fn()
        if ext == ".doc":
            from app.services.text_extract import convert_doc_with_libreoffice, extract_legacy_doc_text
            converted = convert_doc_with_libreoffice(buffer, "docx")
            if converted:
                buffer = converted
            else:
                legacy_text = extract_legacy_doc_text(buffer) or ""
                escaped = html.escape(legacy_text).replace("\n", "<br/>")
                return {
                    "kind": "docx",
                    "html": f'<div class="p-6 bg-white rounded-xl shadow-sm text-gray-800 text-sm leading-relaxed whitespace-pre-line">{escaped}</div>',
                    "fileUrl": file_url,
                    "fileName": original_name,
                    "extension": "doc",
                    "mimeType": "application/msword",
                }

        rendered_html = docx_to_faithful_html(buffer)
        return {
            "kind": "docx",
            "html": rendered_html,
            "fileUrl": file_url,
            "fileName": original_name,
            "extension": "docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

    # 5. Presentation Slides (PPTX, PPT, ODP)
    if ext in [".pptx", ".ppt", ".odp"]:
        buffer = await load_bytes_fn()
        slides_payload = pptx_to_faithful_slides(buffer)
        return {
            "kind": "slides",
            "slides": slides_payload["slides"],
            "totalSlides": slides_payload["totalSlides"],
            "aspectRatio": slides_payload["aspectRatio"],
            "fileUrl": file_url,
            "fileName": original_name,
            "extension": ext.lstrip("."),
            "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }

    # 6. Fallback
    return {
        "kind": "unsupported",
        "fileUrl": file_url,
        "fileName": original_name,
        "extension": ext.lstrip("."),
        "reason": f"File '{original_name}' ({ext.upper()}) can be viewed by downloading directly.",
    }
