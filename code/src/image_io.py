"""
Image I/O utilities for path resolution and image loading.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from PIL import Image


def resolve_image_path(relative_path: str, dataset_dir: Path) -> Path:
    """Resolve an image path relative to the dataset directory.

    Image paths in CSV are like 'images/sample/case_001/img_1.jpg'.
    The dataset_dir is the parent that contains 'images/'.
    """
    rel = relative_path.strip()
    full = dataset_dir / rel
    return full.resolve()


def resolve_all_image_paths(
    image_paths_str: str, dataset_dir: Path
) -> list[tuple[str, Path, bool]]:
    """Resolve all semicolon-separated image paths.

    Returns: list of (image_id, resolved_path, exists)
    """
    results = []
    for path_str in image_paths_str.split(";"):
        path_str = path_str.strip()
        if not path_str:
            continue
        img_id = Path(path_str).stem
        full_path = resolve_image_path(path_str, dataset_dir)
        results.append((img_id, full_path, full_path.exists()))
    return results


def load_image(path: Path) -> Optional[Image.Image]:
    """Load an image file and return a PIL Image, or None on failure."""
    try:
        img = Image.open(path)
        img.load()  # Force load to catch truncated files
        return img
    except Exception:
        return None


def get_image_info(path: Path) -> dict:
    """Get basic image information without full loading."""
    info = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": 0,
        "width": 0,
        "height": 0,
        "format": "",
        "error": None,
    }
    if not path.exists():
        info["error"] = "File not found"
        return info

    try:
        info["size_bytes"] = path.stat().st_size
        with Image.open(path) as img:
            info["width"] = img.width
            info["height"] = img.height
            info["format"] = img.format or ""
    except Exception as e:
        info["error"] = str(e)

    return info


def image_to_base64(path: Path, max_size: int = 1024) -> Optional[str]:
    """Load and resize image, return base64 encoded string."""
    try:
        with Image.open(path) as img:
            # Convert to RGB if needed
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Resize if too large (preserve aspect ratio)
            if max(img.width, img.height) > max_size:
                ratio = max_size / max(img.width, img.height)
                new_w = int(img.width * ratio)
                new_h = int(img.height * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)

            import io
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def load_image_bytes(path: Path) -> Optional[bytes]:
    """Load raw image bytes for API calls."""
    try:
        return path.read_bytes()
    except Exception:
        return None
