"""
File processing background tasks
"""
import os
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.config import settings


@celery_app.task(name="process_image")
def process_image(file_path: str, thumbnail_size: tuple = (200, 200)):
    """
    Process and create thumbnail for uploaded image

    Args:
        file_path: Path to the uploaded image
        thumbnail_size: Tuple of (width, height) for thumbnail
    """
    from PIL import Image

    try:
        img = Image.open(file_path)

        # Create thumbnail
        img.thumbnail(thumbnail_size)

        # Save thumbnail
        base_path, ext = os.path.splitext(file_path)
        thumbnail_path = f"{base_path}_thumb{ext}"
        img.save(thumbnail_path)

        return {
            "original": file_path,
            "thumbnail": thumbnail_path
        }
    except Exception as e:
        print(f"Error processing image: {e}")
        return None


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files(days: int = 30):
    """
    Clean up files older than specified days

    Args:
        days: Number of days to keep files
    """
    if not os.path.exists(settings.UPLOAD_DIR):
        return

    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0

    for root, dirs, files in os.walk(settings.UPLOAD_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))

            if file_modified < cutoff_date:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    return {"deleted_count": deleted_count}


@celery_app.task(name="optimize_image")
def optimize_image(file_path: str, quality: int = 85):
    """
    Optimize image file size

    Args:
        file_path: Path to the image
        quality: JPEG quality (1-100)
    """
    from PIL import Image

    try:
        img = Image.open(file_path)

        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Save with optimization
        img.save(file_path, optimize=True, quality=quality)

        return {"path": file_path, "optimized": True}
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return None
