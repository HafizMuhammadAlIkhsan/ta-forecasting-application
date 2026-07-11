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


class AuthController:
    @staticmethod
    def root():
        if current_user.is_authenticated:
            if not DatasetRepository.has_data():
                return redirect(url_for("forecast.index"))
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @staticmethod
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

    @staticmethod
    @login_required
    def logout():
        logout_user()
        flash("Anda telah logout.", "info")
        return redirect(url_for("auth.login"))

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    @login_required
    def profile():
        return render_template("auth/profile.html")

    @staticmethod
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


auth_bp.add_url_rule("/", view_func=AuthController.root, methods=["GET"])
auth_bp.add_url_rule("/login", view_func=AuthController.login, methods=["GET", "POST"])
auth_bp.add_url_rule("/logout", view_func=AuthController.logout, methods=["GET"])
auth_bp.add_url_rule("/forgot-password", view_func=AuthController.forgot_password, methods=["GET", "POST"])
auth_bp.add_url_rule("/reset-password/<token>", view_func=AuthController.reset_password_token, methods=["GET", "POST"])
auth_bp.add_url_rule("/profile", view_func=AuthController.profile, methods=["GET"])
auth_bp.add_url_rule("/profile/update-password", view_func=AuthController.update_password, methods=["POST"])
