"""
Shared utility helpers: filename safety, MIME sniffing, page-range parsing,
and the background cleanup job that auto-deletes old files.
"""
import os
import re
import uuid
import logging
import mimetypes
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

logger = logging.getLogger("pdf_app")

# Real MIME sniffing (not just trusting the extension) using file signatures.
MAGIC_BYTES = {
    b"%PDF": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"PK\x03\x04": "application/zip",  # docx is a zip container
}


def allowed_extension(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def sniff_mime(file_storage) -> str | None:
    """Read the first bytes of an uploaded file to verify its real type."""
    pos = file_storage.stream.tell()
    header = file_storage.stream.read(16)
    file_storage.stream.seek(pos)
    for magic, mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            return mime
    return None


def make_safe_unique_filename(original_filename: str) -> str:
    """secure_filename() strips dangerous chars; we prefix a UUID to prevent collisions
    and directory traversal / overwrite attacks."""
    safe = secure_filename(original_filename) or "file"
    unique_prefix = uuid.uuid4().hex[:12]
    return f"{unique_prefix}_{safe}"


def parse_page_ranges(spec: str, max_pages: int) -> list[int]:
    """Parse '1-3,5,7-9' into a sorted, de-duplicated 0-indexed page list, bounds-checked."""
    pages = set()
    spec = spec.strip()
    if not spec:
        raise ValueError("No pages specified")
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
            if not m:
                raise ValueError(f"Invalid range: '{part}'")
            start, end = int(m.group(1)), int(m.group(2))
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid page number: '{part}'")
            start = end = int(part)
        if start < 1 or end > max_pages or start > end:
            raise ValueError(f"Range '{part}' is out of bounds (document has {max_pages} pages)")
        pages.update(range(start - 1, end))
    return sorted(pages)


def cleanup_expired_files(app, db):
    """
    Deletes files whose retention window has passed. Intended to be called
    periodically (see app.py's background scheduler thread).
    Requirement #21: 'Auto-delete uploaded files after processing'.
    """
    from models import ProcessingJob

    with app.app_context():
        cutoff = datetime.utcnow()
        expired_jobs = ProcessingJob.query.filter(
            ProcessingJob.expires_at.isnot(None),
            ProcessingJob.expires_at < cutoff,
            ProcessingJob.status == "success",
        ).all()

        removed = 0
        for job in expired_jobs:
            if job.output_path and os.path.exists(job.output_path):
                try:
                    os.remove(job.output_path)
                    removed += 1
                except OSError as e:
                    logger.warning("Could not delete %s: %s", job.output_path, e)
            job.output_path = None
            job.status = "expired"
        db.session.commit()

        # Also sweep orphaned files in uploads/ older than retention window
        retention = timedelta(minutes=app.config["FILE_RETENTION_MINUTES"])
        for folder in (app.config["UPLOAD_FOLDER"], app.config["PROCESSED_FOLDER"]):
            if not os.path.isdir(folder):
                continue
            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                if fname == ".gitkeep":
                    continue
                try:
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(fpath))
                    if datetime.utcnow() - mtime > retention:
                        os.remove(fpath)
                        removed += 1
                except OSError:
                    continue
        if removed:
            logger.info("Cleanup job removed %d expired file(s)", removed)
