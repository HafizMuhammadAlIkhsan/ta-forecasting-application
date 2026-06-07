from app import db
from app.models import (
    Dataset,
)

class DatasetRepository:
    @staticmethod
    def bulk_upsert(records: list[dict]) -> None:
        """Insert atau update jika (package_id, date) sudah ada."""
        if not records:
            return
        for record in records:
            existing = Dataset.query.filter_by(
                package_id=record["package_id"],
                date=record["date"],
            ).first()
            if existing:
                existing.total_subscribe = record["total_subscribe"]
                existing.total_terminate = record["total_terminate"]
            else:
                db.session.add(Dataset(**record))
        db.session.commit()

    @staticmethod
    def get_all() -> list[Dataset]:
        return Dataset.query.order_by(Dataset.package_id, Dataset.date).all()

    @staticmethod
    def has_data() -> bool:
        return db.session.query(Dataset.id).first() is not None

    @staticmethod
    def get_all_package_ids() -> list[int]:
        rows = db.session.query(Dataset.package_id).distinct().all()
        return sorted([r[0] for r in rows])


class SpecificationVMRepository:
   pass

class SimulationRepository:
   pass

class ForecastResultRepository:
    pass