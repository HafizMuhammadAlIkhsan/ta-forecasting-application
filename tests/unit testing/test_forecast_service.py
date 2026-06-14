from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from app import db
from app.models import Dataset
from app.services.forecast_service import ForecastService


# UT-19
def test_aggregate_monthly_sums_per_month(app):
    db.session.add_all([
        Dataset(package_id=48, date=date(2024, 1, 5), total_subscribe=10, total_terminate=2),
        Dataset(package_id=48, date=date(2024, 1, 20), total_subscribe=5, total_terminate=1),
    ])
    db.session.commit()

    result = ForecastService._aggregate_monthly(48)

    assert result is not None
    assert len(result) == 1
    row = result.iloc[0]
    assert row["ds"] == pd.Timestamp("2024-01-01")
    assert row["total_subscribe"] == 15
    assert row["total_terminate"] == 3

# UT-20
def test_aggregate_monthly_returns_none_when_no_data(app):
    result = ForecastService._aggregate_monthly(999)

    assert result is None

# UT-21
def test_run_skips_package_with_insufficient_data(app):
    monthly_df = pd.DataFrame({
        "ds": [pd.Timestamp("2024-01-01")],
        "total_subscribe": [5.0],
        "total_terminate": [1.0],
    })
    simulation = SimpleNamespace(simulation_id=1, horizon_months=6)

    with patch("app.services.forecast_service.DatasetRepository.get_all_package_ids", return_value=[48]), \
            patch.object(ForecastService, "_aggregate_monthly", return_value=monthly_df), \
            patch("app.services.forecast_service.ForecastResultRepository.bulk_insert") as mock_bulk_insert:
        ForecastService.run(simulation)

    mock_bulk_insert.assert_called_once_with([])

# UT-22
def test_run_clamps_negative_forecast_to_zero(app):
    monthly_df = pd.DataFrame({
        "ds": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01")],
        "total_subscribe": [10.0, 12.0],
        "total_terminate": [5.0, 6.0],
    })
    future_subscribe = pd.DataFrame({"ds": [pd.Timestamp("2024-03-01")], "yhat": [-10.0]})
    future_terminate = pd.DataFrame({"ds": [pd.Timestamp("2024-03-01")], "yhat": [-5.0]})
    simulation = SimpleNamespace(simulation_id=1, horizon_months=1)

    with patch("app.services.forecast_service.DatasetRepository.get_all_package_ids", return_value=[48]), \
            patch.object(ForecastService, "_aggregate_monthly", return_value=monthly_df), \
            patch.object(ForecastService, "_run_prophet", side_effect=[future_subscribe, future_terminate]), \
            patch("app.services.forecast_service.ForecastResultRepository.bulk_insert") as mock_bulk_insert:
        ForecastService.run(simulation)

    records = mock_bulk_insert.call_args[0][0]
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
