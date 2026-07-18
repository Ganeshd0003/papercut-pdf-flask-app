"""
Admin panel. Every route here is protected by @admin_required, which
checks current_user.is_admin (set directly in the DB or via the CLI
command `flask make-admin <email>` defined in app.py).
"""
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user

from extensions import db
from models import User, ProcessingJob

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/")
@admin_required
def dashboard():
    total_users = User.query.count()
    total_jobs = ProcessingJob.query.count()
    failed_jobs = ProcessingJob.query.filter_by(status="failed").count()
    since = datetime.utcnow() - timedelta(days=7)
    jobs_last_7d = ProcessingJob.query.filter(ProcessingJob.created_at >= since).count()
    recent_jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).limit(10).all()
    return render_template(
        "admin/dashboard.html", total_users=total_users, total_jobs=total_jobs,
        failed_jobs=failed_jobs, jobs_last_7d=jobs_last_7d, recent_jobs=recent_jobs,
    )


@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You can't disable your own account.", "warning")
    else:
        user.is_active_account = not user.is_active_account
        db.session.commit()
        flash(f"{user.email} is now {'active' if user.is_active_account else 'disabled'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/files")
@admin_required
def files():
    jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).limit(200).all()
    return render_template("admin/files.html", jobs=jobs)


@admin_bp.route("/analytics")
@admin_required
def analytics():
    tool_counts = (
        db.session.query(ProcessingJob.tool, db.func.count(ProcessingJob.id))
        .group_by(ProcessingJob.tool)
        .order_by(db.func.count(ProcessingJob.id).desc())
        .all()
    )
    return render_template("admin/analytics.html", tool_counts=tool_counts)


@admin_bp.route("/settings")
@admin_required
def settings():
    from flask import current_app
    return render_template("admin/settings.html", config=current_app.config)
