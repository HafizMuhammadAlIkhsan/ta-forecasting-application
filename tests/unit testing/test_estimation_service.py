from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.estimation_service import EstimationService


def make_simulation(**overrides):
    defaults = dict(
        simulation_id=1,
        server_utilization_percent=50.0,
        capacity_cpu=100.0,
        capacity_ram=200.0,
        capacity_storage=1000.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# UT-024
def test_run_returns_without_insert_when_forecast_empty(app):
    simulation = make_simulation()

    with patch("app.services.estimation_service.ForecastResultRepository.get_by_simulation_id", return_value=[]), \
            patch("app.services.estimation_service.ServerEstimationResultRepository.bulk_insert") as mock_bulk_insert:
        EstimationService.run(simulation)

    mock_bulk_insert.assert_not_called()

# UT-25
def test_run_raises_when_specification_vm_empty(app):
    forecast_row = SimpleNamespace(package_id=48, date=date(2024, 1, 1), forecast_subscribe=20, forecast_terminate=5)
    simulation = make_simulation()

    with patch("app.services.estimation_service.ForecastResultRepository.get_by_simulation_id", return_value=[forecast_row]), \
            patch("app.services.estimation_service.SpecificationVMRepository.get_all_as_dict", return_value={}):
        with pytest.raises(RuntimeError, match="Tabel specification_vm kosong"):
            EstimationService.run(simulation)

# UT-026
def test_run_calculates_final_utilization_with_valid_capacity(app):
    forecast_row = SimpleNamespace(package_id=48, date=date(2024, 1, 1), forecast_subscribe=20, forecast_terminate=5)
    spec = SimpleNamespace(cpu=2, ram=4, storage=10)
    simulation = make_simulation()

    with patch("app.services.estimation_service.ForecastResultRepository.get_by_simulation_id", return_value=[forecast_row]), \
            patch("app.services.estimation_service.SpecificationVMRepository.get_all_as_dict", return_value={48: spec}), \
            patch("app.services.estimation_service.ServerEstimationResultRepository.bulk_insert") as mock_bulk_insert:
        EstimationService.run(simulation)

    records = mock_bulk_insert.call_args[0][0]
    assert records[0]["final_utilization_percentage"] == pytest.approx(75.0)

# UT-27
def test_run_zero_capacity_returns_base_utilization(app):
    forecast_row = SimpleNamespace(package_id=48, date=date(2024, 1, 1), forecast_subscribe=20, forecast_terminate=5)
    spec = SimpleNamespace(cpu=2, ram=4, storage=10)
    simulation = make_simulation(capacity_cpu=0.0, capacity_ram=0.0, capacity_storage=0.0)

    with patch("app.services.estimation_service.ForecastResultRepository.get_by_simulation_id", return_value=[forecast_row]), \
            patch("app.services.estimation_service.SpecificationVMRepository.get_all_as_dict", return_value={48: spec}), \
            patch("app.services.estimation_service.ServerEstimationResultRepository.bulk_insert") as mock_bulk_insert:
        EstimationService.run(simulation)

    records = mock_bulk_insert.call_args[0][0]
    assert records[0]["final_utilization_percentage"] == pytest.approx(simulation.server_utilization_percent)

# UT-28
def test_run_skips_package_without_specification(app):
    row_with_spec = SimpleNamespace(package_id=48, date=date(2024, 1, 1), forecast_subscribe=20, forecast_terminate=5)
    row_without_spec = SimpleNamespace(package_id=99, date=date(2024, 1, 1), forecast_subscribe=10, forecast_terminate=1)
    spec = SimpleNamespace(cpu=2, ram=4, storage=10)
    simulation = make_simulation()

    with patch("app.services.estimation_service.ForecastResultRepository.get_by_simulation_id", return_value=[row_with_spec, row_without_spec]), \
            patch("app.services.estimation_service.SpecificationVMRepository.get_all_as_dict", return_value={48: spec}), \
            patch("app.services.estimation_service.ServerEstimationResultRepository.bulk_insert") as mock_bulk_insert:
        EstimationService.run(simulation)

    records = mock_bulk_insert.call_args[0][0]
    assert len(records) == 1

# UT-29
def test_run_raises_when_no_package_has_spec(app):
    forecast_row = SimpleNamespace(package_id=99, date=date(2024, 1, 1), forecast_subscribe=10, forecast_terminate=1)
    spec = SimpleNamespace(cpu=2, ram=4, storage=10)
    simulation = make_simulation()

    with patch("app.services.estimation_service.ForecastResultRepository.get_by_simulation_id", return_value=[forecast_row]), \
            patch("app.services.estimation_service.SpecificationVMRepository.get_all_as_dict", return_value={48: spec}):
        with pytest.raises(RuntimeError, match="Estimasi tidak menghasilkan data apapun"):
            EstimationService.run(simulation)
