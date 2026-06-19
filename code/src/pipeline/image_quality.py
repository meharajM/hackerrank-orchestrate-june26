"""
Stage 2 component: Lightweight image-quality prechecks using Pillow.
Detects obvious unreadability, low light, glare, and blur.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

logger = logging.getLogger(__name__)


def check_image_quality(image_path: Path) -> list[str]:
    """Perform quick heuristic quality checks on a local image.
    
    Returns a list of matching RiskFlag string values (e.g. 'blurry_image', 'low_light_or_glare').
    """
    quality_flags = []
    
    if not image_path.exists():
        return ["damage_not_visible"]  # Missing image behaves as damage not visible / unusable

    try:
        with Image.open(image_path) as img:
            # 1. Force loading image data to verify load success
            img.verify()
    except Exception as e:
        logger.warning(f"Failed to load/verify image {image_path}: {e}")
        return ["blurry_image"]  # Unreadable file treated as blurry/unusable

    try:
        with Image.open(image_path) as img:
            # Convert to grayscale for calculations
            gray = img.convert("L")
            
            # Get stats
            stat = ImageStat.Stat(gray)
            mean_brightness = stat.mean[0]
            var = stat.var[0]
            
            # Check for low light or extreme glare
            # Average pixel brightness in 0-255 scale
            if mean_brightness < 25.0:
                quality_flags.append("low_light_or_glare")
            elif mean_brightness > 230.0:
                quality_flags.append("low_light_or_glare")
            else:
                # Check for large concentrated glare regions (e.g. flash reflection)
                # Compute fraction of pixels that are near-saturated white
                glare_mask = gray.point(lambda p: 255 if p > 250 else 0)
                glare_mean = ImageStat.Stat(glare_mask).mean[0]
                saturated_ratio = glare_mean / 255.0
                if saturated_ratio > 0.15:
                    quality_flags.append("low_light_or_glare")

            # Simple Edge-based Blur Detection
            # Resize image to a constant size (e.g., 256x256) to ensure consistent metrics regardless of original resolution
            small_gray = gray.resize((256, 256))
            edges = small_gray.filter(ImageFilter.FIND_EDGES)
            edge_stat = ImageStat.Stat(edges)
            mean_edge_intensity = edge_stat.mean[0]
            
            # If the mean intensity of edges is very low, the image lacks sharp details/transitions
            if mean_edge_intensity < 2.5:
                quality_flags.append("blurry_image")

    except Exception as e:
        logger.error(f"Error during quality checks on {image_path}: {e}")
        quality_flags.append("blurry_image")

    return list(set(quality_flags))
