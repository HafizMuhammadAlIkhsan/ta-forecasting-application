from contextlib import contextmanager
from datetime import date

from flask import template_rendered

from app import db
from app.models import Dataset, SpecificationVM
from app.repositories import SimulationRepository
from app.services.estimation_service import EstimationService
from app.services.forecast_service import ForecastService


@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


# IT-12
def test_dashboard_prepares_chart_data(client, seed_user, app):
    user = seed_user()
    client.post("/login", data={"email": user.email, "password": "Password123"})

    db.session.add_all([
        Dataset(package_id=48, date=date(2024, 1, 1), total_subscribe=10, total_terminate=2),
        Dataset(package_id=48, date=date(2024, 2, 1), total_subscribe=12, total_terminate=3),
    ])
    db.session.add(SpecificationVM(package_id=48, cpu=1, ram=1, storage=20))
    db.session.commit()

    simulation = SimulationRepository.create(
        server_utilization_percent=50,
        horizon_months=4,
        capacity_cpu=100,
        capacity_ram=256,
        capacity_storage=1000,
    )
    ForecastService.run(simulation)
    EstimationService.run(simulation)

    with captured_templates(app) as templates:
        response = client.get(f"/dashboard/?simulation_id={simulation.simulation_id}")

    assert response.status_code == 200
    template, context = templates[0]
    assert template.name == "dashboard/index.html"
    assert context["selected_simulation"].simulation_id == simulation.simulation_id
    assert len(context["forecast_data"]) > 0
    assert len(context["history_data"]) > 0
    assert len(context["estimation_data"]) > 0
    assert context["package_ids"] == [48]
