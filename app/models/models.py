from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"


class Dataset(db.Model):
    __tablename__ = "dataset"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    package_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    total_subscribe = db.Column(db.Integer, nullable=False, default=0)
    total_terminate = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("package_id", "date", name="uq_dataset_package_date"),
    )

    def __repr__(self):
        return f"<Dataset package_id={self.package_id} date={self.date}>"


class SpecificationVM(db.Model):
    """Spesifikasi resource per package/VM (diisi melalui seeder)."""

    __tablename__ = "specification_vm"

    package_id = db.Column(db.Integer, primary_key=True)
    cpu = db.Column(db.Float, nullable=False)
    ram = db.Column(db.Float, nullable=False)
    storage = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<SpecificationVM package_id={self.package_id} cpu={self.cpu}>"


class ServerForecastSimulation(db.Model):
    """Menyimpan parameter input setiap kali user menjalankan simulasi forecasting."""

    __tablename__ = "server_forecast_simulation"

    simulation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    server_utilization_percent = db.Column(db.Float, nullable=False)
    horizon_months = db.Column(db.Integer, nullable=False)
    capacity_cpu = db.Column(db.Float, nullable=False)
    capacity_ram = db.Column(db.Float, nullable=False)
    capacity_storage = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(ZoneInfo("Asia/Jakarta")),
    )

    forecast_results = db.relationship(
        "ForecastResult",
        backref="simulation",
        lazy=True,
        cascade="all, delete-orphan",
    )
    estimation_results = db.relationship(
        "ServerEstimationResult",
        backref="simulation",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<ServerForecastSimulation id={self.simulation_id} "
            f"created_at={self.created_at}>"
        )


class ForecastResult(db.Model):
    """Hasil forecasting subscribe dan terminate per package per bulan."""

    __tablename__ = "forecast_result"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    package_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    forecast_subscribe = db.Column(db.Float, nullable=False, default=0.0)
    forecast_terminate = db.Column(db.Float, nullable=False, default=0.0)
    simulation_id = db.Column(
        db.Integer,
        db.ForeignKey("server_forecast_simulation.simulation_id"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "package_id", "date", "simulation_id",
            name="uq_forecast_result_package_date_simulation",
        ),
    )

    def __repr__(self):
        return (
            f"<ForecastResult package_id={self.package_id} "
            f"date={self.date} sim={self.simulation_id}>"
        )


class ServerEstimationResult(db.Model):
    """Hasil estimasi utilisasi server akhir per bulan per simulasi."""

    __tablename__ = "server_estimation_result"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, index=True)
    final_utilization_percentage = db.Column(db.Float, nullable=False, default=0.0)
    simulation_id = db.Column(
        db.Integer,
        db.ForeignKey("server_forecast_simulation.simulation_id"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "simulation_id", "date",
            name="uq_estimation_result_simulation_date",
        ),
    )

    def __repr__(self):
        return (
            f"<ServerEstimationResult date={self.date} "
            f"util={self.final_utilization_percentage:.2f}% sim={self.simulation_id}>"
        )
