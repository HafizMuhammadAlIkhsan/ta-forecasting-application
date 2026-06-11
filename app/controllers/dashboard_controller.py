from flask import Blueprint, render_template, request
from flask_login import login_required
from app.repositories import (
    SimulationRepository,
    ForecastResultRepository,
    ServerEstimationResultRepository,
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

    if selected_simulation_id:
        selected_simulation = SimulationRepository.get_by_id(selected_simulation_id)
        if selected_simulation:
            forecast_results   = ForecastResultRepository.get_by_simulation_id(selected_simulation_id)
            estimation_results = ServerEstimationResultRepository.get_by_simulation_id(selected_simulation_id)

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

            history_data = []
            for pid in package_ids:
                monthly_df = ForecastService._aggregate_monthly(pid)
                if monthly_df is None:
                    continue
                for _, row in monthly_df.tail(12).iterrows():
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
            estimation_data = forecast_only[:selected_simulation.horizon_months]

    return render_template(
        "dashboard/index.html",
        simulations=simulations,
        selected_simulation=selected_simulation,
        estimation_data=estimation_data,
        forecast_data=forecast_data,
        history_data=history_data,
        package_ids=package_ids,
    )
