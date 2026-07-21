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

        promo_holidays_df = ForecastService._get_promo_holidays()

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
                promo_holidays_df
            )

            terminate_forecast = ForecastService._run_prophet(
                daily_df[["ds", "total_terminate"]].rename(
                    columns={"total_terminate": "y"}
                ),
                horizon_days,
                promo_holidays_df
            )

            subscribe_report = ForecastService._build_series_cv_report(
                daily_df[["ds", "total_subscribe"]].rename(columns={"total_subscribe": "y"}),
                horizon_days,
                promo_holidays_df
            )
            terminate_report = ForecastService._build_series_cv_report(
                daily_df[["ds", "total_terminate"]].rename(columns={"total_terminate": "y"}),
                horizon_days,
                promo_holidays_df
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
    def _run_prophet(df: pd.DataFrame, horizon_months: int, holidays_df: pd.DataFrame) -> pd.DataFrame:
        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
            holidays=holidays_df,
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon_months, freq="D")
        forecast = model.predict(future)
        return forecast[["ds", "yhat"]]

    @staticmethod
    def _build_series_cv_report(series_df: pd.DataFrame, horizon_days: int, holidays_df: pd.DataFrame) -> dict | None:
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
            holidays=holidays_df,
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

    @staticmethod
    def _get_promo_holidays() -> pd.DataFrame:
        promo_data = [
            {'name': 'tahun_baru', 'start': '2020-01-01', 'end': '2020-01-10'},
            {'name': 'tahun_baru', 'start': '2021-12-31', 'end': '2022-01-14'},
            {'name': 'tahun_baru', 'start': '2023-12-08', 'end': '2024-01-05'},

            {'name': 'imlek', 'start': '2021-02-08', 'end': '2021-02-19'},
            {'name': 'imlek', 'start': '2022-02-01', 'end': '2022-02-11'},
            {'name': 'imlek', 'start': '2024-02-08', 'end': '2024-02-15'},

            {'name': 'ramadan', 'start': '2023-03-24', 'end': '2023-04-07'},
            {'name': 'ramadan', 'start': '2025-03-10', 'end': '2025-04-11'},

            {'name': 'lebaran', 'start': '2021-05-03', 'end': '2021-05-31'},
            {'name': 'lebaran', 'start': '2022-04-28', 'end': '2022-05-13'},
            {'name': 'lebaran', 'start': '2023-04-17', 'end': '2023-05-05'},

            {'name': 'kemerdekaan_ri', 'start': '2020-08-17', 'end': '2020-08-31'},
            {'name': 'kemerdekaan_ri', 'start': '2021-08-16', 'end': '2021-08-30'},
            {'name': 'kemerdekaan_ri', 'start': '2022-08-12', 'end': '2022-08-26'},
            {'name': 'kemerdekaan_ri', 'start': '2024-08-17', 'end': '2024-09-16'},
            {'name': 'kemerdekaan_ri', 'start': '2025-08-17', 'end': '2025-08-19'},
            {'name': 'kemerdekaan_ri', 'start': '2025-08-20', 'end': '2025-08-31'},

            {'name': 'promo_9_9', 'start': '2023-09-09', 'end': '2023-09-23'},
            {'name': 'promo_9_9', 'start': '2025-09-09', 'end': '2025-09-09'},

            {'name': 'promo_10_10', 'start': '2020-10-10', 'end': '2020-10-17'},
            {'name': 'promo_10_10', 'start': '2023-10-10', 'end': '2023-10-30'},
            {'name': 'promo_10_10', 'start': '2024-10-10', 'end': '2024-10-31'},
            {'name': 'promo_10_10', 'start': '2025-10-10', 'end': '2025-10-20'},

            {'name': 'promo_november', 'start': '2021-11-08', 'end': '2021-11-21'},
            {'name': 'promo_november', 'start': '2022-11-07', 'end': '2022-11-18'},
            {'name': 'promo_november', 'start': '2025-11-10', 'end': '2025-11-15'},

            {'name': 'harbolnas', 'start': '2021-12-11', 'end': '2021-12-18'},
            {'name': 'harbolnas', 'start': '2024-12-12', 'end': '2024-12-12'},
            {'name': 'harbolnas', 'start': '2025-12-12', 'end': '2025-12-24'},

            {'name': 'natal_tahun_baru', 'start': '2022-12-23', 'end': '2023-01-06'},
            {'name': 'natal_tahun_baru', 'start': '2024-12-23', 'end': '2025-01-10'},
            {'name': 'natal_tahun_baru', 'start': '2025-12-25', 'end': '2026-01-10'},

            {'name': 'promo_juni', 'start': '2023-06-23', 'end': '2023-06-30'},
            {'name': 'promo_juni', 'start': '2025-06-06', 'end': '2025-06-08'},
            {'name': 'promo_juni', 'start': '2025-06-09', 'end': '2025-06-20'},

            {'name': 'promo_september', 'start': '2021-09-15', 'end': '2021-09-30'},
            {'name': 'promo_september', 'start': '2022-09-16', 'end': '2022-09-30'},

            {'name': 'promo_q1_2020', 'start': '2020-03-18', 'end': '2020-03-31'},
            {'name': 'promo_q2_2020', 'start': '2020-06-22', 'end': '2020-06-26'},
            {'name': 'promo_harpitnas', 'start': '2020-07-31', 'end': '2020-07-31'},

            {'name': 'promo_juli', 'start': '2022-07-18', 'end': '2022-07-29'},
            {'name': 'promo_oktober', 'start': '2022-10-14', 'end': '2022-10-24'},

            {'name': 'tahun_baru', 'start': '2026-01-01', 'end': '2026-01-10'},
            {'name': 'imlek', 'start': '2026-01-29', 'end': '2026-02-08'},
            {'name': 'promo_q1_2020', 'start': '2026-02-10', 'end': '2026-02-20'},
            {'name': 'ramadan', 'start': '2026-02-28', 'end': '2026-03-31'},
            {'name': 'lebaran', 'start': '2026-04-01', 'end': '2026-04-20'},
            {'name': 'promo_q2_2020', 'start': '2026-05-15', 'end': '2026-05-25'},
            {'name': 'promo_harpitnas', 'start': '2026-05-29', 'end': '2026-05-31'},
            {'name': 'promo_juni', 'start': '2026-06-15', 'end': '2026-06-25'},
            {'name': 'promo_juli', 'start': '2026-07-15', 'end': '2026-07-25'},
            {'name': 'kemerdekaan_ri', 'start': '2026-08-10', 'end': '2026-08-25'},
            {'name': 'promo_9_9', 'start': '2026-09-09', 'end': '2026-09-20'},
            {'name': 'promo_september', 'start': '2026-09-22', 'end': '2026-09-30'},
            {'name': 'promo_10_10', 'start': '2026-10-10', 'end': '2026-10-25'},
            {'name': 'promo_oktober', 'start': '2026-10-26', 'end': '2026-10-31'},
            {'name': 'promo_november', 'start': '2026-11-10', 'end': '2026-11-20'},
            {'name': 'harbolnas', 'start': '2026-12-12', 'end': '2026-12-12'},
            {'name': 'natal_tahun_baru', 'start': '2026-12-23', 'end': '2027-01-10'},
        ]

        promo_holidays_list = []
        for promo in promo_data:
            start_dt = pd.to_datetime(promo['start'])
            end_dt = pd.to_datetime(promo['end'])
            duration = (end_dt - start_dt).days

            promo_holidays_list.append({
                'holiday': promo['name'],
                'ds': start_dt,
                'lower_window': 0,
                'upper_window': duration
            })

        return pd.DataFrame(promo_holidays_list)