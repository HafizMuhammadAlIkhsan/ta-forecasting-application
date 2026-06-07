from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User
from app import db


class AuthService:
    @staticmethod
    def authenticate(email: str, password: str) -> User | None:
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            return user
        return None

    @staticmethod
    def update_password(
        user: User, current_password: str, new_password: str
    ) -> tuple[bool, str]:
        if not check_password_hash(user.password, current_password):
            return False, "Password saat ini tidak sesuai."
        if len(new_password) < 6:
            return False, "Password baru minimal 6 karakter."
        user.password = generate_password_hash(new_password)
        db.session.commit()
        return True, "Password berhasil diperbarui."