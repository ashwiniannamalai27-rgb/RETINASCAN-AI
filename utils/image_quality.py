import math
from typing import Dict, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError


def validate_image_quality(image_path: str) -> Dict[str, object]:
    """
    Lightweight technical quality validation for uploaded retinal images.

    This is not a medical suitability check. It only rejects clearly unusable
    images before the CNN is run, based on simple technical quality signals.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            arr = np.asarray(img, dtype=np.float32)
    except (UnidentifiedImageError, OSError, ValueError):
        return {
            "is_valid": False,
            "reason": "The uploaded image could not be read. Please upload a clearer retinal image.",
        }

    if arr.size == 0:
        return {
            "is_valid": False,
            "reason": "The uploaded image is empty. Please upload a clearer retinal image.",
        }

    h, w = arr.shape[:2]
    if h < 64 or w < 64:
        return {
            "is_valid": False,
            "reason": "The uploaded image is too small to be processed. Please upload a clearer retinal image.",
        }

    gray = arr.mean(axis=2)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    dark_pixels = float(np.mean(gray < 25))
    bright_pixels = float(np.mean(gray > 245))

    if brightness < 20:
        return {
            "is_valid": False,
            "reason": "The uploaded image looks too dark. Please upload a clearer retinal image.",
        }

    if brightness > 245:
        return {
            "is_valid": False,
            "reason": "The uploaded image looks too bright. Please upload a clearer retinal image.",
        }

    if contrast < 18:
        return {
            "is_valid": False,
            "reason": "The uploaded image appears to have very low contrast. Please upload a clearer retinal image.",
        }

    if dark_pixels > 0.75 or bright_pixels > 0.75:
        return {
            "is_valid": False,
            "reason": "The uploaded image appears unusable for screening. Please upload a clearer retinal image.",
        }

    return {
        "is_valid": True,
        "reason": "Image quality check passed.",
        "brightness": brightness,
        "contrast": contrast,
    }


__all__ = ["validate_image_quality"]
