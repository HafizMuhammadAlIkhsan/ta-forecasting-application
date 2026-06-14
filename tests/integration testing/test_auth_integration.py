from datetime import date

from werkzeug.security import check_password_hash

from app import db, mail
from app.models import Dataset, User


# IT-01
def test_login_success_creates_session(client, seed_user):
    seed_user(email="user@example.com", password="Password123")

    response = client.post("/login", data={
        "email": "user@example.com",
        "password": "Password123",
    })

    assert response.status_code == 302
    assert response.headers["Location"] == "/main/"

    with client.session_transaction() as sess:
        assert "_user_id" in sess

# IT-02
def test_login_redirects_to_dashboard_when_dataset_exists(client, seed_user):
    seed_user(email="user@example.com", password="Password123")
    db.session.add(Dataset(package_id=48, date=date(2024, 1, 1), total_subscribe=1, total_terminate=0))
    db.session.commit()

    response = client.post("/login", data={
        "email": "user@example.com",
        "password": "Password123",
    })

    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard/"


# IT-03
def test_update_password_persists_across_sessions(client, seed_user):
    seed_user(email="user@example.com", password="OldPassword123")

    client.post("/login", data={"email": "user@example.com", "password": "OldPassword123"})
    client.post("/profile/update-password", data={
        "current_password": "OldPassword123",
        "new_password": "NewPassword123",
        "confirm_password": "NewPassword123",
    })
    client.get("/logout")

    old_password_login = client.post("/login", data={
        "email": "user@example.com",
        "password": "OldPassword123",
    })
    new_password_login = client.post("/login", data={
        "email": "user@example.com",
        "password": "NewPassword123",
    })

    assert old_password_login.status_code == 200
    assert new_password_login.status_code == 302
    assert new_password_login.headers["Location"] == "/main/"


# IT-04
def test_forgot_password_sends_reset_email(client, seed_user):
    seed_user(email="user@example.com")

    with mail.record_messages() as outbox:
        response = client.post("/forgot-password", data={"email": "user@example.com"})

    assert response.status_code == 302
    assert len(outbox) == 1
    assert outbox[0].recipients == ["user@example.com"]
    assert "/reset-password/" in outbox[0].body


# IT-05
def test_reset_password_with_valid_token(client, seed_user, app):
    seed_user(email="user@example.com", password="OldPassword123")
    token = app.serializer.dumps("user@example.com", salt="reset-password")

    get_response = client.get(f"/reset-password/{token}")
    assert get_response.status_code == 200

    post_response = client.post(f"/reset-password/{token}", data={
        "password": "NewPassword123",
        "confirm_password": "NewPassword123",
    })

    assert post_response.status_code == 302
    assert post_response.headers["Location"] == "/login"

    user = User.query.filter_by(email="user@example.com").first()
    assert check_password_hash(user.password, "NewPassword123")
