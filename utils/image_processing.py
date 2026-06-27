"""
utils/image_processing.py
Modul preprocessing gambar sebelum diproses oleh model YOLOv8.
Versi ringan tanpa OpenCV (Railway Friendly).
"""

import os
from PIL import Image


class ImageProcessor:
    """
    Kelas preprocessing sederhana untuk validasi gambar.
    YOLOv8 sudah menangani resize dan preprocessing internal,
    sehingga modul ini hanya memastikan file gambar valid.
    """

    DEFAULT_SIZE = (640, 640)

    def __init__(self, target_size=None, maintain_aspect=True):
        self.target_size = target_size or self.DEFAULT_SIZE
        self.maintain_aspect = maintain_aspect

    def preprocess(self, image_path: str) -> str:
        """
        Validasi gambar dan mengembalikan path asli.
        """
        if self._read_image(image_path) is None:
            raise ValueError(f"Gambar tidak dapat dibaca: {image_path}")

        return image_path

    def get_image_info(self, image_path: str) -> dict:
        """
        Mengambil informasi dasar gambar.
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                channels = len(img.getbands())

            size_kb = round(os.path.getsize(image_path) / 1024, 2)

            return {
                'width': width,
                'height': height,
                'channels': channels,
                'size_kb': size_kb
            }

        except Exception:
            return {}

    @staticmethod
    def _read_image(image_path: str):
        """
        Validasi apakah file gambar dapat dibuka.
        """
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return None