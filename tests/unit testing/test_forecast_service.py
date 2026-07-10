from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from app import db
from app.models import Dataset, SpecificationVM
from app.repositories import ForecastMetricRepository, SimulationRepository
from app.services.forecast_service import ForecastService


# UT-19
def test_prepare_daily_data_resamples_to_daily(app):
    db.session.add_all([
        Dataset(package_id=48, date=date(2024, 1, 5), total_subscribe=10, total_terminate=2),
        Dataset(package_id=48, date=date(2024, 1, 20), total_subscribe=5, total_terminate=1),
    ])
    db.session.commit()

    result = ForecastService._prepare_daily_data(48)

    assert result is not None
    assert "ds" in result.columns
    assert "total_subscribe" in result.columns
    assert "total_terminate" in result.columns

# UT-20
def test_prepare_daily_data_returns_none_when_no_data(app):
    result = ForecastService._prepare_daily_data(999)

    assert result is None

# UT-21
def test_run_skips_package_with_insufficient_data(app):
    daily_df = pd.DataFrame({
        "ds": [pd.Timestamp("2024-01-01")],
        "total_subscribe": [5.0],
        "total_terminate": [1.0],
    })
    simulation = SimpleNamespace(simulation_id=1, horizon_months=6)

    with patch("app.services.forecast_service.DatasetRepository.get_all_package_ids", return_value=[48]), \
            patch.object(ForecastService, "_prepare_daily_data", return_value=daily_df), \
            patch("app.services.forecast_service.ForecastResultRepository.bulk_insert") as mock_forecast_insert, \
            patch("app.services.forecast_service.ForecastMetricRepository.bulk_insert") as mock_metric_insert:
        ForecastService.run(simulation)

    mock_forecast_insert.assert_called_once_with([])
    mock_metric_insert.assert_called_once_with([])

# UT-22
def test_run_clamps_negative_forecast_to_zero(app):
    daily_df = pd.DataFrame({
        "ds": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01")],
        "total_subscribe": [10.0, 12.0],
        "total_terminate": [5.0, 6.0],
    })
    future_subscribe = pd.DataFrame({"ds": [pd.Timestamp("2024-03-01")], "yhat": [-10.0]})
    future_terminate = pd.DataFrame({"ds": [pd.Timestamp("2024-03-01")], "yhat": [-5.0]})
    simulation = SimpleNamespace(simulation_id=1, horizon_months=1)

    with patch("app.services.forecast_service.DatasetRepository.get_all_package_ids", return_value=[48]), \
            patch.object(ForecastService, "_prepare_daily_data", return_value=daily_df), \
            patch.object(ForecastService, "_run_prophet", side_effect=[future_subscribe, future_terminate]), \
            patch.object(ForecastService, "_build_series_cv_report", return_value=None), \
            patch("app.services.forecast_service.ForecastResultRepository.bulk_insert") as mock_forecast_insert, \
            patch("app.services.forecast_service.ForecastMetricRepository.bulk_insert"):
        ForecastService.run(simulation)

    records = mock_forecast_insert.call_args[0][0]
    assert records[0]["forecast_subscribe"] == 0.0
    assert records[0]["forecast_terminate"] == 0.0

# UT-23
def test_run_prophet_returns_ds_and_yhat_columns():
    df = pd.DataFrame({
        "ds": pd.date_range("2024-01-01", periods=2, freq="MS"),
        "y": [10.0, 12.0],
    })

    result = ForecastService._run_prophet(df, horizon_months=4)

    assert {"ds", "yhat"}.issubset(result.columns)
    assert len(result) == len(df) + 4

# UT-31
def test_build_series_cv_report_returns_none_when_insufficient_data():
    df = pd.DataFrame({
        "ds": pd.date_range("2024-01-01", periods=5, freq="D"),
        "y": [1.0, 2.0, 3.0, 4.0, 5.0],
    })

    result = ForecastService._build_series_cv_report(df, horizon_days=2)

    assert result is None

# UT-32
def test_forecast_metric_repository_bulk_insert_and_get(app):
    simulation = SimulationRepository.create(
        server_utilization_percent=50,
        horizon_months=4,
        capacity_cpu=100,
        capacity_ram=256,
        capacity_storage=1000,
    )

    ForecastMetricRepository.bulk_insert([{
        "simulation_id": simulation.simulation_id,
        "package_id": 48,
        "subscribe_mae": 1.5,
        "subscribe_rmse": 2.0,
        "subscribe_smape": 10.0,
        "terminate_mae": 0.8,
        "terminate_rmse": 1.2,
        "terminate_smape": 8.5,
    }])

    results = ForecastMetricRepository.get_by_simulation_id(simulation.simulation_id)
    assert len(results) == 1
    assert results[0].package_id == 48
    assert results[0].subscribe_mae == 1.5
