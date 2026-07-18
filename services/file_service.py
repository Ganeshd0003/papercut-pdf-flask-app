"""
Wraps upload validation + saving + ProcessingJob bookkeeping so route
handlers stay short. This is where security checks #1-5 from the brief
(file size, MIME type, secure filenames) actually get enforced.
"""
import os
from datetime import datetime, timedelta
from flask import current_app
from flask_login import current_user

from extensions import db
from models import ProcessingJob
from utils import allowed_extension, sniff_mime, make_safe_unique_filename


class UploadError(Exception):
    pass


def save_upload(file_storage, allowed_exts: set) -> str:
    """Validates extension + real MIME signature, then saves to UPLOAD_FOLDER.
    Returns the absolute path of the saved file."""
    if not file_storage or file_storage.filename == "":
        raise UploadError("No file selected.")

    if not allowed_extension(file_storage.filename, allowed_exts):
        raise UploadError(f"File type not allowed: {file_storage.filename}")

    mime = sniff_mime(file_storage)
    valid_mimes = {"application/pdf", "image/jpeg", "image/png", "application/zip"}
    if mime not in valid_mimes:
        raise UploadError("File content does not match a supported file type.")

    safe_name = make_safe_unique_filename(file_storage.filename)
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)
    file_storage.save(dest)
    return dest


def create_job(tool: str, input_filenames: list[str]) -> ProcessingJob:
    job = ProcessingJob(
        user_id=current_user.id if current_user.is_authenticated else None,
        tool=tool,
        input_filenames=", ".join(input_filenames),
        status="pending",
    )
    db.session.add(job)
    db.session.commit()
    return job


def complete_job(job: ProcessingJob, output_path: str) -> None:
    retention = current_app.config["FILE_RETENTION_MINUTES"]
    job.status = "success"
    job.output_path = output_path
    job.output_filename = os.path.basename(output_path)
    job.file_size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else None
    job.expires_at = datetime.utcnow() + timedelta(minutes=retention)
    db.session.commit()


def fail_job(job: ProcessingJob, error_message: str) -> None:
    job.status = "failed"
    job.error_message = error_message[:500]
    db.session.commit()
