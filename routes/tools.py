"""
Every PDF/image tool lives behind one blueprint. Each tool has:
  GET  /tools/<slug>          -> renders the upload page (tools/<slug>.html)
  POST /tools/<slug>/process  -> AJAX endpoint, returns JSON {ok, download_url, error}

Uploaded files are validated + saved via services.file_service, processed
via services.pdf_service, and every run is logged as a ProcessingJob so it
shows up in the user's dashboard history.
"""
import os
import uuid
import logging
from flask import (
    Blueprint, render_template, request, jsonify, send_from_directory,
    current_app, abort
)
from flask_login import current_user

from extensions import limiter
from forms import (
    MultiPDFUploadForm, SinglePDFUploadForm, SplitForm, CompressForm, RotateForm,
    WatermarkForm, PageNumbersForm, ProtectForm, UnlockForm, ExtractDeleteForm,
    ImageToPDFForm, OCRForm,
)
from services.file_service import save_upload, create_job, complete_job, fail_job, UploadError
from services import pdf_service
from services.pdf_service import PDFServiceError
from models import ProcessingJob
from utils import parse_page_ranges

tools_bp = Blueprint("tools", __name__, url_prefix="/tools")
logger = logging.getLogger("pdf_app")

PDF_EXT = {"pdf"}
IMG_EXT = {"jpg", "jpeg", "png"}
DOC_EXT = {"docx", "doc"}


def _output_path(suffix: str) -> str:
    name = f"{uuid.uuid4().hex[:12]}_{suffix}"
    return os.path.join(current_app.config["PROCESSED_FOLDER"], name)


def _job_response(job: ProcessingJob, ok: bool, error: str | None = None):
    if ok:
        return jsonify({
            "ok": True,
            "download_url": f"/tools/download/{job.id}",
            "filename": job.output_filename,
        })
    return jsonify({"ok": False, "error": error or "Processing failed."}), 400


# ---------------------------------------------------------------- page renderers
@tools_bp.route("/<slug>")
def tool_page(slug):
    forms = {
        "merge": MultiPDFUploadForm(), "split": SplitForm(), "compress": CompressForm(),
        "rotate": RotateForm(), "watermark": WatermarkForm(), "page-numbers": PageNumbersForm(),
        "protect": ProtectForm(), "unlock": UnlockForm(), "extract-pages": ExtractDeleteForm(),
        "delete-pages": ExtractDeleteForm(), "organize": SinglePDFUploadForm(),
        "pdf-to-jpg": SinglePDFUploadForm(), "jpg-to-pdf": ImageToPDFForm(),
        "pdf-to-word": SinglePDFUploadForm(), "word-to-pdf": SinglePDFUploadForm(),
        "ocr": OCRForm(),
    }
    form = forms.get(slug)
    if form is None:
        abort(404)
    return render_template("tools/generic_tool.html", slug=slug, form=form, slug_name=slug)


# ---------------------------------------------------------------- processing endpoints
@tools_bp.route("/merge/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_merge():
    files = request.files.getlist("files")
    job = create_job("merge", [f.filename for f in files])
    try:
        if len(files) < 2:
            raise UploadError("Select at least two PDF files.")
        saved = [save_upload(f, PDF_EXT) for f in files]
        out = _output_path("merged.pdf")
        pdf_service.merge_pdfs(saved, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("merge failed")
        fail_job(job, "Unexpected error during merge.")
        return _job_response(job, False, "Unexpected error during merge.")


@tools_bp.route("/split/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_split():
    file = request.files.get("file")
    ranges = request.form.get("ranges", "")
    job = create_job("split", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        page_count = pdf_service.get_page_count(saved)
        indices = parse_page_ranges(ranges, page_count)
        out = _output_path("split.pdf")
        pdf_service.split_pdf(saved, indices, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError, ValueError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("split failed")
        fail_job(job, "Unexpected error during split.")
        return _job_response(job, False, "Unexpected error during split.")


@tools_bp.route("/compress/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_compress():
    file = request.files.get("file")
    quality = request.form.get("quality", "medium")
    job = create_job("compress", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        out = _output_path("compressed.pdf")
        pdf_service.compress_pdf(saved, out, quality)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("compress failed")
        fail_job(job, "Unexpected error during compression.")
        return _job_response(job, False, "Unexpected error during compression.")


@tools_bp.route("/rotate/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_rotate():
    file = request.files.get("file")
    angle = int(request.form.get("angle", 90))
    job = create_job("rotate", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        out = _output_path("rotated.pdf")
        pdf_service.rotate_pdf(saved, out, angle)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("rotate failed")
        fail_job(job, "Unexpected error during rotation.")
        return _job_response(job, False, "Unexpected error during rotation.")


@tools_bp.route("/watermark/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_watermark():
    file = request.files.get("file")
    text = request.form.get("text", "").strip()
    opacity = int(request.form.get("opacity", 30))
    job = create_job("watermark", [file.filename if file else "unknown"])
    try:
        if not text:
            raise UploadError("Watermark text is required.")
        saved = save_upload(file, PDF_EXT)
        out = _output_path("watermarked.pdf")
        pdf_service.add_watermark(saved, out, text, opacity)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("watermark failed")
        fail_job(job, "Unexpected error during watermarking.")
        return _job_response(job, False, "Unexpected error during watermarking.")


@tools_bp.route("/page-numbers/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_page_numbers():
    file = request.files.get("file")
    position = request.form.get("position", "bottom-center")
    start_number = int(request.form.get("start_number", 1))
    job = create_job("page-numbers", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        out = _output_path("numbered.pdf")
        pdf_service.add_page_numbers(saved, out, position, start_number)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("page-numbers failed")
        fail_job(job, "Unexpected error while numbering pages.")
        return _job_response(job, False, "Unexpected error while numbering pages.")


@tools_bp.route("/protect/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_protect():
    file = request.files.get("file")
    password = request.form.get("password", "")
    job = create_job("protect", [file.filename if file else "unknown"])
    try:
        if len(password) < 4:
            raise UploadError("Password must be at least 4 characters.")
        saved = save_upload(file, PDF_EXT)
        out = _output_path("protected.pdf")
        pdf_service.protect_pdf(saved, out, password)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("protect failed")
        fail_job(job, "Unexpected error while protecting file.")
        return _job_response(job, False, "Unexpected error while protecting file.")


@tools_bp.route("/unlock/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_unlock():
    file = request.files.get("file")
    password = request.form.get("password", "")
    job = create_job("unlock", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        out = _output_path("unlocked.pdf")
        pdf_service.unlock_pdf(saved, out, password)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("unlock failed")
        fail_job(job, "Unexpected error while unlocking file.")
        return _job_response(job, False, "Unexpected error while unlocking file.")


@tools_bp.route("/extract-pages/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_extract_pages():
    file = request.files.get("file")
    pages = request.form.get("pages", "")
    job = create_job("extract-pages", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        page_count = pdf_service.get_page_count(saved)
        indices = parse_page_ranges(pages, page_count)
        out = _output_path("extracted.pdf")
        pdf_service.extract_pages(saved, indices, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError, ValueError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("extract-pages failed")
        fail_job(job, "Unexpected error while extracting pages.")
        return _job_response(job, False, "Unexpected error while extracting pages.")


@tools_bp.route("/delete-pages/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_delete_pages():
    file = request.files.get("file")
    pages = request.form.get("pages", "")
    job = create_job("delete-pages", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        page_count = pdf_service.get_page_count(saved)
        indices = parse_page_ranges(pages, page_count)
        out = _output_path("deleted_pages.pdf")
        pdf_service.delete_pages(saved, indices, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError, ValueError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("delete-pages failed")
        fail_job(job, "Unexpected error while deleting pages.")
        return _job_response(job, False, "Unexpected error while deleting pages.")


@tools_bp.route("/organize/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_organize():
    """new_order comes from the drag-and-drop UI as a comma-separated 1-indexed list."""
    file = request.files.get("file")
    order_raw = request.form.get("order", "")
    job = create_job("organize", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        try:
            new_order = [int(x) - 1 for x in order_raw.split(",") if x.strip() != ""]
        except ValueError:
            raise UploadError("Invalid page order.")
        out = _output_path("organized.pdf")
        pdf_service.organize_pages(saved, new_order, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("organize failed")
        fail_job(job, "Unexpected error while reordering pages.")
        return _job_response(job, False, "Unexpected error while reordering pages.")


@tools_bp.route("/pdf-to-jpg/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_pdf_to_jpg():
    """Returns a zip if multi-page, or the single JPG if one page."""
    import zipfile
    file = request.files.get("file")
    job = create_job("pdf-to-jpg", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        base = uuid.uuid4().hex[:12]
        images = pdf_service.pdf_to_jpg(saved, current_app.config["PROCESSED_FOLDER"], base)
        if len(images) == 1:
            out = images[0]
        else:
            out = _output_path("pages.zip")
            with zipfile.ZipFile(out, "w") as zf:
                for img in images:
                    zf.write(img, os.path.basename(img))
                    os.remove(img)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("pdf-to-jpg failed")
        fail_job(job, "Unexpected error during conversion.")
        return _job_response(job, False, "Unexpected error during conversion.")


@tools_bp.route("/jpg-to-pdf/process", methods=["POST"])
@limiter.limit("30 per hour")
def process_jpg_to_pdf():
    files = request.files.getlist("files")
    job = create_job("jpg-to-pdf", [f.filename for f in files])
    try:
        if not files:
            raise UploadError("Select at least one image.")
        saved = [save_upload(f, IMG_EXT) for f in files]
        out = _output_path("images.pdf")
        pdf_service.images_to_pdf(saved, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("jpg-to-pdf failed")
        fail_job(job, "Unexpected error during conversion.")
        return _job_response(job, False, "Unexpected error during conversion.")


@tools_bp.route("/pdf-to-word/process", methods=["POST"])
@limiter.limit("20 per hour")
def process_pdf_to_word():
    file = request.files.get("file")
    job = create_job("pdf-to-word", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        out = _output_path("converted.docx")
        pdf_service.pdf_to_word(saved, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("pdf-to-word failed")
        fail_job(job, "Unexpected error during conversion.")
        return _job_response(job, False, "Unexpected error during conversion.")


@tools_bp.route("/word-to-pdf/process", methods=["POST"])
@limiter.limit("20 per hour")
def process_word_to_pdf():
    file = request.files.get("file")
    job = create_job("word-to-pdf", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, DOC_EXT)
        out = _output_path("converted.pdf")
        pdf_service.word_to_pdf(saved, out)
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("word-to-pdf failed")
        fail_job(job, "Unexpected error during conversion.")
        return _job_response(job, False, "Unexpected error during conversion.")


@tools_bp.route("/ocr/process", methods=["POST"])
@limiter.limit("15 per hour")
def process_ocr():
    file = request.files.get("file")
    language = request.form.get("language", "eng")
    job = create_job("ocr", [file.filename if file else "unknown"])
    try:
        saved = save_upload(file, PDF_EXT)
        out = _output_path("ocr.pdf")
        pdf_service.ocr_pdf(saved, out, language, current_app.config.get("TESSERACT_CMD"))
        complete_job(job, out)
        return _job_response(job, True)
    except (UploadError, PDFServiceError) as e:
        fail_job(job, str(e))
        return _job_response(job, False, str(e))
    except Exception:
        logger.exception("ocr failed")
        fail_job(job, "OCR failed — ensure Tesseract is installed on the server.")
        return _job_response(job, False, "OCR failed — ensure Tesseract is installed on the server.")


@tools_bp.route("/organize/page-count", methods=["POST"])
@limiter.limit("30 per hour")
def organize_page_count():
    """Returns the page count of an uploaded PDF so the UI can render draggable page chips."""
    file = request.files.get("file")
    try:
        saved = save_upload(file, PDF_EXT)
        count = pdf_service.get_page_count(saved)
        return jsonify({"ok": True, "page_count": count, "temp_name": os.path.basename(saved)})
    except (UploadError, PDFServiceError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------------------------------------------------------------- download
@tools_bp.route("/download/<int:job_id>")
def download(job_id):
    job = ProcessingJob.query.get_or_404(job_id)
    if not job.output_path or not os.path.exists(job.output_path):
        abort(404, description="File has expired or was already removed.")
    job.downloaded_count = (job.downloaded_count or 0) + 1
    from extensions import db
    db.session.commit()
    directory, filename = os.path.split(job.output_path)
    return send_from_directory(directory, filename, as_attachment=True,
                                download_name=job.output_filename)
