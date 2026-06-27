"""
utils/helper.py
Fungsi-fungsi utilitas umum untuk FishCountingSystem.
Berisi:
  - Validasi ekstensi file
  - Format ukuran file
  - Format confidence
  - Pembuatan keterangan analisis otomatis
  - Pembersihan file lama
"""

import os
import glob
import time


# ── File Utilities ─────────────────────────────────────────────────────────────

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Memeriksa apakah ekstensi file diizinkan.

    Args:
        filename            (str) : Nama file.
        allowed_extensions  (set) : Himpunan ekstensi yang diizinkan.

    Returns:
        bool: True jika ekstensi valid.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_size(file_path: str) -> str:
    """
    Mengembalikan ukuran file dalam format manusiawi (KB / MB).

    Args:
        file_path (str): Path lengkap file.

    Returns:
        str: Ukuran file terformat, contoh '1.23 MB'.
    """
    if not os.path.exists(file_path):
        return 'N/A'

    size_bytes = os.path.getsize(file_path)
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 ** 2):.2f} MB"


def format_confidence(confidence_value: float) -> str:
    """
    Memformat nilai confidence menjadi string persentase.

    Args:
        confidence_value (float): Nilai confidence 0–100.

    Returns:
        str: Contoh '92.35%'
    """
    return f"{confidence_value:.2f}%"


# ── Analysis Text Generator ────────────────────────────────────────────────────

def generate_analysis_text(fish_count: int, avg_confidence: float,
                            max_confidence: float) -> str:
    """
    Menghasilkan keterangan analisis otomatis berdasarkan hasil deteksi.

    Args:
        fish_count       (int)  : Jumlah ikan terdeteksi.
        avg_confidence   (float): Rata-rata confidence (0–100).
        max_confidence   (float): Confidence tertinggi (0–100).

    Returns:
        str: Kalimat analisis dalam Bahasa Indonesia.
    """
    if fish_count == 0:
        return (
            "Model YOLOv8 tidak mendeteksi objek ikan pada citra yang diberikan. "
            "Hal ini dapat disebabkan oleh kualitas gambar yang kurang baik, "
            "pencahayaan yang tidak memadai, atau objek ikan yang terlalu kecil "
            "di luar batas deteksi model."
        )

    # Evaluasi kualitas deteksi
    if avg_confidence >= 90:
        quality_label = "sangat tinggi"
        quality_note  = "Model berhasil mendeteksi ikan dengan keyakinan yang sangat baik."
    elif avg_confidence >= 75:
        quality_label = "tinggi"
        quality_note  = "Model mampu melakukan deteksi dengan baik pada citra yang diberikan."
    elif avg_confidence >= 60:
        quality_label = "cukup"
        quality_note  = "Kualitas deteksi cukup baik meskipun terdapat beberapa ketidakpastian."
    else:
        quality_label = "rendah"
        quality_note  = (
            "Tingkat kepercayaan model relatif rendah; "
            "pertimbangkan untuk menggunakan gambar dengan kualitas lebih baik."
        )

    ekor_text = "ekor" if fish_count > 1 else "ekor"

    return (
        f"Hasil deteksi menunjukkan terdapat {fish_count} {ekor_text} ikan yang berhasil "
        f"dikenali oleh model YOLOv8 dengan tingkat confidence rata-rata {avg_confidence:.1f}% "
        f"dan confidence tertinggi {max_confidence:.1f}%. "
        f"Tingkat keyakinan model dikategorikan sebagai {quality_label}. "
        f"{quality_note}"
    )


def get_confidence_level(avg_confidence: float) -> dict:
    """
    Mengembalikan label dan warna berdasarkan rata-rata confidence.

    Returns:
        dict: {'level': str, 'color': str, 'badge': str}
    """
    if avg_confidence >= 90:
        return {'level': 'Sangat Tinggi', 'color': '#10b981', 'badge': 'success'}
    elif avg_confidence >= 75:
        return {'level': 'Tinggi',        'color': '#3b82f6', 'badge': 'info'}
    elif avg_confidence >= 60:
        return {'level': 'Cukup',         'color': '#f59e0b', 'badge': 'warning'}
    else:
        return {'level': 'Rendah',        'color': '#ef4444', 'badge': 'danger'}


# ── File Cleanup ───────────────────────────────────────────────────────────────

def cleanup_old_files(folder: str, max_age_hours: int = 24,
                      extensions: tuple = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
    """
    Menghapus file lama di folder tertentu untuk menjaga penggunaan disk.

    Args:
        folder        (str) : Folder yang akan dibersihkan.
        max_age_hours (int) : File lebih tua dari ini akan dihapus.
        extensions    (tuple): Ekstensi file yang akan diperiksa.
    """
    if not os.path.exists(folder):
        return

    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0

    for ext in extensions:
        for file_path in glob.glob(os.path.join(folder, f'*{ext}')):
            if os.path.getmtime(file_path) < cutoff:
                try:
                    os.remove(file_path)
                    removed += 1
                except OSError:
                    pass

    if removed:
        print(f"[Cleanup] {removed} file dihapus dari {folder}.")
