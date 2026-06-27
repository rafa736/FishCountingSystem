"""
FishCounting System v2.0 
============================================================
Mata Kuliah : Pengolahan Citra Digital
Sistem      : Deteksi & Penghitungan Ikan Otomatis — YOLOv8
Author      : Rafa | Teknik Informatika — UMRAH
============================================================
Changelog v2.0:
  - Session history: simpan riwayat deteksi per sesi
  - Endpoint /history untuk ambil riwayat
  - Endpoint /stats untuk ringkasan statistik sesi
  - Endpoint /compare untuk multi-image comparison mode
  - Endpoint /health untuk monitoring status sistem
  - Confidence threshold dinamis via request param
  - Cleanup otomatis file upload lama (>24 jam)
  - Response JSON lebih kaya (processing_time, image_info, etc.)
"""

import os
import uuid
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from utils.detector import FishDetector
from utils.image_processing import ImageProcessor
from utils.helper import (
    allowed_file, get_file_size, format_confidence,
    generate_analysis_text, get_confidence_level, cleanup_old_files
)

# ── Konfigurasi Aplikasi ───────────────────────────────────────────────────────
app = Flask(__name__)

app.config['SECRET_KEY']          = os.environ.get('SECRET_KEY', 'fishcounting-v2-secret')
app.config['UPLOAD_FOLDER']       = os.path.join('static', 'uploads')
app.config['RESULTS_FOLDER']      = os.path.join('static', 'results')
app.config['MAX_CONTENT_LENGTH']  = 16 * 1024 * 1024   # 16 MB
app.config['ALLOWED_EXTENSIONS']  = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
app.config['MODEL_PATH']          = 'best.pt'

os.makedirs(app.config['UPLOAD_FOLDER'],  exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Inisialisasi komponen utama
detector  = FishDetector(model_path=app.config['MODEL_PATH'])
print("="*50)
print("FishCountingSystem v2.0")
print("Loading YOLO model...")
processor = ImageProcessor()

# ── In-memory session history ──────────────────────────────────────────────────
# List of detection records, max 50 entri per server session
_detection_history = []
_history_lock = threading.Lock()
MAX_HISTORY = 50

def _add_to_history(record: dict):
    with _history_lock:
        _detection_history.append(record)
        if len(_detection_history) > MAX_HISTORY:
            _detection_history.pop(0)

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Halaman utama."""
    model_info = detector.get_model_info()
    return render_template('index.html', model_info=model_info)


@app.route('/about')
def about():
    """Halaman informasi proyek."""
    return render_template('about.html')


@app.route('/health')
def health():
    """
    Health-check endpoint untuk monitoring.
    Berguna untuk deployment di Railway / Render / VPS.
    """
    return jsonify({
        'status'      : 'ok',
        'version'     : '2.0.0',
        'model_loaded': detector.get_model_info()['model_loaded'],
        'timestamp'   : datetime.utcnow().isoformat() + 'Z',
        'history_size': len(_detection_history),
    })


@app.route('/detect', methods=['POST'])
def detect():
    """
    Endpoint utama deteksi ikan (v2).
    Tambahan v2:
      - Parameter conf_threshold dari form (opsional)
      - Informasi dimensi gambar di respons
      - Waktu pemrosesan (processing_time_ms)
      - Teks analisis otomatis
      - Confidence level badge
      - Record masuk ke session history
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Tidak ada file yang diunggah.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nama file kosong.'}), 400

    if not allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
        return jsonify({
            'success': False,
            'error'  : 'Format file tidak didukung. Gunakan PNG, JPG, JPEG, WEBP, atau BMP.'
        }), 400

    # Confidence threshold dinamis (default 0.25, range 0.1–0.9)
    try:
        req_conf = float(request.form.get('conf_threshold', detector.conf_threshold))
        req_conf = max(0.10, min(0.90, req_conf))
    except (TypeError, ValueError):
        req_conf = detector.conf_threshold

    try:
        t_start = time.perf_counter()

        unique_id       = str(uuid.uuid4())[:8]
        filename        = secure_filename(file.filename)
        base_name       = os.path.splitext(filename)[0]
        extension       = os.path.splitext(filename)[1].lower()

        upload_filename = f"{unique_id}_{base_name}{extension}"
        result_filename = f"result_{unique_id}_{base_name}{extension}"

        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)

        file.save(upload_path)

        # Informasi gambar
        image_info = processor.get_image_info(upload_path)

        # Preprocessing & deteksi
        processed_path    = processor.preprocess(upload_path)
        detection_results = detector.detect(
            processed_path, result_path, conf_override=req_conf
        )

        t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

        # Pengayaan data
        detection_results['upload_image']        = upload_filename
        detection_results['result_image']        = result_filename
        detection_results['file_size']           = get_file_size(upload_path)
        detection_results['processing_time_ms']  = t_elapsed_ms
        detection_results['image_info']          = image_info
        detection_results['conf_threshold_used'] = req_conf
        detection_results['timestamp']           = datetime.utcnow().isoformat() + 'Z'

        # Format confidence per deteksi
        if detection_results.get('detections'):
            for det in detection_results['detections']:
                det['confidence_display'] = format_confidence(det['confidence'])

        # Teks analisis & badge
        stats = detection_results.get('statistics', {})
        detection_results['analysis_text']    = generate_analysis_text(
            detection_results['fish_count'],
            stats.get('avg_confidence', 0),
            stats.get('max_confidence', 0),
        )
        detection_results['confidence_level'] = get_confidence_level(
            stats.get('avg_confidence', 0)
        )

        # Simpan ke history
        _add_to_history({
            'id'           : unique_id,
            'timestamp'    : detection_results['timestamp'],
            'fish_count'   : detection_results['fish_count'],
            'avg_confidence': stats.get('avg_confidence', 0),
            'upload_image' : upload_filename,
            'result_image' : result_filename,
            'file_size'    : detection_results['file_size'],
            'processing_ms': t_elapsed_ms,
        })

        return jsonify({'success': True, 'data': detection_results})

    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': f'Model tidak ditemukan: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Detection error: {e}")
        return jsonify({'success': False, 'error': f'Terjadi kesalahan saat deteksi: {str(e)}'}), 500


@app.route('/history')
def history():
    """
    Mengembalikan riwayat deteksi sesi ini (JSON).
    Digunakan oleh frontend untuk tab History.
    """
    with _history_lock:
        records = list(reversed(_detection_history))   # terbaru di atas
    return jsonify({'success': True, 'count': len(records), 'data': records})


@app.route('/stats')
def stats():
    """
    Statistik agregat seluruh deteksi dalam sesi ini.
    """
    with _history_lock:
        records = list(_detection_history)

    if not records:
        return jsonify({'success': True, 'data': {
            'total_images'    : 0,
            'total_fish'      : 0,
            'avg_fish_per_img': 0,
            'avg_confidence'  : 0,
            'avg_time_ms'     : 0,
        }})

    total_fish = sum(r['fish_count'] for r in records)
    avg_conf   = round(sum(r['avg_confidence'] for r in records) / len(records), 2)
    avg_time   = round(sum(r['processing_ms']  for r in records) / len(records), 1)

    return jsonify({'success': True, 'data': {
        'total_images'    : len(records),
        'total_fish'      : total_fish,
        'avg_fish_per_img': round(total_fish / len(records), 1),
        'avg_confidence'  : avg_conf,
        'avg_time_ms'     : avg_time,
    }})


@app.route('/download/<filename>')
def download_result(filename):
    """Unduh gambar hasil anotasi."""
    file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File tidak ditemukan.'}), 404
    return send_file(file_path, as_attachment=True,
                     download_name=f"fishcountv2_{filename}")


@app.route('/result')
def result():
    return render_template('result.html')


# ── Cleanup thread (background) ────────────────────────────────────────────────

def _background_cleanup():
    """Hapus file upload & result lebih dari 24 jam setiap 1 jam."""
    while True:
        time.sleep(3600)
        cleanup_old_files(app.config['UPLOAD_FOLDER'])
        cleanup_old_files(app.config['RESULTS_FOLDER'])

threading.Thread(target=_background_cleanup, daemon=True).start()


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  Fish Counting System v2.0 — Portfolio Edition")
    print("  Mata Kuliah : Pengolahan Citra")
    print("  Author      : Rafa | TI — UMRAH")
    print("=" * 60)
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1"
    )
