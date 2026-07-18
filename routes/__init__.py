"""Aggregates all blueprints so app.py can import + register them in one line."""
from routes.main import main_bp
from routes.auth import auth_bp
from routes.tools import tools_bp
from routes.dashboard import dashboard_bp
from routes.admin import admin_bp

all_blueprints = (main_bp, auth_bp, tools_bp, dashboard_bp, admin_bp)
