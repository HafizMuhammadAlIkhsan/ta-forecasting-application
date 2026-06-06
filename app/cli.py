import click
from flask import Blueprint

cli_bp = Blueprint("cli", __name__)

@cli_bp.cli.command("init-db")
def init_db():
    """Buat semua tabel database."""
    from app import db
    db.create_all()
    click.echo("✅ Tabel database berhasil dibuat.")


@cli_bp.cli.command("seed")
def seed():
    """Isi data awal: user dan specification_vm."""
    from app import db
    db.create_all()
    from seeders import seed_users, seed_specification_vm
    seed_users()
    seed_specification_vm()
    click.echo("✅ Semua seeder selesai dijalankan.")

@cli_bp.cli.command("db-reset")
def db_reset():
    """DROP semua tabel + create ulang + seed."""

    from app import db

    click.echo("🧨 Menghapus semua tabel...")
    db.drop_all()

    click.echo("🏗️ Membuat ulang semua tabel...")
    db.create_all()

    click.echo("🌱 Menjalankan seeder...")

    # pakai seeder yang sudah kamu punya biar konsisten
    from seeders import seed_users, seed_specification_vm

    seed_users()
    seed_specification_vm()

    click.echo("✅ DB reset + seed selesai.")