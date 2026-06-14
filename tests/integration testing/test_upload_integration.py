from datetime import date
from io import BytesIO

from app.models import Dataset
from app.repositories import DatasetRepository


# IT-06
def test_upload_valid_csv_saves_dataset(client, seed_user):
    user = seed_user()
    client.post("/login", data={"email": user.email, "password": "Password123"})

    csv_content = (
        b"package_id,date,total_subscribe,total_terminate\n"
        b"48,2024-01-01,10,2\n"
        b"48,2024-02-01,12,3\n"
    )
    response = client.post(
        "/main/upload",
        data={"file": (BytesIO(csv_content), "data.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/main/"
    assert Dataset.query.count() == 2

# IT-07
def test_upload_invalid_file_does_not_save(client, seed_user):
    user = seed_user()
    client.post("/login", data={"email": user.email, "password": "Password123"})

    response = client.post(
        "/main/upload",
        data={"file": (BytesIO(b"not a csv"), "data.xlsx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/main/"
    assert Dataset.query.count() == 0

# IT-14
def test_bulk_upsert_does_not_create_duplicates(db):
    record = {
        "package_id": 48,
        "date": date(2024, 1, 1),
        "total_subscribe": 10,
        "total_terminate": 2,
    }

    DatasetRepository.bulk_upsert([record])
    DatasetRepository.bulk_upsert([record])

    assert Dataset.query.filter_by(package_id=48, date=date(2024, 1, 1)).count() == 1
