import logging
from app.repositories import (
    ForecastResultRepository,
    SpecificationVMRepository,
    ServerEstimationResultRepository,
)
from app.models import ServerForecastSimulation

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

        records_by_date: dict = {}
        skipped_packages: set = set()

        for row in forecast_rows:
            spec = all_specs.get(row.package_id)

            if spec is None:
                skipped_packages.add(row.package_id)
                continue

            net_demand = row.forecast_subscribe - row.forecast_terminate

            est_cpu     = net_demand * spec.cpu
            est_ram     = net_demand * spec.ram
            est_storage = net_demand * spec.storage

            pct_cpu = (
                (est_cpu / simulation.capacity_cpu * 100)
                if simulation.capacity_cpu > 0
                else 0.0
            )
            pct_ram = (
                (est_ram / simulation.capacity_ram * 100)
                if simulation.capacity_ram > 0
                else 0.0
            )
            pct_storage = (
                (est_storage / simulation.capacity_storage * 100)
                if simulation.capacity_storage > 0
                else 0.0
            )

            avg_resource_pct  = (pct_cpu + pct_ram + pct_storage) / 3
            final_utilization = simulation.server_utilization_percent + avg_resource_pct

            if row.date not in records_by_date:
                records_by_date[row.date] = []
            records_by_date[row.date].append(final_utilization)

        if skipped_packages:
            logger.warning(
                "[EstimationService] %d package tidak memiliki spesifikasi VM "
                "dan dilewati: %s",
                len(skipped_packages),
                sorted(skipped_packages),
            )

        if not records_by_date:
            raise RuntimeError(
                "Estimasi tidak menghasilkan data apapun. "
                "Pastikan package_id di tabel specification_vm sesuai dengan dataset. "
                f"Package di forecast: {sorted({r.package_id for r in forecast_rows})}. "
                f"Package di spec: {sorted(all_specs.keys())}."
            )

        estimation_records = [
            {
                "date": date_obj,
                "final_utilization_percentage": sum(values) / len(values),
                "simulation_id": simulation.simulation_id,
            }
            for date_obj, values in sorted(records_by_date.items())
        ]

        ServerEstimationResultRepository.bulk_insert(estimation_records)
        logger.info(
            "[EstimationService] Berhasil menyimpan %d baris estimasi untuk simulation_id=%s",
            len(estimation_records),
            simulation.simulation_id,
        )