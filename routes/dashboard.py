from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from extensions import db
from forms import ProfileForm, ChangePasswordForm
from models import ProcessingJob

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def home():
    recent_jobs = (ProcessingJob.query.filter_by(user_id=current_user.id)
                   .order_by(ProcessingJob.created_at.desc()).limit(5).all())
    total_jobs = ProcessingJob.query.filter_by(user_id=current_user.id).count()
    return render_template("dashboard/home.html", recent_jobs=recent_jobs, total_jobs=total_jobs)


@dashboard_bp.route("/history")
@login_required
def history():
    jobs = (ProcessingJob.query.filter_by(user_id=current_user.id)
            .order_by(ProcessingJob.created_at.desc()).all())
    return render_template("dashboard/history.html", jobs=jobs)


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("dashboard.profile"))
    return render_template("dashboard/profile.html", form=form, password_form=password_form)


@dashboard_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password updated.", "success")
    else:
        flash("Please correct the errors and try again.", "danger")
    return redirect(url_for("dashboard.profile"))


@dashboard_bp.route("/subscription")
@login_required
def subscription():
    return render_template("dashboard/subscription.html")
