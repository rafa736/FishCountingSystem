"""
utils/detector.py  —  FishCounting v2.0
=========================================
Upgrade dari v1:
  - conf_override per-call (confidence threshold dinamis)
  - Label confidence per bounding box (Tinggi / Cukup / Rendah)
  - Historgram distribusi confidence (10-bucket)
  - Grid density map (4x4) untuk menunjukkan sebaran ikan
  - Versi sistem diupdate ke 2.0.0
"""

import os
import numpy as np
from PIL import Image

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARNING] Ultralytics tidak tersedia. Mode demo diaktifkan.")


class FishDetector:
    """
    Kelas utama deteksi ikan YOLOv8 — versi 2.0.

    Attributes:
        model_path      (str)  : Path file model .pt
        conf_threshold  (float): Default confidence threshold
        iou_threshold   (float): Threshold IoU untuk NMS
    """

    SYSTEM_VERSION = '2.0.0'

    def __init__(self, model_path: str = 'best.pt',
                 conf_threshold: float = 0.25,
                 iou_threshold:  float = 0.45):
        self.model_path     = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold  = iou_threshold
        self.model          = None
        self._load_model()

    # ── Private ─────────────────────────────────────────────────────────────────

    def _load_model(self):
        if not YOLO_AVAILABLE:
            print("[INFO] Ultralytics tidak tersedia. Mode demo aktif.")
            return
        try:
            if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 0:
                self.model = YOLO(self.model_path)
                print(f"[INFO] Model dimuat: {self.model_path}")
            else:
                self.model = YOLO("yolov8n.pt")
                print("[INFO] Menggunakan yolov8n.pt (fallback)")
        except Exception as e:
            print(f"[WARNING] Gagal memuat model: {e}")
            self.model = None

    # ── Public ──────────────────────────────────────────────────────────────────

    def detect(self, image_path: str, output_path: str,
               conf_override: float = None) -> dict:
        """
        Menjalankan deteksi YOLOv8.

        Args:
            image_path    (str)           : Path gambar input.
            output_path   (str)           : Path output gambar beranotasi.
            conf_override (float | None)  : Override confidence threshold sementara.

        Returns:
            dict: fish_count, detections, statistics, density_map, conf_histogram.
        """
        conf = conf_override if conf_override is not None else self.conf_threshold

        if self.model is None or not YOLO_AVAILABLE:
            return self._demo_result(output_path, conf)

        results = self.model.predict(
            source=image_path,
            conf=conf,
            iou=self.iou_threshold,
            save=False,
            verbose=False,
        )

        detections  = []
        confidences = []
        image_w, image_h = self._get_image_size(image_path)

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i, box in enumerate(boxes):
                c    = float(box.conf[0])
                cls  = int(box.cls[0])
                xyxy = box.xyxy[0].tolist()

                confidences.append(c)
                detections.append({
                    'id'               : i + 1,
                    'confidence'       : round(c * 100, 2),
                    'class_id'         : cls,
                    'class_name'       : 'Fish',
                    'bbox'             : [round(v, 1) for v in xyxy],
                    'status'           : 'Terdeteksi',
                    'confidence_label' : self._conf_label(c),
                })

            annotated = result.plot()
            self._save_annotated(annotated, output_path)

        statistics    = self._compute_statistics(confidences)
        density_map   = self._compute_density_map(detections, image_w, image_h)
        conf_histogram = self._conf_histogram(confidences)

        return {
            'fish_count'    : len(detections),
            'detections'    : detections,
            'statistics'    : statistics,
            'density_map'   : density_map,
            'conf_histogram': conf_histogram,
        }

    def get_model_info(self) -> dict:
        return {
            'model_name'      : 'YOLOv8',
            'detection_class' : 'Fish (Ikan)',
            'framework'       : 'PyTorch / Ultralytics',
            'version'         : self.SYSTEM_VERSION,
            'conf_threshold'  : self.conf_threshold,
            'iou_threshold'   : self.iou_threshold,
            'model_file'      : self.model_path,
            'model_loaded'    : self.model is not None,
        }

    # ── Private helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _get_image_size(image_path: str):
        try:
            with Image.open(image_path) as img:
                return img.size   # (width, height)
        except Exception:
            return (640, 640)

    @staticmethod
    def _conf_label(conf: float) -> str:
        """Kembalikan label tekstual confidence."""
        if conf >= 0.85:
            return 'Sangat Tinggi'
        elif conf >= 0.70:
            return 'Tinggi'
        elif conf >= 0.50:
            return 'Cukup'
        else:
            return 'Rendah'

    @staticmethod
    def _save_annotated(annotated_array, output_path: str):
        Image.fromarray(annotated_array).save(output_path)

    @staticmethod
    def _compute_statistics(confidences: list) -> dict:
        if not confidences:
            return {
                'avg_confidence'   : 0.0,
                'max_confidence'   : 0.0,
                'min_confidence'   : 0.0,
                'total_detections' : 0,
                'std_confidence'   : 0.0,
            }
        arr = np.array(confidences) * 100
        return {
            'avg_confidence'   : round(float(np.mean(arr)),   2),
            'max_confidence'   : round(float(np.max(arr)),    2),
            'min_confidence'   : round(float(np.min(arr)),    2),
            'total_detections' : len(confidences),
            'std_confidence'   : round(float(np.std(arr)),    2),
        }

    @staticmethod
    def _compute_density_map(detections: list, img_w: int, img_h: int,
                              grid_rows: int = 4, grid_cols: int = 4) -> list:
        """
        Bagi gambar menjadi grid 4x4 dan hitung jumlah ikan per sel.
        Returns list of {row, col, count} untuk heatmap frontend.
        """
        grid = [[0] * grid_cols for _ in range(grid_rows)]

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            col = min(int(cx / img_w * grid_cols), grid_cols - 1)
            row = min(int(cy / img_h * grid_rows), grid_rows - 1)
            grid[row][col] += 1

        result = []
        for r in range(grid_rows):
            for c in range(grid_cols):
                result.append({'row': r, 'col': c, 'count': grid[r][c]})
        return result

    @staticmethod
    def _conf_histogram(confidences: list, bins: int = 10) -> list:
        """
        Histogram distribusi confidence dalam 10 bucket (0–100%).
        Returns list of {range_label, count}.
        """
        if not confidences:
            return [{'label': f'{i*10}-{(i+1)*10}%', 'count': 0} for i in range(bins)]

        arr    = np.array(confidences) * 100
        counts = [0] * bins
        for v in arr:
            idx = min(int(v // 10), bins - 1)
            counts[idx] += 1

        return [
            {'label': f'{i*10}–{(i+1)*10}%', 'count': counts[i]}
            for i in range(bins)
        ]

    @staticmethod
    def _demo_result(output_path: str, conf: float = 0.25) -> dict:
        """Simulasi ketika YOLO tidak tersedia."""
        import random, shutil

        demo_confs = [round(random.uniform(conf, 0.98), 4)
                      for _ in range(random.randint(5, 15))]
        detections = [
            {
                'id'               : i + 1,
                'confidence'       : round(c * 100, 2),
                'class_id'         : 0,
                'class_name'       : 'Fish',
                'bbox'             : [
                    random.randint(0, 500), random.randint(0, 400),
                    random.randint(50, 600), random.randint(50, 480)
                ],
                'status'           : 'Terdeteksi',
                'confidence_label' : FishDetector._conf_label(c),
            }
            for i, c in enumerate(demo_confs)
        ]

        input_guess = output_path.replace('result_', '').replace('results', 'uploads')
        if os.path.exists(input_guess):
            shutil.copy(input_guess, output_path)

        stats = FishDetector._compute_statistics(demo_confs)
        return {
            'fish_count'    : len(detections),
            'detections'    : detections,
            'statistics'    : stats,
            'density_map'   : FishDetector._compute_density_map(detections, 640, 480),
            'conf_histogram': FishDetector._conf_histogram(demo_confs),
            'demo_mode'     : True,
        }
