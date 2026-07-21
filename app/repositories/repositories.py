from app import db
from app.models import (
    Dataset,
    SpecificationVM,
    ServerForecastSimulation,
    ForecastResult,
    ServerEstimationResult,
    ForecastMetric
)

class DatasetRepository:
    @staticmethod
    def bulk_upsert(records: list[dict]) -> None:
        if not records:
            return

        for record in records:
            existing = Dataset.query.filter_by(
                package_id=record["package_id"],
                date=record["date"],
            ).first()

            if existing:
                changed = (
                    existing.total_subscribe != record["total_subscribe"]
                    or existing.total_terminate != record["total_terminate"]
                )

                if changed:
                    existing.total_subscribe = record["total_subscribe"]
                    existing.total_terminate = record["total_terminate"]
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
    
    @staticmethod
    def get_last_date():
        return db.session.query(db.func.max(Dataset.date)).scalar()


class SpecificationVMRepository:
    @staticmethod
    def get_by_package_id(package_id: int) -> SpecificationVM | None:
        return SpecificationVM.query.filter_by(package_id=package_id).first()

    @staticmethod
    def get_all() -> list[SpecificationVM]:
        return SpecificationVM.query.order_by(SpecificationVM.package_id).all()

    @staticmethod
    def get_all_as_dict() -> dict[int, SpecificationVM]:
        specs = SpecificationVM.query.all()
        return {spec.package_id: spec for spec in specs}

class SimulationRepository:
    @staticmethod
    def create(
        server_utilization_percent: float,
        horizon_months: int,
        capacity_cpu: float,
        capacity_ram: float,
        capacity_storage: float,
    ) -> ServerForecastSimulation:
        simulation = ServerForecastSimulation(
            server_utilization_percent=server_utilization_percent,
            horizon_months=horizon_months,
            capacity_cpu=capacity_cpu,
            capacity_ram=capacity_ram,
            capacity_storage=capacity_storage,
        )
        db.session.add(simulation)
        db.session.commit()
        return simulation

    @staticmethod
    def get_all_ordered_by_newest() -> list[ServerForecastSimulation]:
        return ServerForecastSimulation.query.order_by(
            ServerForecastSimulation.created_at.desc()
        ).all()

    @staticmethod
    def get_by_id(simulation_id: int) -> ServerForecastSimulation | None:
        return ServerForecastSimulation.query.get(simulation_id)

class ForecastResultRepository:
    @staticmethod
    def bulk_insert(records: list[dict]) -> None:
        if not records:
            return
        db.session.bulk_insert_mappings(ForecastResult, records)
        db.session.commit()

    @staticmethod
    def get_by_simulation_id(simulation_id: int) -> list[ForecastResult]:
        return (
            ForecastResult.query
            .filter_by(simulation_id=simulation_id)
            .order_by(ForecastResult.package_id, ForecastResult.date)
            .all()
        )
        
class ServerEstimationResultRepository:
    @staticmethod
    def bulk_insert(records: list[dict]) -> None:
        if not records:
            return
        db.session.bulk_insert_mappings(ServerEstimationResult, records)
        db.session.commit()

    @staticmethod
    def get_by_simulation_id(simulation_id: int) -> list[ServerEstimationResult]:
        return (
            ServerEstimationResult.query
            .filter_by(simulation_id=simulation_id)
            .order_by(ServerEstimationResult.date)
            .all()
        )

class ForecastMetricRepository:
    @staticmethod
    def bulk_insert(records: list[dict]) -> None:
        if not records:
            return
        db.session.bulk_insert_mappings(ForecastMetric, records)
        db.session.commit()

    @staticmethod
    def get_by_simulation_id(simulation_id: int) -> list[ForecastMetric]:
        return (
            ForecastMetric.query
            .filter_by(simulation_id=simulation_id)
            .order_by(ForecastMetric.package_id)
            .all()
        )