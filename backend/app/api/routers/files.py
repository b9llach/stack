"""
File upload endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.db.models.user import User
from app.services.file_service import file_service
from app.tasks.file_tasks import process_image, optimize_image


router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "",
    optimize: bool = True,
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file

    Supports both S3 and local storage based on configuration
    """
    result = await file_service.upload_file(
        file=file,
        folder=folder,
        optimize_image=optimize
    )

    # Queue background task for image processing if it's an image
    if file.content_type and file.content_type.startswith("image/"):
        process_image.delay(result["path"])

    return result


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload user avatar

    Automatically creates thumbnail and updates user profile
    """
    # Upload original
    result = await file_service.upload_file(
        file=file,
        folder=f"avatars/{current_user.id}",
        optimize_image=True
    )

    # Create thumbnail
    thumbnail = await file_service.create_thumbnail(result["path"])

    # Update user avatar
    current_user.avatar_url = result["url"]
    db.add(current_user)
    await db.commit()

    return {
        "avatar": result,
        "thumbnail": thumbnail
    }


@router.delete("/delete")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file

    Args:
        file_path: Path to the file to delete
    """
    success = await file_service.delete_file(file_path)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )

    return {"message": "File deleted successfully"}
