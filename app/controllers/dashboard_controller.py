import pandas as pd

from flask import Blueprint, render_template, request
from flask_login import login_required
from app.repositories import (
    SimulationRepository,
    ForecastResultRepository,
    ServerEstimationResultRepository,
    ForecastMetricRepository,
)
from app.services.forecast_service import ForecastService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/", methods=["GET"])
@login_required
def index():
    simulations = SimulationRepository.get_all_ordered_by_newest()

    selected_simulation_id = request.args.get("simulation_id", type=int)
    if not selected_simulation_id and simulations:
        selected_simulation_id = simulations[0].simulation_id

    selected_simulation = None
    estimation_data  = []
    forecast_data    = []
    history_data     = []
    package_ids      = []
    forecast_metrics = {}

    if selected_simulation_id:
        selected_simulation = SimulationRepository.get_by_id(selected_simulation_id)
        if selected_simulation:
            forecast_results   = ForecastResultRepository.get_by_simulation_id(selected_simulation_id)
            estimation_results = ServerEstimationResultRepository.get_by_simulation_id(selected_simulation_id)
            metric_results     = ForecastMetricRepository.get_by_simulation_id(selected_simulation_id)

            forecast_data = [
                {
                    "package_id":         r.package_id,
                    "date":               r.date.strftime("%Y-%m-%d"),
                    "forecast_subscribe": round(r.forecast_subscribe, 2),
                    "forecast_terminate": round(r.forecast_terminate, 2),
                }
                for r in forecast_results
            ]

            package_ids = sorted({r["package_id"] for r in forecast_data})

            for m in metric_results:
                forecast_metrics[m.package_id] = {
                    "subscribe": {
                        "mae": m.subscribe_mae,
                        "rmse": m.subscribe_rmse,
                        "smape": m.subscribe_smape,
                    },
                    "terminate": {
                        "mae": m.terminate_mae,
                        "rmse": m.terminate_rmse,
                        "smape": m.terminate_smape,
                    },
                }

            history_data = []
            for pid in package_ids:
                daily_df = ForecastService._aggregate_daily(pid)
                if daily_df is None:
                    continue

                for _, row in daily_df.iterrows():
                    history_data.append({
                        "package_id":      pid,
                        "date":            row["ds"].strftime("%Y-%m-%d"),
                        "total_subscribe": round(float(row["total_subscribe"]), 2),
                        "total_terminate": round(float(row["total_terminate"]), 2),
                    })

            all_estimation = [
                {
                    "date":        r.date.strftime("%Y-%m-%d"),
                    "utilization": round(r.final_utilization_percentage, 2),
                }
                for r in estimation_results
            ]

            max_hist_date = max((r["date"] for r in history_data), default=None)
            if max_hist_date:
                forecast_only = [r for r in all_estimation if r["date"] > max_hist_date]
            else:
                forecast_only = sorted(all_estimation, key=lambda r: r["date"])

            forecast_only.sort(key=lambda r: r["date"])
            estimation_data = forecast_only

    return render_template(
        "dashboard/index.html",
        simulations=simulations,
        selected_simulation=selected_simulation,
        estimation_data=estimation_data,
        forecast_data=forecast_data,
        history_data=history_data,
        package_ids=package_ids,
        forecast_metrics=forecast_metrics,
    )