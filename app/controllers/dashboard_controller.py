from flask import Blueprint, render_template, request
from flask_login import login_required
from app.repositories import (
    SimulationRepository,
    ForecastResultRepository,
    ServerEstimationResultRepository,
)

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/", methods=["GET"])
# @login_required
def index():
    simulations = SimulationRepository.get_all_ordered_by_newest()

    selected_simulation_id = request.args.get("simulation_id", type=int)

    if not selected_simulation_id and simulations:
        selected_simulation_id = simulations[0].simulation_id

    selected_simulation = None
    forecast_results = []
    estimation_results = []

    if selected_simulation_id:
        selected_simulation = SimulationRepository.get_by_id(selected_simulation_id)
        if selected_simulation:
            forecast_results = ForecastResultRepository.get_by_simulation_id(
                selected_simulation_id
            )
            estimation_results = ServerEstimationResultRepository.get_by_simulation_id(
                selected_simulation_id
            )

    return render_template(
        "dashboard/index.html",
        simulations=simulations,
        selected_simulation=selected_simulation,
        forecast_results=forecast_results,
        estimation_results=estimation_results,
    )
