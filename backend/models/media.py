"""
Media/Asset model for file management
"""

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, String

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class Media(Base, IDMixin, TimestampMixin):
    """
    Media model for uploaded files (images, videos, documents)
    """

    __tablename__ = "media"

    # Organization (Tenant)
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Uploader
    uploaded_by_id = Column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # File Info
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)  # Storage path
    url = Column(String(1000), nullable=False)  # Public URL

    # File Type
    mime_type = Column(String(100), nullable=False, index=True)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    file_extension = Column(String(20), nullable=True)

    # Media Type Category
    media_type = Column(
        String(20), nullable=False, index=True
    )  # image, video, audio, document, other

    # Image-specific fields
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Alt text for accessibility
    alt_text = Column(String(500), nullable=True)
    description = Column(String(1000), nullable=True)

    # Tags (stored as JSON array)
    tags = Column(String, nullable=True)  # JSON array of strings

    # CDN
    cdn_url = Column(String(1000), nullable=True)

    # Status
    is_public = Column(Boolean, default=False, nullable=False)

    # File metadata (EXIF, etc. - stored as JSON)
    file_metadata = Column(String, nullable=True)  # JSON object

    def __repr__(self):
        return f"<Media(id={self.id}, filename='{self.filename}', type='{self.media_type}')>"
