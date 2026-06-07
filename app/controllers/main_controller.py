from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.repositories import DatasetRepository

main_bp = Blueprint("main", __name__, url_prefix="/main")

@main_bp.route("/", methods=["GET"])
@login_required
def index():
    has_data = DatasetRepository.has_data()
    return render_template("main/index.html", has_data=has_data)
