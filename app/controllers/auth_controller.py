from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.services import AuthService
from app.repositories import DatasetRepository
from app import login_manager
from app.models import User

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return User.query.get(int(user_id))


@auth_bp.route("/", methods=["GET"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = AuthService.authenticate(email, password)
        if user:
            login_user(user)
            if not DatasetRepository.has_data():
                return redirect(url_for("main.index"))
            return redirect(url_for("dashboard.index"))

        flash("Login Error: Email atau password salah.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("auth/profile.html")


@auth_bp.route("/profile/update-password", methods=["POST"])
@login_required
def update_password():
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    if new_pw != confirm_pw:
        flash("Konfirmasi password tidak cocok.", "danger")
        return redirect(url_for("auth.profile"))

    success, message = AuthService.update_password(current_user, current_pw, new_pw)
    flash(message, "success" if success else "danger")
    return redirect(url_for("auth.profile"))
