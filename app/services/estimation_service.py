import logging
from app.models import ServerForecastSimulation
from app.repositories import (
    ForecastResultRepository,
    SpecificationVMRepository,
    ServerEstimationResultRepository,
    DatasetRepository,
)

logger = logging.getLogger(__name__)

class EstimationService:
    @staticmethod
    def run(simulation: ServerForecastSimulation) -> None:
        forecast_rows = ForecastResultRepository.get_by_simulation_id(
            simulation.simulation_id
        )
        if not forecast_rows:
            logger.warning(
                "[EstimationService] Tidak ada forecast_result untuk simulation_id=%s",
                simulation.simulation_id,
            )
            return

        all_specs = SpecificationVMRepository.get_all_as_dict()

        if not all_specs:
            raise RuntimeError(
                "Tabel specification_vm kosong. "
                "Jalankan seeder untuk mengisi spesifikasi VM sebelum menjalankan forecast."
            )

        last_actual_date = DatasetRepository.get_last_date()

        rows_by_date = {}
        for row in forecast_rows:
            if last_actual_date and row.date <= last_actual_date:
                continue

            if row.date not in rows_by_date:
                rows_by_date[row.date] = []
            rows_by_date[row.date].append(row)

        skipped_packages = set()
        estimation_records = []
        cumulative_net_demand = {}

        for date_obj, daily_rows in sorted(rows_by_date.items()):
            for row in daily_rows:
                spec = all_specs.get(row.package_id)
                if spec is None:
                    skipped_packages.add(row.package_id)
                    continue

                daily_delta = row.forecast_subscribe - row.forecast_terminate
                cumulative_net_demand[row.package_id] = (
                    cumulative_net_demand.get(row.package_id, 0.0) + daily_delta
                )

            total_cpu = 0.0
            total_ram = 0.0
            total_storage = 0.0

            for package_id, net_demand in cumulative_net_demand.items():
                spec = all_specs[package_id]
                total_cpu += net_demand * spec.cpu
                total_ram += net_demand * spec.ram
                total_storage += net_demand * spec.storage

            pct_cpu = (total_cpu / simulation.capacity_cpu * 100) if simulation.capacity_cpu > 0 else 0.0
            pct_ram = (total_ram / simulation.capacity_ram * 100) if simulation.capacity_ram > 0 else 0.0
            pct_storage = (total_storage / simulation.capacity_storage * 100) if simulation.capacity_storage > 0 else 0.0

            avg_resource_pct = (pct_cpu + pct_ram + pct_storage) / 3
            final_utilization = simulation.server_utilization_percent + avg_resource_pct

            estimation_records.append({
                "date": date_obj,
                "final_utilization_percentage": final_utilization,
                "simulation_id": simulation.simulation_id,
            })

        if skipped_packages:
            logger.warning(
                "[EstimationService] %d package dilewati: %s",
                len(skipped_packages),
                sorted(skipped_packages),
            )

        if not cumulative_net_demand or not estimation_records:
            raise RuntimeError(
                "Estimasi tidak menghasilkan data apapun untuk periode masa depan. "
                "Pastikan package_id di tabel specification_vm sesuai dengan dataset."
            )

        ServerEstimationResultRepository.bulk_insert(estimation_records)
        logger.info(
            "[EstimationService] Berhasil menyimpan %d baris estimasi",
            len(estimation_records),
            simulation.simulation_id,
        )
