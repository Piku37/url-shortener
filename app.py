"""
URL Shortener Application
Main Flask application file
"""

import os
import io
import string
import random
import logging
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, jsonify,
    send_from_directory, send_file, url_for
)
from flask_sqlalchemy import SQLAlchemy
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask  # "cool" look
from PIL import Image

# ------------- Config & App init -------------
os.makedirs("data", exist_ok=True)

app = Flask(__name__)

default_sqlite_path = "sqlite:///data/urls.db"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", default_sqlite_path)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy(app)

# ============================================
# DATABASE MODELS
# ============================================
class URL(db.Model):
    __tablename__ = "url"   # <-- add this
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    clicks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())
    clicks_rel = db.relationship("Click", backref="url", cascade="all, delete-orphan")
    def __repr__(self):
        return f"<URL {self.short_code}>"

class Click(db.Model):
    __tablename__ = "click"  # <-- add this
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey("url.id"), nullable=False)  # <-- fix FK
    clicked_at = db.Column(db.DateTime, default=db.func.now())
    ip = db.Column(db.String(64))
    user_agent = db.Column(db.String(512))
    referrer = db.Column(db.String(512))
    def __repr__(self):
        return f"<Click {self.url_id} at {self.clicked_at}>"

# ============================================
# HELPERS
# ============================================
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        code = "".join(random.choices(characters, k=length))
        if not URL.query.filter_by(short_code=code).first():
            return code

def is_valid_url(url):
    return url.startswith(("http://", "https://"))

def get_base_url():
    return request.host_url.rstrip("/")

def client_ip():
    # honor proxies if any
    fwd = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return fwd or request.remote_addr or ""

# ============================================
# ROUTES
# ============================================
@app.route("/")
def home():
    return render_template("index.html")

# Serve favicon so it doesn't hit the catch-all short_code route
@app.route("/favicon.ico")
def favicon():
    fav_dir = os.path.join(app.root_path, "static")
    fav_path = os.path.join(fav_dir, "favicon.ico")
    if os.path.exists(fav_path):
        return send_from_directory(fav_dir, "favicon.ico")
    return "", 204

@app.route("/shorten", methods=["POST"])
def shorten_url():
    try:
        data = request.get_json() if request.is_json else request.form
        original_url = (data.get("url") or "").strip()

        if not original_url:
            return jsonify({"error": "URL is required"}), 400
        if not is_valid_url(original_url):
            return jsonify({"error": "Invalid URL. Must start with http:// or https://"}), 400

        short_code = generate_short_code()
        new_url = URL(original_url=original_url, short_code=short_code)
        db.session.add(new_url)
        db.session.commit()

        short_url = f"{get_base_url()}/{short_code}"

        return jsonify(
            {
                "success": True,
                "short_url": short_url,
                "short_code": short_code,
                "original_url": original_url,
                "qr_url": url_for("qr_code", short_code=short_code),
                "stats_url": url_for("get_stats", short_code=short_code),
            }
        )
    except Exception as e:
        logger.exception("Error while shortening URL")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/<short_code>")
def redirect_to_url(short_code):
    url_entry = URL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return render_template("404.html", short_code=short_code), 404

    # record analytics
    try:
        click = Click(
            url_id=url_entry.id,
            ip=client_ip(),
            user_agent=(request.headers.get("User-Agent") or "")[:512],
            referrer=(request.referrer or "")[:512],
        )
        url_entry.clicks = (url_entry.clicks or 0) + 1
        db.session.add(click)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return redirect(url_entry.original_url)

@app.route("/stats/<short_code>")
def get_stats(short_code):
    url_entry = URL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({"error": "URL not found"}), 404

    last_click = (
        Click.query.filter_by(url_id=url_entry.id)
        .order_by(Click.clicked_at.desc())
        .first()
    )
    return jsonify(
        {
            "short_code": url_entry.short_code,
            "original_url": url_entry.original_url,
            "clicks": url_entry.clicks,
            "created_at": url_entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_click_at": last_click.clicked_at.strftime("%Y-%m-%d %H:%M:%S") if last_click else None,
        }
    )

# ---------- QR Code (cool style) ----------
@app.route("/qr/<short_code>")
def qr_code(short_code):
    url_entry = URL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({"error": "URL not found"}), 404

    short_url = f"{get_base_url()}/{short_code}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # good balance
        box_size=12,
        border=2,
    )
    qr.add_data(short_url)
    qr.make(fit=True)

    # Styled image: rounded modules + radial gradient (purple → blue)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=RadialGradiantColorMask(
            center_color=(118, 75, 162),  # #764ba2
            edge_color=(102, 126, 234),   # #667eea
        ),
        back_color="white",
    )

    # Optional: small white border to help scanners
    if isinstance(img, Image.Image):
        pass
    else:
        img = img.get_image()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=False, download_name=f"{short_code}.png")

# ---------- Dashboard (list + delete) ----------
@app.route("/dashboard")
def dashboard():
    urls = URL.query.order_by(URL.created_at.desc()).all()
    total_urls = len(urls)
    total_clicks = sum(u.clicks or 0 for u in urls)
    return render_template("dashboard.html", urls=urls, total_urls=total_urls, total_clicks=total_clicks)

@app.route("/delete/<int:url_id>", methods=["POST"])
def delete_url(url_id):
    url_entry = URL.query.get(url_id)
    if not url_entry:
        return jsonify({"error": "Not found"}), 404
    try:
        db.session.delete(url_entry)  # cascades to clicks
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    # if request is AJAX, return json; if form post, redirect
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})
    return redirect(url_for("dashboard"))

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200

# ============================================
# DB initialization (works under Gunicorn/Docker)
# ============================================
def init_db():
    with app.app_context():
        db.create_all()
        logger.info("Database initialized (tables created if missing).")

with app.app_context():
    db.create_all()

# ============================================
# Run (only direct)
# ============================================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
