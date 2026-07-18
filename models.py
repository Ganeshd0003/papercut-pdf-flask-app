"""
SQLAlchemy models: User, ProcessingJob (history), and a lightweight
Subscription record. Kept intentionally simple — swap SQLite for
PostgreSQL by changing DATABASE_URL only, no code changes needed.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    plan = db.Column(db.String(20), default="free", nullable=False)  # free | pro | business
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    jobs = db.relationship("ProcessingJob", backref="user", lazy="dynamic",
                            cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # Flask-Login expects is_active as a property/attribute
    @property
    def is_active(self):
        return self.is_active_account

    def __repr__(self):
        return f"<User {self.email}>"


class ProcessingJob(db.Model):
    """One row per tool run — powers 'Processing history' and 'Download history'."""
    __tablename__ = "processing_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # nullable: guest usage
    tool = db.Column(db.String(50), nullable=False)          # e.g. "merge", "compress"
    input_filenames = db.Column(db.Text, nullable=False)      # comma-separated original names
    output_filename = db.Column(db.String(255), nullable=True)
    output_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default="pending")      # pending|success|failed
    error_message = db.Column(db.Text, nullable=True)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)         # auto-delete cutoff
    downloaded_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Job {self.tool} status={self.status}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
