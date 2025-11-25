"""
Quick test to verify storage backend configuration
"""
from backend.core.storage import get_storage_backend, LocalStorageBackend, S3StorageBackend
from backend.core.config import Settings


def test_storage_backend_selection():
    """Test that storage backend is selected correctly based on config"""
    settings = Settings()
    
    print(f"Current STORAGE_BACKEND setting: {settings.STORAGE_BACKEND}")
    
    storage = get_storage_backend()
    
    if settings.STORAGE_BACKEND == 'local':
        assert isinstance(storage, LocalStorageBackend), "Expected LocalStorageBackend"
        print("✅ Local storage backend selected correctly")
        print(f"   Upload directory: {storage.base_dir}")
    elif settings.STORAGE_BACKEND == 's3':
        assert isinstance(storage, S3StorageBackend), "Expected S3StorageBackend"
        print("✅ S3 storage backend selected correctly")
        print(f"   Bucket: {storage.bucket_name}")
        print(f"   Region: {settings.AWS_REGION}")
    else:
        raise ValueError(f"Unknown storage backend: {settings.STORAGE_BACKEND}")


def test_local_storage():
    """Test local storage operations"""
    from pathlib import Path
    import tempfile
    
    # Create temporary storage for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_dir=tmpdir)
        
        # Test file save
        test_content = b"Hello, World!"
        file_path = "test/sample.txt"
        
        url = storage.save_file(test_content, file_path)
        print(f"✅ File saved to local storage: {url}")
        
        # Test file exists
        assert storage.file_exists(file_path), "File should exist"
        print(f"✅ File existence check passed")
        
        # Test get URL
        file_url = storage.get_file_url(file_path)
        print(f"✅ File URL: {file_url}")
        
        # Test file read
        full_path = storage.get_full_path(file_path)
        with open(full_path, 'rb') as f:
            content = f.read()
        assert content == test_content, "File content should match"
        print(f"✅ File content verified")
        
        # Test file delete
        deleted = storage.delete_file(file_path)
        assert deleted, "File should be deleted"
        assert not storage.file_exists(file_path), "File should not exist after deletion"
        print(f"✅ File deletion successful")


def test_s3_storage_config():
    """Test S3 storage configuration"""
    settings = Settings()
    
    if settings.STORAGE_BACKEND != 's3':
        print("⏭️  Skipping S3 test (STORAGE_BACKEND is not 's3')")
        return
    
    # Check required settings
    required_settings = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'S3_BUCKET_NAME',
        'AWS_REGION'
    ]
    
    missing = []
    for setting in required_settings:
        value = getattr(settings, setting, None)
        if not value:
            missing.append(setting)
    
    if missing:
        print(f"❌ Missing S3 configuration: {', '.join(missing)}")
        print("   Please set these in your .env file")
        return
    
    print("✅ S3 configuration complete")
    print(f"   Bucket: {settings.S3_BUCKET_NAME}")
    print(f"   Region: {settings.AWS_REGION}")
    
    if settings.S3_ENDPOINT_URL:
        print(f"   Endpoint: {settings.S3_ENDPOINT_URL}")
    
    if settings.S3_PUBLIC_URL:
        print(f"   Public URL: {settings.S3_PUBLIC_URL}")
    
    # Try to initialize S3 backend
    try:
        storage = S3StorageBackend()
        print("✅ S3 storage backend initialized successfully")
        print(f"   Bucket exists: {storage.bucket_name}")
    except Exception as e:
        print(f"❌ Failed to initialize S3 storage: {str(e)}")
        print("   Check your AWS credentials and bucket configuration")


if __name__ == '__main__':
    print("=" * 60)
    print("Storage Backend Configuration Test")
    print("=" * 60)
    print()
    
    # Test 1: Backend selection
    print("Test 1: Storage Backend Selection")
    print("-" * 60)
    test_storage_backend_selection()
    print()
    
    # Test 2: Local storage operations
    print("Test 2: Local Storage Operations")
    print("-" * 60)
    test_local_storage()
    print()
    
    # Test 3: S3 configuration
    print("Test 3: S3 Storage Configuration")
    print("-" * 60)
    test_s3_storage_config()
    print()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
