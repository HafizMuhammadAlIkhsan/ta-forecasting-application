import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db as _db, mail
from app.models import User


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret-key",
        MAIL_SUPPRESS_SEND=True,
        WTF_CSRF_ENABLED=False,
    )
    mail.init_app(app)

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seed_user(db):
    def _seed_user(email="user@example.com", password="Password123"):
        user = User(email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return user

    return _seed_user
