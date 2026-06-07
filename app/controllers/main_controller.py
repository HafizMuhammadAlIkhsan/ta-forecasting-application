from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.services import UploadService
from app.repositories import DatasetRepository

main_bp = Blueprint("main", __name__, url_prefix="/main")

@main_bp.route("/", methods=["GET"])
@login_required
def index():
    has_data = DatasetRepository.has_data()
    return render_template("main/index.html", has_data=has_data)

@main_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    if "file" not in request.files or request.files["file"].filename == "":
        flash("Tidak ada file yang dipilih.", "danger")
        return redirect(url_for("main.index"))

    success, message = UploadService.validate_and_save(request.files["file"])
    flash(message, "success" if success else "danger")
    return redirect(url_for("main.index"))