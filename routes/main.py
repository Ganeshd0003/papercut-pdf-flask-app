from flask import Blueprint, render_template, current_app

main_bp = Blueprint("main", __name__)

# Metadata that drives both the homepage tool grid and the /tools/<slug> router.
TOOLS = [
    {"slug": "merge", "name": "Merge PDF", "icon": "layers", "desc": "Combine PDFs in the order you want.", "category": "organize"},
    {"slug": "split", "name": "Split PDF", "icon": "scissors", "desc": "Pull specific pages into a new file.", "category": "organize"},
    {"slug": "compress", "name": "Compress PDF", "icon": "minimize-2", "desc": "Shrink file size, keep quality.", "category": "optimize"},
    {"slug": "pdf-to-word", "name": "PDF to Word", "icon": "file-text", "desc": "Convert PDF to editable DOCX.", "category": "convert"},
    {"slug": "word-to-pdf", "name": "Word to PDF", "icon": "file", "desc": "Turn DOCX into a polished PDF.", "category": "convert"},
    {"slug": "pdf-to-jpg", "name": "PDF to JPG", "icon": "image", "desc": "Export every page as an image.", "category": "convert"},
    {"slug": "jpg-to-pdf", "name": "JPG to PDF", "icon": "file-plus", "desc": "Combine images into one PDF.", "category": "convert"},
    {"slug": "rotate", "name": "Rotate PDF", "icon": "rotate-cw", "desc": "Fix sideways or upside-down pages.", "category": "organize"},
    {"slug": "watermark", "name": "Watermark PDF", "icon": "droplet", "desc": "Stamp text across every page.", "category": "edit"},
    {"slug": "page-numbers", "name": "Add Page Numbers", "icon": "hash", "desc": "Number pages automatically.", "category": "edit"},
    {"slug": "protect", "name": "Protect PDF", "icon": "lock", "desc": "Add a password to a PDF.", "category": "security"},
    {"slug": "unlock", "name": "Unlock PDF", "icon": "unlock", "desc": "Remove a known password.", "category": "security"},
    {"slug": "organize", "name": "Organize Pages", "icon": "grid", "desc": "Drag and drop to reorder pages.", "category": "organize"},
    {"slug": "delete-pages", "name": "Delete Pages", "icon": "trash-2", "desc": "Remove unwanted pages.", "category": "organize"},
    {"slug": "extract-pages", "name": "Extract Pages", "icon": "download", "desc": "Save specific pages as a new PDF.", "category": "organize"},
    {"slug": "ocr", "name": "OCR PDF", "icon": "search", "desc": "Make scanned PDFs searchable.", "category": "optimize"},
]

FAQS = [
    ("Is my file kept private?", "Yes. Files are processed on the server and automatically deleted after a short retention window — see our cleanup policy in Settings."),
    ("Do I need an account?", "Most tools work without signing in. Create a free account to keep processing history and download files later."),
    ("What's the file size limit?", "Free accounts can upload files up to 100MB per request. Paid plans raise this limit."),
    ("Which file formats are supported?", "PDF, JPG, PNG, and DOCX are supported depending on the tool."),
]


@main_bp.route("/")
def index():
    return render_template("index.html", tools=TOOLS, app_name=current_app.config["APP_NAME"],
                            tagline=current_app.config["APP_TAGLINE"], faqs=FAQS)


@main_bp.route("/pricing")
def pricing():
    plans = [
        {"name": "Free", "price": "$0", "features": ["5 tasks / day", "100MB max file size", "Standard processing speed"]},
        {"name": "Pro", "price": "$9/mo", "features": ["Unlimited tasks", "500MB max file size", "Priority processing", "No watermark on exports"]},
        {"name": "Business", "price": "$29/mo", "features": ["Everything in Pro", "Team seats", "API access", "Priority support"]},
    ]
    return render_template("pricing.html", plans=plans)


@main_bp.route("/faq")
def faq():
    return render_template("faq.html", faqs=FAQS)
