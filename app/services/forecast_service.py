import logging

import pandas as pd
from prophet.diagnostics import cross_validation
from prophet import Prophet
from app.repositories import (
    DatasetRepository,
    ForecastResultRepository,
    ForecastMetricRepository,
)
from app import db
from app.models import Dataset, ServerForecastSimulation

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

class ForecastService:
    @staticmethod
    def run(simulation: ServerForecastSimulation) -> None:
        package_ids = DatasetRepository.get_all_package_ids()
        all_forecast_records = []
        all_metric_records = []

        for package_id in package_ids:
            daily_df = ForecastService._prepare_daily_data(package_id)
            if daily_df is None or len(daily_df) < 2:
                continue

            last_history_date = pd.Timestamp(daily_df["ds"].iloc[-1])
            forecast_end_date = last_history_date + pd.DateOffset(
                months=simulation.horizon_months
            )
            horizon_days = max((forecast_end_date - last_history_date).days, 1)

            subs_forecast = ForecastService._run_prophet(
                daily_df[["ds", "total_subscribe"]].rename(
                    columns={"total_subscribe": "y"}
                ),
                horizon_days,
            )

            terminate_forecast = ForecastService._run_prophet(
                daily_df[["ds", "total_terminate"]].rename(
                    columns={"total_terminate": "y"}
                ),
                horizon_days,
            )

            subscribe_report = ForecastService._build_series_cv_report(
                daily_df[["ds", "total_subscribe"]].rename(columns={"total_subscribe": "y"}),
                horizon_days,
            )
            terminate_report = ForecastService._build_series_cv_report(
                daily_df[["ds", "total_terminate"]].rename(columns={"total_terminate": "y"}),
                horizon_days,
            )

            sub_m = subscribe_report if subscribe_report else {}
            term_m = terminate_report if terminate_report else {}

            all_metric_records.append(
                {
                    "simulation_id": simulation.simulation_id,
                    "package_id": package_id,
                    "subscribe_mae": sub_m.get("mae"),
                    "subscribe_rmse": sub_m.get("rmse"),
                    "subscribe_smape": sub_m.get("smape"),
                    "terminate_mae": term_m.get("mae"),
                    "terminate_rmse": term_m.get("rmse"),
                    "terminate_smape": term_m.get("smape"),
                }
            )

            merged = subs_forecast.rename(columns={"yhat": "forecast_subscribe"})
            merged["forecast_terminate"] = terminate_forecast["yhat"].values

            for _, row in merged.iterrows():
                all_forecast_records.append(
                    {
                        "package_id": package_id,
                        "date": row["ds"].date(),
                        "forecast_subscribe": max(0.0, float(row["forecast_subscribe"])),
                        "forecast_terminate": max(0.0, float(row["forecast_terminate"])),
                        "simulation_id": simulation.simulation_id,
                    }
                )

        ForecastResultRepository.bulk_insert(all_forecast_records)
        ForecastMetricRepository.bulk_insert(all_metric_records)

    @staticmethod
    def _prepare_daily_data(package_id: int) -> pd.DataFrame | None:
        rows = (
            db.session.query(Dataset)
            .filter_by(package_id=package_id)
            .order_by(Dataset.date)
            .all()
        )

        if not rows:
            return None

        df = pd.DataFrame(
            [
                {
                    "ds": pd.Timestamp(r.date),
                    "total_subscribe": float(r.total_subscribe),
                    "total_terminate": float(r.total_terminate),
                }
                for r in rows
            ]
        )

        df = df.set_index("ds")
        daily = df.resample("D").sum()
        daily = daily.asfreq("D", fill_value=0.0)
        daily = daily.reset_index()

        return daily

    @staticmethod
    def _run_prophet(df: pd.DataFrame, horizon_months: int) -> pd.DataFrame:
        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon_months, freq="D")
        forecast = model.predict(future)
        return forecast[["ds", "yhat"]]

    @staticmethod
    def _build_series_cv_report(series_df: pd.DataFrame, horizon_days: int) -> dict | None:
        series_df = series_df.sort_values("ds").reset_index(drop=True)

        if len(series_df) < 8:
            return None

        cv_horizon_days = max(1, min(horizon_days, max(7, len(series_df) // 4)))
        if len(series_df) <= (cv_horizon_days * 2 + 1):
            return None

        initial_days = max(cv_horizon_days * 2, len(series_df) - cv_horizon_days - 1)
        period_days = max(1, cv_horizon_days // 2)

        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
        )
        model.fit(series_df)

        try:
            cv_results = cross_validation(
                model,
                initial=f"{initial_days} days",
                period=f"{period_days} days",
                horizon=f"{cv_horizon_days} days",
            )
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "[ForecastService] Cross validation skipped: %s",
                exc,
            )
            return None

        if cv_results.empty:
            return None

        residuals = cv_results["y"] - cv_results["yhat"]
        abs_errors = residuals.abs()
        smape_denominator = cv_results["y"].abs() + cv_results["yhat"].abs()
        smape_values = (200 * abs_errors / smape_denominator.replace(0, pd.NA)).fillna(0.0)

        return {
            "mae": float(abs_errors.mean()),
            "rmse": float((residuals.pow(2).mean()) ** 0.5),
            "smape": float(smape_values.mean()),
        }