from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.services import AuthService
from app.repositories import DatasetRepository
from app import db, mail, login_manager
from app.models import User
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import secrets, random

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return User.query.get(int(user_id))


@auth_bp.route("/", methods=["GET"])
def root():
    if current_user.is_authenticated:
        if not DatasetRepository.has_data():
            return redirect(url_for("forecast.index"))
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))   

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if not DatasetRepository.has_data():
            return redirect(url_for("forecast.index"))
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = AuthService.authenticate(email, password)
        if user:
            login_user(user)
            if not DatasetRepository.has_data():
                return redirect(url_for("forecast.index"))
            return redirect(url_for("dashboard.index"))

        flash("Login Error, Email atau password salah.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = AuthService.get_user_by_email(email)

        if not user:
            flash("Email tidak ditemukan.", "danger")
            return redirect(url_for("auth.forgot_password"))

        serializer = current_app.serializer
        token = serializer.dumps(email, salt="reset-password")

        reset_link = url_for("auth.reset_password_token", token=token, _external=True)

        msg = Message(
            subject="Reset Password",
            recipients=[email]
        )

        msg.body = f"""
        Klik link berikut untuk reset password:

        {reset_link}

        Link ini berlaku selama 30 menit.
        """

        mail.send(msg)

        flash("Link reset password sudah dikirim ke email.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot-password.html")

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_token(token):

    try:
        serializer = current_app.serializer
        email = serializer.loads(token, salt="reset-password", max_age=1800)  # 30 menit
    except SignatureExpired:
        flash("Link reset sudah expired.", "error")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("Link tidak valid.", "error")
        return redirect(url_for("auth.forgot_password"))

    user = AuthService.get_user_by_email(email)

    if not user:
        flash("User tidak ditemukan.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Password tidak cocok.", "error")
            return redirect(request.url)

        user.password = generate_password_hash(password)
        db.session.commit()

        flash("Password berhasil diubah.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset-password.html")

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
        flash("Konfirmasi password tidak cocok.", "error")
        return redirect(url_for("auth.profile"))

    success, message = AuthService.update_password(current_user, current_pw, new_pw)
    flash(message, "success" if success else "error")
    return redirect(url_for("auth.profile"))
