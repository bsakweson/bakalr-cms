"""
Media utility functions for file handling
"""
import os
import uuid
import mimetypes
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import hashlib


# Allowed file extensions by category
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.json'}

ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS | 
    ALLOWED_VIDEO_EXTENSIONS | 
    ALLOWED_AUDIO_EXTENSIONS | 
    ALLOWED_DOCUMENT_EXTENSIONS
)

# File size limits (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB

# Upload directory
UPLOAD_DIR = Path("uploads")
THUMBNAIL_DIR = UPLOAD_DIR / "thumbnails"


def ensure_upload_directories():
    """Ensure upload directories exist"""
    UPLOAD_DIR.mkdir(exist_ok=True)
    THUMBNAIL_DIR.mkdir(exist_ok=True)
    
    # Create subdirectories by type
    for subdir in ['images', 'videos', 'audio', 'documents', 'other']:
        (UPLOAD_DIR / subdir).mkdir(exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension"""
    return Path(filename).suffix.lower()


def get_media_type(mime_type: str, extension: str) -> str:
    """Determine media type category"""
    if extension in ALLOWED_IMAGE_EXTENSIONS or mime_type.startswith('image/'):
        return 'image'
    elif extension in ALLOWED_VIDEO_EXTENSIONS or mime_type.startswith('video/'):
        return 'video'
    elif extension in ALLOWED_AUDIO_EXTENSIONS or mime_type.startswith('audio/'):
        return 'audio'
    elif extension in ALLOWED_DOCUMENT_EXTENSIONS or mime_type.startswith('application/'):
        return 'document'
    else:
        return 'other'


def validate_file_extension(filename: str) -> Tuple[bool, str]:
    """
    Validate file extension
    
    Returns:
        (is_valid, error_message)
    """
    extension = get_file_extension(filename)
    
    if not extension:
        return False, "File has no extension"
    
    if extension not in ALL_ALLOWED_EXTENSIONS:
        return False, f"File type {extension} not allowed"
    
    return True, ""


def validate_file_size(file_size: int, mime_type: str, extension: str) -> Tuple[bool, str]:
    """
    Validate file size based on type
    
    Returns:
        (is_valid, error_message)
    """
    media_type = get_media_type(mime_type, extension)
    
    if media_type == 'image' and file_size > MAX_IMAGE_SIZE:
        return False, f"Image size exceeds {MAX_IMAGE_SIZE // (1024*1024)} MB limit"
    elif media_type == 'video' and file_size > MAX_VIDEO_SIZE:
        return False, f"Video size exceeds {MAX_VIDEO_SIZE // (1024*1024)} MB limit"
    elif media_type == 'audio' and file_size > MAX_AUDIO_SIZE:
        return False, f"Audio size exceeds {MAX_AUDIO_SIZE // (1024*1024)} MB limit"
    elif media_type == 'document' and file_size > MAX_DOCUMENT_SIZE:
        return False, f"Document size exceeds {MAX_DOCUMENT_SIZE // (1024*1024)} MB limit"
    
    return True, ""


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate unique filename with UUID
    
    Args:
        original_filename: Original uploaded filename
        
    Returns:
        Unique filename like "uuid_original.ext"
    """
    extension = get_file_extension(original_filename)
    unique_id = str(uuid.uuid4())
    safe_name = Path(original_filename).stem[:50]  # Limit length
    
    # Remove any unsafe characters
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('-', '_'))
    
    return f"{unique_id}_{safe_name}{extension}"


def get_file_storage_path(filename: str, media_type: str, organization_id: int) -> Path:
    """
    Get storage path for file
    
    Args:
        filename: Generated unique filename
        media_type: Media type category
        organization_id: Organization ID for tenant isolation
        
    Returns:
        Full path where file should be stored
    """
    # Organize by organization and media type
    return UPLOAD_DIR / f"org_{organization_id}" / f"{media_type}s" / filename


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()


def get_image_dimensions(file_path: Path) -> Optional[Tuple[int, int]]:
    """
    Get image dimensions
    
    Args:
        file_path: Path to image file
        
    Returns:
        (width, height) or None if not an image
    """
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception:
        return None


def create_thumbnail(
    source_path: Path,
    output_path: Path,
    max_width: int = 300,
    max_height: int = 300,
    quality: int = 85
) -> Tuple[int, int]:
    """
    Create thumbnail from image
    
    Args:
        source_path: Source image path
        output_path: Output thumbnail path
        max_width: Maximum width
        max_height: Maximum height
        quality: JPEG quality (1-100)
        
    Returns:
        (width, height) of created thumbnail
    """
    with Image.open(source_path) as img:
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Calculate thumbnail size maintaining aspect ratio
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save thumbnail
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        
        return img.size


def optimize_image(
    image_path: Path,
    quality: int = 85,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None
) -> Tuple[int, int]:
    """
    Optimize image file
    
    Args:
        image_path: Path to image
        quality: JPEG quality
        max_width: Optional max width to resize to
        max_height: Optional max height to resize to
        
    Returns:
        (width, height) after optimization
    """
    with Image.open(image_path) as img:
        # Convert RGBA to RGB if saving as JPEG
        if img.mode == 'RGBA' and image_path.suffix.lower() in ['.jpg', '.jpeg']:
            img = img.convert('RGB')
        
        # Resize if dimensions specified
        if max_width or max_height:
            img.thumbnail(
                (max_width or img.width, max_height or img.height),
                Image.Resampling.LANCZOS
            )
        
        # Save optimized
        img.save(image_path, quality=quality, optimize=True)
        
        return img.size


def get_mime_type(filename: str) -> str:
    """
    Get MIME type from filename
    
    Args:
        filename: Filename with extension
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def format_file_size(size_bytes: int) -> str:
    """
    Format file size for display
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string like "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
