import io
import pandas as pd
from app.repositories import DatasetRepository

REQUIRED_COLUMNS = {"package_id", "date", "total_subscribe", "total_terminate"}

COLUMN_ALIASES = {
    "package id": "package_id",
    "total subscribe": "total_subscribe",
    "total terminate": "total_terminate",
}


class UploadService:
    @staticmethod
    def validate_and_save(file_storage) -> tuple[bool, str]:
        if not file_storage.filename.lower().endswith(".csv"):
            return False, "File harus berformat CSV."

        try:
            content = file_storage.read()
            df = pd.read_csv(io.BytesIO(content))
        except Exception:
            return False, "File tidak dapat dibaca. Pastikan format CSV valid."

        df.columns = [
            COLUMN_ALIASES.get(col.strip().lower(), col.strip().lower())
            for col in df.columns
        ]

        missing_columns = REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            return False, f"Kolom tidak ditemukan: {', '.join(sorted(missing_columns))}."

        try:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        except Exception:
            return False, "Kolom 'date' tidak dapat diproses sebagai tanggal."

        try:
            df["package_id"] = pd.to_numeric(df["package_id"], errors="raise").astype(int)
        except Exception:
            return False, "Kolom 'package_id' harus berupa angka integer."

        for col in ("total_subscribe", "total_terminate"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        records = df[list(REQUIRED_COLUMNS)].to_dict(orient="records")

        try:
            DatasetRepository.bulk_upsert(records)
        except Exception as e:
            return False, f"Gagal menyimpan data: {str(e)}"

        return True, f"Berhasil mengunggah {len(records)} baris data."
