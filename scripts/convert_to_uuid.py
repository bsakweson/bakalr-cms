#!/usr/bin/env python3
"""
Script to convert Integer foreign keys to UUID foreign keys in model files
"""
import re
from pathlib import Path

# Models directory
MODELS_DIR = Path("backend/models")

# Files to process (excluding base.py and __init__.py)
files_to_process = [
    "media.py",
    "theme.py",
    "webhook.py",
    "organization.py",
    "notification.py",
    "rbac.py",
    "user_organization.py",
    "content_template.py",
    "api_key.py",
    "content.py",
    "translation.py",
    "audit_log.py",
    "user.py",
    "schedule.py",
    "relationship.py",
]


def add_uuid_import(content):
    """Add UUID import if not present"""
    if "from sqlalchemy.dialects.postgresql import UUID" in content:
        return content

    # Find the sqlalchemy import line
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("from sqlalchemy import"):
            # Check if ForeignKey is imported
            if "ForeignKey" in line:
                # Add UUID import after this line
                lines.insert(i + 1, "from sqlalchemy.dialects.postgresql import UUID")
                return "\n".join(lines)

    # If no sqlalchemy import found, add at the top after docstring
    for i, line in enumerate(lines):
        if i > 0 and not line.startswith('"""') and not line.startswith("'''") and line.strip():
            lines.insert(i, "from sqlalchemy.dialects.postgresql import UUID")
            return "\n".join(lines)

    return content


def convert_foreign_keys(content):
    """Convert Integer ForeignKey columns to UUID ForeignKey columns"""
    # Pattern to match: Column(Integer, ForeignKey(...))
    pattern = r"Column\(Integer,\s*ForeignKey\("
    replacement = r"Column(UUID(as_uuid=True), ForeignKey("

    content = re.sub(pattern, replacement, content)

    # Also handle reversed order: Column(ForeignKey(...), Integer)
    pattern2 = r"Column\(ForeignKey\(([^)]+)\),\s*Integer"
    replacement2 = r"Column(UUID(as_uuid=True), ForeignKey(\1)"

    content = re.sub(pattern2, replacement2, content)

    return content


def process_file(filepath):
    """Process a single model file"""
    print(f"Processing {filepath}...")

    with open(filepath, "r") as f:
        content = f.read()

    original = content

    # Add UUID import
    content = add_uuid_import(content)

    # Convert foreign keys
    content = convert_foreign_keys(content)

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  ✅ Updated {filepath}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {filepath}")
        return False


def main():
    """Main conversion function"""
    print("🔄 Converting Integer foreign keys to UUID foreign keys...\n")

    updated_count = 0

    for filename in files_to_process:
        filepath = MODELS_DIR / filename
        if filepath.exists():
            if process_file(filepath):
                updated_count += 1
        else:
            print(f"⚠️  File not found: {filepath}")

    print(f"\n✅ Conversion complete! Updated {updated_count} files.")
    print("\n⚠️  IMPORTANT: You must now:")
    print("  1. Create and run database migration to convert existing data")
    print("  2. Update all API endpoints that accept integer IDs")
    print("  3. Update frontend to handle UUID strings")
    print("  4. Update all tests")


if __name__ == "__main__":
    main()
