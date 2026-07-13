from werkzeug.security import generate_password_hash
from app import db
from app.models import User


def seed_users() -> None:
    default_users = [
        {"email": "admin@forecasting.com", "password": "admin123"},
        {"email": "kensio683@gmail.com", "password": "admin123"},
        {"email": "khairiansyahfachry1@gmail.com", "password": "admin123"},
    ]

    for data in default_users:
        exists = User.query.filter_by(email=data["email"]).first()
        if not exists:
            db.session.add(
                User(
                    email=data["email"],
                    password=generate_password_hash(data["password"]),
                )
            )

    db.session.commit()
    print("✅ User seeded.")
