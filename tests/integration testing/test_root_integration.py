from datetime import date

from app import db
from app.models import Dataset


# IT-13
def test_root_redirects_based_on_session_and_data(client, seed_user):
    # 1. Anonymous user
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

    # 2. Logged in, no dataset
    user = seed_user()
    client.post("/login", data={"email": user.email, "password": "Password123"})

    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/forecast/"

    # 3. Logged in, dataset available
    db.session.add(Dataset(package_id=48, date=date(2024, 1, 1), total_subscribe=1, total_terminate=0))
    db.session.commit()

    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard/"
