"""
Database backup and data anonymization tool for Bakalr CMS

Creates database backups and anonymizes user data for GDPR compliance.
Run with: poetry run python scripts/backup_database.py --help
"""
import os
import sys
import argparse
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from backend.db.session import SessionLocal, engine
from backend.models.user import User
from backend.models.audit_log import AuditLog


def create_backup(output_dir: str, compress: bool = True) -> str:
    """Create a full database backup"""
    # Create backup directory if it doesn't exist
    backup_dir = Path(output_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"bakalr_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename
    
    # Get current database path
    from backend.core.config import settings
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return None
    
    # Copy database file
    print(f"📦 Creating backup...")
    print(f"   Source: {db_path}")
    print(f"   Destination: {backup_path}")
    
    shutil.copy2(db_path, backup_path)
    
    # Compress if requested
    if compress:
        import gzip
        compressed_path = str(backup_path) + ".gz"
        print(f"🗜️  Compressing backup...")
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        backup_path.unlink()
        backup_path = Path(compressed_path)
    
    # Get file size
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    
    print(f"✅ Backup created: {backup_path}")
    print(f"   Size: {size_mb:.2f} MB")
    
    return str(backup_path)


def anonymize_users(db: Session, exclude_emails: Optional[list] = None):
    """Anonymize user data for GDPR compliance"""
    exclude_emails = exclude_emails or []
    
    users = db.query(User).all()
    anonymized_count = 0
    
    print(f"🔒 Anonymizing user data...")
    print(f"   Total users: {len(users)}")
    print(f"   Excluded emails: {exclude_emails}")
    
    for user in users:
        if user.email in exclude_emails:
            print(f"   ⏭️  Skipping: {user.email}")
            continue
        
        # Generate anonymous hash based on user ID
        hash_suffix = hashlib.md5(str(user.id).encode()).hexdigest()[:8]
        
        # Anonymize personal data
        user.email = f"user_{hash_suffix}@anonymized.local"
        user.username = f"user_{hash_suffix}" if user.username else None
        user.first_name = "Anonymous"
        user.last_name = "User"
        user.bio = None
        user.avatar_url = None
        
        # Clear sensitive fields
        user.password_reset_token = None
        user.verification_token = None
        user.two_factor_secret = None
        user.two_factor_backup_codes = None
        
        anonymized_count += 1
    
    db.commit()
    print(f"✅ Anonymized {anonymized_count} users")


def anonymize_audit_logs(db: Session):
    """Anonymize IP addresses and user agents in audit logs"""
    logs = db.query(AuditLog).all()
    
    print(f"🔒 Anonymizing audit logs...")
    print(f"   Total logs: {len(logs)}")
    
    for log in logs:
        if log.ip_address:
            # Keep first two octets, anonymize the rest
            parts = log.ip_address.split('.')
            if len(parts) == 4:
                log.ip_address = f"{parts[0]}.{parts[1]}.XXX.XXX"
        
        if log.user_agent:
            # Remove detailed version information
            log.user_agent = "Mozilla/5.0 (Anonymized)"
    
    db.commit()
    print(f"✅ Anonymized {len(logs)} audit log entries")


def clean_old_backups(backup_dir: str, keep_count: int = 5):
    """Clean old backup files, keeping only the most recent N backups"""
    backup_path = Path(backup_dir)
    
    if not backup_path.exists():
        return
    
    # Find all backup files
    backup_files = sorted(
        backup_path.glob("bakalr_backup_*.db*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if len(backup_files) <= keep_count:
        print(f"📁 Current backups: {len(backup_files)} (no cleanup needed)")
        return
    
    # Remove old backups
    files_to_remove = backup_files[keep_count:]
    print(f"🗑️  Removing {len(files_to_remove)} old backup(s)...")
    
    for backup_file in files_to_remove:
        backup_file.unlink()
        print(f"   ✓ Removed: {backup_file.name}")
    
    print(f"✅ Kept {keep_count} most recent backups")


def main():
    parser = argparse.ArgumentParser(description="Bakalr CMS database backup and anonymization")
    parser.add_argument(
        "operation",
        choices=["backup", "anonymize", "backup-and-anonymize"],
        help="Operation to perform"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./dumps",
        help="Directory to store backups (default: ./dumps)"
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Compress backup with gzip"
    )
    parser.add_argument(
        "--exclude-emails",
        nargs="+",
        help="Email addresses to exclude from anonymization"
    )
    parser.add_argument(
        "--keep-backups",
        type=int,
        default=5,
        help="Number of recent backups to keep (default: 5)"
    )
    parser.add_argument(
        "--anonymize-logs",
        action="store_true",
        help="Also anonymize audit logs"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Bakalr CMS Backup & Anonymization Tool")
    print("=" * 60)
    
    try:
        if args.operation in ["backup", "backup-and-anonymize"]:
            # Create backup
            backup_path = create_backup(args.output_dir, args.compress)
            
            if backup_path:
                # Clean old backups
                clean_old_backups(args.output_dir, args.keep_backups)
        
        if args.operation in ["anonymize", "backup-and-anonymize"]:
            # Anonymize data
            if args.operation == "backup-and-anonymize":
                print("\n" + "=" * 60)
                print("Starting data anonymization...")
                print("=" * 60)
            
            confirm = input("\n⚠️  This will PERMANENTLY anonymize user data. Continue? (yes/no): ")
            
            if confirm.lower() != "yes":
                print("❌ Anonymization cancelled")
                return
            
            db = SessionLocal()
            try:
                # Anonymize users
                anonymize_users(db, args.exclude_emails)
                
                # Anonymize audit logs if requested
                if args.anonymize_logs:
                    anonymize_audit_logs(db)
                
            finally:
                db.close()
        
        print("\n" + "=" * 60)
        print("✅ Operation completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during operation: {e}")
        raise


if __name__ == "__main__":
    main()
