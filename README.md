# FishCounting AI v2.0 — Portfolio Edition

Sistem deteksi dan penghitungan ikan otomatis berbasis YOLOv8 + Flask.  
Dikembangkan untuk Mata Kuliah **Pengolahan Citra Digital** — Teknik Informatika, UMRAH.

---

## Fitur v2.0 (Upgrade dari v1)

| Fitur | v1 | v2 |
|-------|----|----|
| Deteksi YOLOv8 | ✅ | ✅ |
| Confidence slider dinamis | ❌ | ✅ |
| Density Map 4×4 | ❌ | ✅ |
| Histogram distribusi confidence | ❌ | ✅ |
| Tabel deteksi per bounding box | ❌ | ✅ |
| Session history | ❌ | ✅ |
| Session stats bar (animasi) | ❌ | ✅ |
| Endpoint `/history`, `/stats`, `/health` | ❌ | ✅ |
| Waktu proses (ms) di respons | ❌ | ✅ |
| Cleanup file otomatis (background thread) | ❌ | ✅ |
| Label confidence per deteksi (Tinggi/Cukup/Rendah) | ❌ | ✅ |
| Std deviasi confidence | ❌ | ✅ |

---

## Struktur Proyek

```
FishCountingV2/
├── app.py                  # Flask app (routes + session history)
├── best.pt                 # Model YOLOv8 terlatih
├── requirements.txt
├── Procfile
├── nixpacks.toml
├── utils/
│   ├── detector.py         # FishDetector (density map, histogram, labels)
│   ├── image_processing.py # ImageProcessor
│   └── helper.py           # Utilities
├── templates/
│   ├── index.html          # Halaman utama (v2 UI)
│   └── about.html
└── static/
    ├── css/style.css       # Ocean dashboard theme v2
    ├── js/script.js        # Frontend logic v2
    ├── uploads/
    └── results/
```

---

## Instalasi & Menjalankan

```bash
# 1. Clone / ekstrak proyek
cd FishCountingV2

# 2. Install dependensi
pip install -r requirements.txt

# 3. Jalankan
python app.py
```

Buka browser di `http://localhost:5000`

---

## API Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/` | Halaman utama |
| POST | `/detect` | Deteksi ikan (form: `file`, `conf_threshold`) |
| GET | `/history` | Riwayat deteksi sesi ini (JSON) |
| GET | `/stats` | Statistik agregat sesi (JSON) |
| GET | `/health` | Health check (JSON) |
| GET | `/download/<filename>` | Unduh gambar hasil |

---

## Tech Stack

- **Model:** YOLOv8 (Ultralytics)
- **Backend:** Python 3.11 + Flask
- **Image:** Pillow
- **Frontend:** Vanilla JS + CSS custom properties (no framework)
- **Deployment:** Railway / Render / VPS

---

*Teknik Informatika — Universitas Maritim Raja Ali Haji (UMRAH) · 2026*
