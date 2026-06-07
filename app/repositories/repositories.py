from app import db
from app.models import (
    Dataset,
    SpecificationVM,
    ServerForecastSimulation,
    ForecastResult,
    ServerEstimationResult,
)

class DatasetRepository:
    @staticmethod
    def has_data() -> bool:
        return db.session.query(Dataset.id).first() is not None
       
    @staticmethod
    def get_all_package_ids() -> list[int]:
        rows = db.session.query(Dataset.package_id).distinct().all()
        return sorted([r[0] for r in rows])
    
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