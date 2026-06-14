from datetime import date

from app.models import Dataset
from app.repositories import DatasetRepository


# UT-15
def test_bulk_upsert_inserts_new_record(app):
    record = {
        "package_id": 48,
        "date": date(2024, 1, 1),
        "total_subscribe": 10,
        "total_terminate": 2,
    }

    DatasetRepository.bulk_upsert([record])

    saved = Dataset.query.filter_by(package_id=48, date=date(2024, 1, 1)).first()
    assert saved is not None
    assert saved.total_subscribe == 10
    assert saved.total_terminate == 2

# UT-16
def test_bulk_upsert_updates_existing_record(app):
    DatasetRepository.bulk_upsert([{
        "package_id": 48,
        "date": date(2024, 1, 1),
        "total_subscribe": 10,
        "total_terminate": 2,
    }])

    DatasetRepository.bulk_upsert([{
        "package_id": 48,
        "date": date(2024, 1, 1),
        "total_subscribe": 99,
        "total_terminate": 5,
    }])

    rows = Dataset.query.filter_by(package_id=48, date=date(2024, 1, 1)).all()
    assert len(rows) == 1
    assert rows[0].total_subscribe == 99
    assert rows[0].total_terminate == 5

# UT-17
def test_has_data_returns_false_when_empty(app):
    assert DatasetRepository.has_data() is False


# UT-18
def test_has_data_returns_true_when_data_exists(app):
    DatasetRepository.bulk_upsert([{
        "package_id": 1,
        "date": date(2024, 1, 1),
        "total_subscribe": 1,
        "total_terminate": 0,
    }])

    assert DatasetRepository.has_data() is True
