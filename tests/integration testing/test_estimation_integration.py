from datetime import date

from app import db
from app.models import SpecificationVM
from app.repositories import (
    ForecastResultRepository,
    ServerEstimationResultRepository,
    SimulationRepository,
)
from app.services.estimation_service import EstimationService


# IT-11
def test_estimation_service_run_saves_results_per_date(db):
    simulation = SimulationRepository.create(
        server_utilization_percent=50,
        horizon_months=1,
        capacity_cpu=100,
        capacity_ram=200,
        capacity_storage=1000,
    )

    db.session.add(SpecificationVM(package_id=48, cpu=2, ram=4, storage=10))
    ForecastResultRepository.bulk_insert([{
        "package_id": 48,
        "date": date(2024, 3, 1),
        "forecast_subscribe": 20.0,
        "forecast_terminate": 5.0,
        "simulation_id": simulation.simulation_id,
    }])

    EstimationService.run(simulation)

    results = ServerEstimationResultRepository.get_by_simulation_id(simulation.simulation_id)
    assert len(results) == 1
    assert results[0].date == date(2024, 3, 1)
    assert results[0].simulation_id == simulation.simulation_id
