"""
All actual PDF manipulation lives here, kept separate from Flask routes
so it's independently testable and reusable.

Libraries used deliberately per task (each is best-in-class for that job):
  - PyMuPDF (fitz): rendering, rasterizing, watermarking, page ops, compression
  - pikepdf (qpdf bindings): encryption/decryption, linearization
  - pypdf: lightweight merge/split fallback, metadata
  - reportlab: generating overlay content (page numbers, watermark text)
  - Pillow: image <-> PDF conversions
"""
import os
import io
import fitz  # PyMuPDF
import pikepdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


class PDFServiceError(Exception):
    """Raised for any expected, user-facing processing failure."""


def merge_pdfs(input_paths: list[str], output_path: str) -> None:
    if len(input_paths) < 2:
        raise PDFServiceError("Select at least two PDF files to merge.")
    merged = fitz.open()
    try:
        for path in input_paths:
            with fitz.open(path) as doc:
                merged.insert_pdf(doc)
        merged.save(output_path)
    finally:
        merged.close()


def split_pdf(input_path: str, page_indices: list[int], output_path: str) -> None:
    """Extracts the given 0-indexed pages into a single new PDF."""
    with fitz.open(input_path) as doc:
        if any(p >= doc.page_count for p in page_indices):
            raise PDFServiceError("Requested page is out of range.")
        new_doc = fitz.open()
        for p in page_indices:
            new_doc.insert_pdf(doc, from_page=p, to_page=p)
        new_doc.save(output_path)
        new_doc.close()


def compress_pdf(input_path: str, output_path: str, quality: str = "medium") -> None:
    """
    Recompresses embedded images and strips redundant data.
    quality: low (keep quality, light compress) | medium | high (max compression)
    """
    image_quality_map = {"low": 85, "medium": 60, "high": 30}
    jpg_quality = image_quality_map.get(quality, 60)
    zoom_map = {"low": 1.0, "medium": 0.85, "high": 0.6}
    scale = zoom_map.get(quality, 0.85)

    with fitz.open(input_path) as doc:
        for page in doc:
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                try:
                    base = doc.extract_image(xref)
                    pil_img = Image.open(io.BytesIO(base["image"])).convert("RGB")
                    if scale != 1.0:
                        w, h = pil_img.size
                        pil_img = pil_img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=jpg_quality, optimize=True)
                    doc.update_stream(xref, buf.getvalue())
                except Exception:
                    continue  # non-recompressible image (e.g. mask); skip safely
        doc.save(output_path, garbage=4, deflate=True, clean=True)


def rotate_pdf(input_path: str, output_path: str, angle: int) -> None:
    with fitz.open(input_path) as doc:
        for page in doc:
            page.set_rotation((page.rotation + angle) % 360)
        doc.save(output_path)


def add_watermark(input_path: str, output_path: str, text: str, opacity_pct: int = 30) -> None:
    with fitz.open(input_path) as doc:
        opacity = max(0.05, min(1.0, opacity_pct / 100))
        for page in doc:
            rect = page.rect
            page.insert_textbox(
                rect,
                text,
                fontsize=min(rect.width, rect.height) / 10,
                rotate=45,
                color=(0.5, 0.5, 0.5),
                fill_opacity=opacity,
                align=1,
            )
        doc.save(output_path)


def add_page_numbers(input_path: str, output_path: str, position: str = "bottom-center", start: int = 1) -> None:
    with fitz.open(input_path) as doc:
        for i, page in enumerate(doc):
            label = str(start + i)
            rect = page.rect
            margin = 24
            if position == "bottom-center":
                point = fitz.Point(rect.width / 2, rect.height - margin)
            elif position == "bottom-right":
                point = fitz.Point(rect.width - margin, rect.height - margin)
            else:  # top-right
                point = fitz.Point(rect.width - margin, margin)
            page.insert_text(point, label, fontsize=10, color=(0, 0, 0))
        doc.save(output_path)


def protect_pdf(input_path: str, output_path: str, password: str) -> None:
    with pikepdf.open(input_path) as pdf:
        pdf.save(
            output_path,
            encryption=pikepdf.Encryption(owner=password, user=password, R=4),
        )


def unlock_pdf(input_path: str, output_path: str, password: str) -> None:
    try:
        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
    except pikepdf.PasswordError:
        raise PDFServiceError("Incorrect password.")


def extract_pages(input_path: str, page_indices: list[int], output_path: str) -> None:
    split_pdf(input_path, page_indices, output_path)  # same operation


def delete_pages(input_path: str, page_indices: list[int], output_path: str) -> None:
    with fitz.open(input_path) as doc:
        keep = [p for p in range(doc.page_count) if p not in set(page_indices)]
        if not keep:
            raise PDFServiceError("Cannot delete every page in the document.")
        new_doc = fitz.open()
        for p in keep:
            new_doc.insert_pdf(doc, from_page=p, to_page=p)
        new_doc.save(output_path)
        new_doc.close()


def organize_pages(input_path: str, new_order: list[int], output_path: str) -> None:
    """new_order is a 0-indexed permutation of all pages, as chosen via drag & drop in the UI."""
    with fitz.open(input_path) as doc:
        if sorted(new_order) != list(range(doc.page_count)):
            raise PDFServiceError("Page order must include every page exactly once.")
        new_doc = fitz.open()
        for p in new_order:
            new_doc.insert_pdf(doc, from_page=p, to_page=p)
        new_doc.save(output_path)
        new_doc.close()


def pdf_to_jpg(input_path: str, output_dir: str, base_name: str) -> list[str]:
    """Rasterizes each page to a JPG at 150 DPI. Returns list of output file paths."""
    outputs = []
    with fitz.open(input_path) as doc:
        zoom = 150 / 72
        matrix = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_path = os.path.join(output_dir, f"{base_name}_page{i + 1}.jpg")
            pix.save(out_path)
            outputs.append(out_path)
    return outputs


def images_to_pdf(image_paths: list[str], output_path: str) -> None:
    images = [Image.open(p).convert("RGB") for p in image_paths]
    if not images:
        raise PDFServiceError("No images provided.")
    first, rest = images[0], images[1:]
    first.save(output_path, save_all=True, append_images=rest)


def pdf_to_word(input_path: str, output_path: str) -> None:
    """Uses pdf2docx for layout-aware conversion (best-effort; complex layouts may shift)."""
    from pdf2docx import Converter
    cv = Converter(input_path)
    try:
        cv.convert(output_path)
    finally:
        cv.close()


def word_to_pdf(input_path: str, output_path: str) -> None:
    """
    Converts a .docx to PDF. docx2pdf requires MS Word (Windows/Mac).
    On Linux servers, install LibreOffice and use its headless CLI instead.
    """
    import platform
    import subprocess

    if platform.system() in ("Windows", "Darwin"):
        from docx2pdf import convert
        convert(input_path, output_path)
    else:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             "--outdir", os.path.dirname(output_path), input_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise PDFServiceError(
                "Word-to-PDF conversion requires LibreOffice installed on the server "
                "(sudo apt install libreoffice)."
            )
        # LibreOffice names the output after the input file; rename to expected output_path
        produced = os.path.join(
            os.path.dirname(output_path),
            os.path.splitext(os.path.basename(input_path))[0] + ".pdf",
        )
        if produced != output_path and os.path.exists(produced):
            os.replace(produced, output_path)


def ocr_pdf(input_path: str, output_path: str, language: str = "eng", tesseract_cmd: str | None = None) -> None:
    """Adds a searchable text layer using Tesseract via PyMuPDF's OCR integration."""
    import pytesseract
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    with fitz.open(input_path) as doc:
        out = fitz.open()
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang=language)
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(new_page.rect, doc, page.number)
            # Invisible text layer so the page looks the same but becomes searchable/selectable
            new_page.insert_textbox(
                new_page.rect, text, fontsize=1, render_mode=3, color=(1, 1, 1)
            )
        out.save(output_path)
        out.close()


def get_page_count(input_path: str) -> int:
    with fitz.open(input_path) as doc:
        return doc.page_count
