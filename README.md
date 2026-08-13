
# Aplikasi Forecasting Kebutuhan Server

Aplikasi web ini dibangun menggunakan Flask untuk melakukan forecasting kebutuhan sumber daya server berdasarkan data historis penggunaan layanan. Aplikasi ini memungkinkan pengguna untuk mengunggah dataset, menjalankan simulasi peramalan dengan parameter yang dapat disesuaikan, dan melihat hasil visualisasi melalui dashboard.

## Fitur Utama

-   **Autentikasi Pengguna**: Sistem login, logout, dan manajemen profil pengguna.
-   **Manajemen Dataset**: Pengguna dapat mengunggah file dataset historis dalam format CSV.
-   **Simulasi Forecasting**: Menjalankan proses peramalan menggunakan model Prophet dengan parameter yang dapat diatur seperti horison waktu dan utilisasi server.
-   **Estimasi Kebutuhan**: Mengestimasi kebutuhan CPU, RAM, dan storage di masa depan berdasarkan hasil peramalan.
-   **Dashboard**: Visualisasi data historis, hasil peramalan, dan metrik akurasi (MAE, RMSE, SMAPE) untuk setiap simulasi.

## Teknologi yang Digunakan

-   **Backend**: Python, Flask, Flask-SQLAlchemy, Flask-Login
-   **Mesin Forecasting**: Facebook Prophet
-   **Database**: Menggunakan Schema `SQLAlchemy`, dapat berjalan di atas SQLite, PostgreSQL, dll.
-   **Frontend**: HTML, Jinja2, JavaScript, Chart.js (untuk visualisasi)
-   **Testing**: Pytest
-   **Containerization**: Docker, Docker Compose

## Struktur Folder Proyek

```
.
├── app/                  # Direktori utama aplikasi Flask
│   ├── controllers/      # Logika untuk handle request (Routes)
│   ├── models/           # Definisi model database (SQLAlchemy)
│   ├── services/         # Logika bisnis (forecasting, estimasi)
│   ├── repositories/     # Akses dan manipulasi data ke database
│   ├── templates/        # File-file template HTML (Jinja2)
│   ├── static/           # Aset statis (CSS, JavaScript, gambar)
│   └── cli.py            # Perintah kustom untuk Flask CLI
├── config/               # Konfigurasi aplikasi
├── seeders/              # Skrip untuk seeding data awal
├── tests/                # Unit & Integration tests
├── requirements.txt      # Dependensi Python
├── run.py                # Titik masuk untuk menjalankan aplikasi
├── Dockerfile            # Konfigurasi untuk membangun image Docker
└── docker-compose.yml    # Konfigurasi untuk menjalankan aplikasi dengan Docker
```

## Instalasi dan Menjalankan Aplikasi

### 1. Prasyarat

-   Python 3.9+
-   Docker dan Docker Compose (opsional, untuk metode Docker)
-   Git

### 2. Konfigurasi Awal

Salin file `.env.example` (jika ada) menjadi `.env` atau buat file `.env` baru di root proyek dan isi variabel yang dibutuhkan. Variabel minimal yang dibutuhkan biasanya:

```env
# Kunci rahasia untuk aplikasi Flask (buat nilai acak dan aman)
SECRET_KEY='your-super-secret-key'

# URI untuk koneksi database
DATABASE_URI='sqlite:///../instance/app.db'

# Konfigurasi email untuk fitur lupa password
MAIL_SERVER='smtp.example.com'
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME='your-email@example.com'
MAIL_PASSWORD='your-email-password'
MAIL_DEFAULT_SENDER='sender@example.com'
```

### 3. Menjalankan Secara Lokal (Tanpa Docker)

1.  **Clone repository:**
    ```bash
    git clone https://github.com/your-username/ta-forecasting-application.git
    cd ta-forecasting-application
    ```

2.  **Buat dan aktifkan virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Untuk Linux/macOS
    venv\Scripts\activate     # Untuk Windows
    ```

3.  **Install dependensi:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Inisialisasi dan seeding database:**
    Gunakan perintah Flask CLI untuk membuat tabel dan mengisi data awal.
    ```bash
    flask cli db-reset
    ```

5.  **Jalankan aplikasi:**
    ```bash
    python run.py
    ```

    Aplikasi akan berjalan di `http://127.0.0.1:5000`.

### 4. Menjalankan dengan Docker

Metode ini lebih sederhana karena semua dependensi sudah diatur dalam container.

1.  **Pastikan Docker sudah berjalan.**

2.  **Jalankan Docker Compose:**
    ```bash
    docker-compose up --build
    ```
    Perintah ini akan membangun image dan menjalankan container. Aplikasi akan dapat diakses di `http://localhost:5000`.

3.  **Inisialisasi Database (Hanya untuk pertama kali):**
    Buka terminal baru, dan jalankan perintah berikut untuk membuat tabel dan mengisi data awal di dalam container yang sedang berjalan.
    ```bash
    docker-compose exec flask_app flask cli db-reset
    ```
    Setelah itu, refresh halaman browser Anda.

## Perintah CLI yang Tersedia

Aplikasi ini menyediakan beberapa perintah kustom melalui Flask CLI:

-   **`flask cli init-db`**: Membuat semua tabel database berdasarkan model yang ada.
-   **`flask cli seed`**: Mengisi data awal untuk tabel `user` dan `specification_vm`.
-   **`flask cli db-reset`**: Menghapus semua data, membuat ulang semua tabel, dan menjalankan seeder. **PERHATIAN: Perintah ini akan menghapus semua data!**

## Menjalankan Test

Untuk menjalankan serangkaian tes dan memastikan semua fungsi berjalan dengan baik, gunakan `pytest`:

```bash
pytest
```
