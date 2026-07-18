"""
Application configuration.
Reads sensitive values from environment variables (.env supported via python-dotenv).
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production-please")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- File storage ---
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    PROCESSED_FOLDER = os.path.join(basedir, "processed")
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB hard cap per request
    ALLOWED_EXTENSIONS = {
        "pdf", "jpg", "jpeg", "png", "docx", "doc"
    }
    # How long a processed/uploaded file is kept before the cleanup job deletes it
    FILE_RETENTION_MINUTES = int(os.environ.get("FILE_RETENTION_MINUTES", 60))

    # --- Security ---
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # --- Branding (change freely, this is YOUR app, not a copy of anyone else's) ---
    APP_NAME = os.environ.get("APP_NAME", "PaperCut PDF")
    APP_TAGLINE = "Every PDF tool you need, in one clean workspace."

    # --- Third-party binaries ---
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD")  # e.g. /usr/bin/tesseract
    POPPLER_PATH = os.environ.get("POPPLER_PATH")    # needed by pdf2image on Windows


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
