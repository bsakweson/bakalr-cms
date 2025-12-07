"""
Storage backend abstraction for local and S3 storage
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

import boto3
from botocore.exceptions import ClientError

from backend.core.config import Settings

settings = Settings()


class StorageBackend(ABC):
    """Abstract storage backend"""

    @abstractmethod
    def save_file(self, file_content: bytes, file_path: str) -> str:
        """
        Save file to storage

        Args:
            file_content: File content as bytes
            file_path: Relative file path

        Returns:
            Public URL or path to access the file
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from storage

        Args:
            file_path: File path to delete

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> str:
        """
        Get public URL for file

        Args:
            file_path: File path

        Returns:
            Public URL to access file
        """
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists

        Args:
            file_path: File path

        Returns:
            True if file exists
        """
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir.mkdir(exist_ok=True, parents=True)

    def save_file(self, file_content: bytes, file_path: str) -> str:
        """Save file to local filesystem"""
        full_path = self.base_dir / file_path
        full_path.parent.mkdir(exist_ok=True, parents=True)

        with open(full_path, "wb") as f:
            f.write(file_content)

        # Return relative path as URL
        return f"/api/v1/media/files/{Path(file_path).name}"

    def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            full_path = Path(file_path)
            if not full_path.is_absolute():
                full_path = self.base_dir / file_path

            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False

    def get_file_url(self, file_path: str) -> str:
        """Get URL for local file"""
        filename = Path(file_path).name
        return f"/api/v1/media/files/{filename}"

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists locally"""
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = self.base_dir / file_path
        return full_path.exists()

    def get_full_path(self, file_path: str) -> Path:
        """Get full filesystem path"""
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = self.base_dir / file_path
        return full_path


class S3StorageBackend(StorageBackend):
    """AWS S3 or S3-compatible storage"""

    def __init__(self):
        # Initialize S3 client
        s3_config = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
        }

        # Add endpoint URL for S3-compatible services (e.g., MinIO)
        if settings.S3_ENDPOINT_URL:
            s3_config["endpoint_url"] = settings.S3_ENDPOINT_URL
            s3_config["use_ssl"] = settings.S3_USE_SSL

        self.s3_client = boto3.client("s3", **s3_config)
        self.bucket_name = settings.S3_BUCKET_NAME
        self.public_url = settings.S3_PUBLIC_URL

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Bucket doesn't exist, create it
                try:
                    if settings.AWS_REGION == "us-east-1":
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
                        )
                except ClientError:
                    pass  # Bucket might have been created by another process

    def save_file(self, file_content: bytes, file_path: str) -> str:
        """Save file to S3"""
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=self._guess_content_type(file_path),
            )

            # Return proxy URL so files are served through the API
            # This avoids exposing MinIO/S3 directly to browsers
            from pathlib import Path

            return f"/api/v1/media/proxy/{Path(file_path).name}"
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {str(e)}")

    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            # Extract S3 key from file_path (remove bucket/domain if present)
            s3_key = file_path.replace(f"s3://{self.bucket_name}/", "")

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_file_url(self, file_path: str) -> str:
        """Get public URL for S3 file"""
        # Use custom CDN URL if configured
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{file_path}"

        # Use S3 endpoint URL if configured
        if settings.S3_ENDPOINT_URL:
            return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{file_path}"

        # Default AWS S3 URL
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_path}"

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            s3_key = file_path.replace(f"s3://{self.bucket_name}/", "")
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def _guess_content_type(self, file_path: str) -> str:
        """Guess content type from file extension"""
        import mimetypes

        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or "application/octet-stream"

    def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for temporary access

        Args:
            file_path: S3 key
            expiration: URL expiration in seconds

        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def get_file_content(self, file_path: str) -> Tuple[bytes, str]:
        """
        Download file content from S3

        Args:
            file_path: S3 key

        Returns:
            Tuple of (file_content, content_type)
        """
        try:
            s3_key = file_path.replace(f"s3://{self.bucket_name}/", "")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            return content, content_type
        except ClientError as e:
            raise Exception(f"Failed to download from S3: {str(e)}")


def get_storage_backend() -> StorageBackend:
    """
    Get configured storage backend

    Returns:
        StorageBackend instance (Local or S3)
    """
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    else:
        return LocalStorageBackend()
