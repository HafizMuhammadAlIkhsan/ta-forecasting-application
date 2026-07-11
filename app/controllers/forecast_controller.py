from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.services import UploadService, ForecastService, EstimationService
from app.repositories import DatasetRepository, SimulationRepository

forecast_bp = Blueprint("forecast", __name__, url_prefix="/forecast")


class ForecastController:
    @staticmethod
    @login_required
    def index():
        has_data = DatasetRepository.has_data()
        return render_template("forecast/index.html", has_data=has_data)

    @staticmethod
    @login_required
    def upload():
        if "file" not in request.files or request.files["file"].filename == "":
            flash("Tidak ada file yang dipilih.", "danger")
            return redirect(url_for("forecast.index"))

        success, message = UploadService.validate_and_save(request.files["file"])
        flash(message, "success" if success else "danger")
        return redirect(url_for("forecast.index"))

    @staticmethod
    @login_required
    def run_forecast():
        try:
            server_utilization_percent = float(request.form.get("server_utilization_percent", 0))
            horizon_months = int(request.form.get("horizon_months", 6))
            capacity_cpu = float(request.form.get("capacity_cpu", 0))
            capacity_ram = float(request.form.get("capacity_ram", 0))
            capacity_storage = float(request.form.get("capacity_storage", 0))
        except ValueError:
            flash("Input tidak valid. Pastikan semua nilai berupa angka.", "danger")
            return redirect(url_for("forecast.index"))

        if not (4 <= horizon_months <= 12):
            flash("Horizon forecasting harus antara 4 hingga 12 bulan.", "danger")
            return redirect(url_for("forecast.index"))

        if any(v < 0 for v in [server_utilization_percent, capacity_cpu, capacity_ram, capacity_storage]):
            flash("Nilai kapasitas tidak boleh negatif.", "danger")
            return redirect(url_for("forecast.index"))

        if not DatasetRepository.has_data():
            flash("Upload dataset terlebih dahulu sebelum menjalankan forecast.", "warning")
            return redirect(url_for("forecast.index"))

        try:
            simulation = SimulationRepository.create(
                server_utilization_percent=server_utilization_percent,
                horizon_months=horizon_months,
                capacity_cpu=capacity_cpu,
                capacity_ram=capacity_ram,
                capacity_storage=capacity_storage,
            )

            ForecastService.run(simulation)
            EstimationService.run(simulation)

            flash("Forecasting dan estimasi berhasil dijalankan.", "success")
            return redirect(url_for("dashboard.index", simulation_id=simulation.simulation_id))

        except Exception as e:
            flash(f"Terjadi kesalahan saat proses forecasting: {str(e)}", "danger")
            return redirect(url_for("forecast.index"))


forecast_bp.add_url_rule("/", view_func=ForecastController.index, methods=["GET"])
forecast_bp.add_url_rule("/upload", view_func=ForecastController.upload, methods=["POST"])
forecast_bp.add_url_rule("/run-forecast", view_func=ForecastController.run_forecast, methods=["POST"])
