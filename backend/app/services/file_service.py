"""
File upload and storage service
"""
import os
import uuid
from typing import Optional, BinaryIO
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from PIL import Image
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings


class FileService:
    """Service for handling file uploads to S3 or local storage"""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        if settings.USE_S3:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        else:
            self.s3_client = None

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        return filename.split(".")[-1].lower() if "." in filename else ""

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        ext = self._get_file_extension(original_filename)
        unique_name = f"{uuid.uuid4()}"
        return f"{unique_name}.{ext}" if ext else unique_name

    def _validate_file(self, file: UploadFile):
        """
        Validate file extension and size

        Args:
            file: Uploaded file

        Raises:
            HTTPException: If file is invalid
        """
        # Check extension
        ext = self._get_file_extension(file.filename)
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type .{ext} not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Check file size (if file.size is available)
        if hasattr(file, "size") and file.size:
            if file.size > settings.MAX_UPLOAD_SIZE:
                max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum size: {max_mb}MB"
                )

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "",
        optimize_image: bool = True
    ) -> dict:
        """
        Upload file to S3 or local storage

        Args:
            file: Uploaded file
            folder: Optional folder/prefix
            optimize_image: Whether to optimize images

        Returns:
            Dict with file info (path, url, filename, size)
        """
        # Validate file
        self._validate_file(file)

        # Generate unique filename
        unique_filename = self._generate_unique_filename(file.filename)
        file_path = os.path.join(folder, unique_filename) if folder else unique_filename

        # Read file content
        content = await file.read()
        file_size = len(content)

        if settings.USE_S3:
            # Upload to S3
            return await self._upload_to_s3(file_path, content, file.content_type, optimize_image)
        else:
            # Save locally
            return await self._save_locally(file_path, content, optimize_image)

    async def _upload_to_s3(
        self,
        file_path: str,
        content: bytes,
        content_type: str,
        optimize_image: bool
    ) -> dict:
        """Upload file to S3"""
        try:
            # Optimize image if enabled
            if optimize_image and content_type.startswith("image/"):
                content = self._optimize_image_content(content)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=file_path,
                Body=content,
                ContentType=content_type
            )

            # Generate URL
            url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{file_path}"

            return {
                "filename": os.path.basename(file_path),
                "path": file_path,
                "url": url,
                "size": len(content),
                "storage": "s3"
            }
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to S3: {str(e)}"
            )

    async def _save_locally(
        self,
        file_path: str,
        content: bytes,
        optimize_image: bool
    ) -> dict:
        """Save file locally"""
        try:
            # Create full path
            full_path = self.upload_dir / file_path

            # Create subdirectories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Optimize image if enabled
            if optimize_image and file_path.lower().endswith((".jpg", ".jpeg", ".png")):
                content = self._optimize_image_content(content)

            # Write file
            with open(full_path, "wb") as f:
                f.write(content)

            # Generate URL (relative path)
            url = f"/uploads/{file_path}"

            return {
                "filename": os.path.basename(file_path),
                "path": str(full_path),
                "url": url,
                "size": len(content),
                "storage": "local"
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file locally: {str(e)}"
            )

    def _optimize_image_content(self, content: bytes, quality: int = 85) -> bytes:
        """Optimize image content"""
        try:
            from io import BytesIO

            img = Image.open(BytesIO(content))

            # Convert RGBA to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Save optimized
            output = BytesIO()
            img.save(output, format="JPEG", optimize=True, quality=quality)
            return output.getvalue()
        except Exception:
            # If optimization fails, return original content
            return content

    async def create_thumbnail(
        self,
        file_path: str,
        size: tuple = (200, 200)
    ) -> Optional[dict]:
        """
        Create thumbnail for an image

        Args:
            file_path: Path to the original image
            size: Thumbnail size (width, height)

        Returns:
            Dict with thumbnail info or None if failed
        """
        try:
            if settings.USE_S3:
                # Download from S3, create thumbnail, upload back
                response = self.s3_client.get_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=file_path
                )
                content = response["Body"].read()
            else:
                # Read local file
                with open(file_path, "rb") as f:
                    content = f.read()

            # Create thumbnail
            from io import BytesIO
            img = Image.open(BytesIO(content))
            img.thumbnail(size)

            # Save thumbnail
            output = BytesIO()
            img.save(output, format="JPEG", quality=85)
            thumbnail_content = output.getvalue()

            # Generate thumbnail path
            base_path, ext = os.path.splitext(file_path)
            thumbnail_path = f"{base_path}_thumb{ext}"

            if settings.USE_S3:
                # Upload thumbnail to S3
                self.s3_client.put_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=thumbnail_path,
                    Body=thumbnail_content,
                    ContentType="image/jpeg"
                )
                url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{thumbnail_path}"
            else:
                # Save thumbnail locally
                with open(thumbnail_path, "wb") as f:
                    f.write(thumbnail_content)
                url = f"/uploads/{thumbnail_path}"

            return {
                "path": thumbnail_path,
                "url": url,
                "size": len(thumbnail_content)
            }
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from S3 or local storage

        Args:
            file_path: Path to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            if settings.USE_S3:
                self.s3_client.delete_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=file_path
                )
            else:
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False


# Create singleton instance
file_service = FileService()
