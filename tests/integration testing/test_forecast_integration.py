from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import (
    Dataset,
    ForecastResult,
    ServerEstimationResult,
    ServerForecastSimulation,
    SpecificationVM,
)
from app.repositories import ForecastResultRepository, SimulationRepository
from app.services.forecast_service import ForecastService

# IT-08
def test_run_forecast_invalid_horizon_does_not_create_simulation(client, seed_user):
    user = seed_user()
    client.post("/login", data={"email": user.email, "password": "Password123"})

    db.session.add(Dataset(package_id=48, date=date(2024, 1, 1), total_subscribe=10, total_terminate=2))
    db.session.commit()

    response = client.post("/forecast/run-forecast", data={
        "server_utilization_percent": "50",
        "horizon_months": "13",
        "capacity_cpu": "100",
        "capacity_ram": "256",
        "capacity_storage": "1000",
    })

    assert response.status_code == 302
    assert response.headers["Location"] == "/forecast/"
    assert ServerForecastSimulation.query.count() == 0

# IT-09
def test_run_forecast_valid_runs_full_pipeline(client, seed_user):
    user = seed_user()
    client.post("/login", data={"email": user.email, "password": "Password123"})

    db.session.add_all([
        Dataset(package_id=48, date=date(2024, 1, 1), total_subscribe=10, total_terminate=2),
        Dataset(package_id=48, date=date(2024, 2, 1), total_subscribe=12, total_terminate=3),
    ])
    db.session.add(SpecificationVM(package_id=48, cpu=1, ram=1, storage=20))
    db.session.commit()

    response = client.post("/forecast/run-forecast", data={
        "server_utilization_percent": "50",
        "horizon_months": "4",
        "capacity_cpu": "100",
        "capacity_ram": "256",
        "capacity_storage": "1000",
    })

    simulation = ServerForecastSimulation.query.first()
    assert simulation is not None
    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/?simulation_id={simulation.simulation_id}"
    assert ForecastResult.query.filter_by(simulation_id=simulation.simulation_id).count() > 0
    assert ServerEstimationResult.query.filter_by(simulation_id=simulation.simulation_id).count() > 0

# IT-10
def test_forecast_service_run_saves_results_per_package(db):
    db.session.add_all([
        Dataset(package_id=48, date=date(2024, 1, 1), total_subscribe=10, total_terminate=2),
        Dataset(package_id=48, date=date(2024, 2, 1), total_subscribe=12, total_terminate=3),
    ])
    db.session.commit()

    simulation = SimulationRepository.create(
        server_utilization_percent=50,
        horizon_months=4,
        capacity_cpu=100,
        capacity_ram=256,
        capacity_storage=1000,
    )

    ForecastService.run(simulation)

    results = ForecastResultRepository.get_by_simulation_id(simulation.simulation_id)
    assert len(results) > 0
    assert all(r.package_id == 48 for r in results)
    assert all(r.simulation_id == simulation.simulation_id for r in results)

# IT-15
def test_forecast_result_unique_constraint(db):
    simulation = SimulationRepository.create(
        server_utilization_percent=50,
        horizon_months=4,
        capacity_cpu=100,
        capacity_ram=256,
        capacity_storage=1000,
    )
    record = {
        "package_id": 48,
        "date": date(2024, 1, 1),
        "forecast_subscribe": 10.0,
        "forecast_terminate": 2.0,
        "simulation_id": simulation.simulation_id,
    }

    ForecastResultRepository.bulk_insert([record])

    with pytest.raises(IntegrityError):
        ForecastResultRepository.bulk_insert([record])
