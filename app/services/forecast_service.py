import logging
import pandas as pd
from prophet import Prophet
from app.repositories import (
    DatasetRepository,
    ForecastResultRepository,
)
from app import db
from app.models import Dataset, ServerForecastSimulation

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

class ForecastService:
    @staticmethod
    def run(simulation: ServerForecastSimulation) -> None:
        package_ids = DatasetRepository.get_all_package_ids()
        all_forecast_records = []

        for package_id in package_ids:
            monthly_df = ForecastService._aggregate_monthly(package_id)
            if monthly_df is None or len(monthly_df) < 2:
                continue

            subs_forecast = ForecastService._run_prophet(
                monthly_df[["ds", "total_subscribe"]].rename(
                    columns={"total_subscribe": "y"}
                ),
                simulation.horizon_months,
            )

            terminate_forecast = ForecastService._run_prophet(
                monthly_df[["ds", "total_terminate"]].rename(
                    columns={"total_terminate": "y"}
                ),
                simulation.horizon_months,
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

    @staticmethod
    def _aggregate_monthly(package_id: int) -> pd.DataFrame | None:
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
        monthly = df.resample("MS").sum()
        monthly = monthly.asfreq("MS", fill_value=0.0)
        monthly = monthly.reset_index()

        return monthly

    @staticmethod
    def _run_prophet(df: pd.DataFrame, horizon_months: int) -> pd.DataFrame:
        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon_months, freq="MS")
        forecast = model.predict(future)
        return forecast[["ds", "yhat"]]
