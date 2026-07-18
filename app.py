"""
Application factory. Run with:  python app.py   (dev)
or:  gunicorn "app:create_app()"                 (prod)
"""
import os
import logging
import threading
import time
import click
from flask import Flask, render_template

from config import config_by_name
from extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

    _configure_logging(app)

    # --- extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # --- blueprints ---
    from routes import all_blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    # --- models (import after db.init_app so tables register) ---
    with app.app_context():
        import models  # noqa: F401
        db.create_all()

    _register_error_handlers(app)
    _register_cli(app)
    _register_context_processors(app)

    if not app.config.get("TESTING"):
        _start_cleanup_thread(app)

    return app


def _configure_logging(app):
    logger = logging.getLogger("pdf_app")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        logging.getLogger("pdf_app").exception("Unhandled server error")
        return render_template("errors/500.html"), 500


def _register_context_processors(app):
    @app.context_processor
    def inject_globals():
        return {"app_name": app.config["APP_NAME"], "app_tagline": app.config["APP_TAGLINE"]}


def _register_cli(app):
    @app.cli.command("make-admin")
    @click.argument("email")
    def make_admin(email):
        """Usage: flask make-admin someone@example.com"""
        from models import User
        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user:
            click.echo(f"No user found with email {email}")
            return
        user.is_admin = True
        db.session.commit()
        click.echo(f"{email} is now an admin.")


def _start_cleanup_thread(app):
    """Background thread that periodically deletes expired uploaded/processed files.
    For production, prefer a real scheduler (cron + `flask cleanup`) over an in-process
    thread, but this keeps the demo self-contained."""
    from utils import cleanup_expired_files

    def loop():
        while True:
            try:
                cleanup_expired_files(app, db)
            except Exception:
                logging.getLogger("pdf_app").exception("Cleanup job failed")
            time.sleep(300)  # every 5 minutes

    t = threading.Thread(target=loop, daemon=True)
    t.start()


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False), host="0.0.0.0", port=5000)