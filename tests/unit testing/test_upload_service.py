from io import BytesIO
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from app.services.upload_service import UploadService


def make_csv_file(content: str, filename: str = "data.csv") -> FileStorage:
    return FileStorage(stream=BytesIO(content.encode("utf-8")), filename=filename)


# UT-07
def test_rejects_non_csv_extension():
    file = make_csv_file(
        "package_id,date,total_subscribe,total_terminate\n1,2024-01-01,5,2\n",
        filename="data.xlsx",
    )

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "File harus berformat CSV."

# UT-08
def test_rejects_unreadable_csv():
    file = FileStorage(stream=BytesIO(b""), filename="data.csv")

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "File tidak dapat dibaca. Pastikan format CSV valid."

# UT-09
def test_rejects_missing_required_column():
    content = "package_id,total_subscribe,total_terminate\n1,5,2\n"
    file = make_csv_file(content)

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "Kolom tidak ditemukan: date."

# UT-10
@patch("app.services.upload_service.DatasetRepository.bulk_upsert")
def test_accepts_column_aliases(mock_bulk_upsert):
    content = "Package ID,Date,Total Subscribe,Total Terminate\n1,2024-01-01,5,2\n"
    file = make_csv_file(content)

    ok, message = UploadService.validate_and_save(file)

    assert ok is True
    mock_bulk_upsert.assert_called_once()
    records = mock_bulk_upsert.call_args[0][0]
    assert set(records[0].keys()) == {"package_id", "date", "total_subscribe", "total_terminate"}

# UT-11
def test_rejects_invalid_date():
    content = "package_id,date,total_subscribe,total_terminate\n1,not-a-date,5,2\n"
    file = make_csv_file(content)

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "Kolom 'date' tidak dapat diproses sebagai tanggal."


# UT-012: Menolak package_id non integer
def test_rejects_non_integer_package_id():
    content = "package_id,date,total_subscribe,total_terminate\nABC,2024-01-01,5,2\n"
    file = make_csv_file(content)

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "Kolom 'package_id' harus berupa angka integer."


# UT-013: Menolak total_subscribe kosong
def test_rejects_empty_total_subscribe():
    content = "package_id,date,total_subscribe,total_terminate\n1,2024-01-01,,2\n"
    file = make_csv_file(content)

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "Kolom total_subscribe tidak boleh kosong."


# UT-014: Menolak total_terminate kosong
def test_rejects_empty_total_terminate():
    content = "package_id,date,total_subscribe,total_terminate\n1,2024-01-01,5,\n"
    file = make_csv_file(content)

    ok, message = UploadService.validate_and_save(file)

    assert ok is False
    assert message == "Kolom total_terminate tidak boleh kosong."
