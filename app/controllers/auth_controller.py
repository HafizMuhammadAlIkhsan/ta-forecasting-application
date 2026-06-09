from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.services import AuthService
from app.repositories import DatasetRepository
from app import db, mail, login_manager
from app.models import User
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
from flask import session
import secrets, random

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

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = AuthService.get_user_by_email(email)
        otp = str(random.randint(100000, 999999))
        
        session["reset_email"] = email
        session["reset_otp"] = otp
        
        if not user:
            flash("Email tidak ditemukan.", "danger")
            return redirect(url_for("auth.forgot_password"))

        new_password = secrets.token_urlsafe(8)

        user.password = generate_password_hash(new_password)
        db.session.commit()

        msg = Message(
            subject="Kode Reset Password",
            recipients=[email]
        )

        msg.body = f"""
        Kode verifikasi reset password Anda:

        {otp}

        Kode berlaku selama 10 menit.
        """

        mail.send(msg)

        flash("Kode Verifikasi telah dikirim ke email Anda.", "success")
        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/forgot-password.html")

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        otp = request.form.get("otp")

        if otp != session.get("reset_otp"):
            flash("Kode OTP salah.", "danger")
            return redirect(url_for("auth.verify_otp"))

        return redirect(url_for("auth.reset_password"))

    return render_template("auth/verify-otp.html")

@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if request.method == "POST":

        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Konfirmasi password tidak cocok.", "danger")
            return redirect(url_for("auth.reset_password"))

        email = session.get("reset_email")

        user = AuthService.get_user_by_email(email)

        user.password = generate_password_hash(password)

        db.session.commit()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)

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
        flash("Konfirmasi password tidak cocok.", "danger")
        return redirect(url_for("auth.profile"))

    success, message = AuthService.update_password(current_user, current_pw, new_pw)
    flash(message, "success" if success else "danger")
    return redirect(url_for("auth.profile"))
