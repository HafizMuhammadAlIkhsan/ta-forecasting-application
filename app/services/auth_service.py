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
