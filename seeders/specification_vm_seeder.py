from app import db
from app.models import SpecificationVM


def seed_specification_vm() -> None:
    """
    Seeder spesifikasi resource per package VM.
    package_id bertipe integer sesuai skema tabel.
    cpu   : jumlah vCPU per subscriber
    ram   : GB RAM per subscriber
    storage: GB storage per subscriber
    """
    specifications = [
        {"package_id": 48, "cpu": 1,  "ram": 1,   "storage": 20},
        {"package_id": 49, "cpu": 2,  "ram": 2,   "storage": 40},
        {"package_id": 51, "cpu": 4,  "ram": 4,   "storage": 70},
        {"package_id": 54, "cpu": 8,  "ram": 8,   "storage": 120},
        {"package_id": 58, "cpu": 16,  "ram": 16,   "storage": 200},
        {"package_id": 63, "cpu": 32,  "ram": 332,   "storage": 320},
    ]

    for spec_data in specifications:
        exists = SpecificationVM.query.filter_by(
            package_id=spec_data["package_id"]
        ).first()
        if not exists:
            db.session.add(SpecificationVM(**spec_data))

    db.session.commit()
    print("✅ SpecificationVM seeded.")
