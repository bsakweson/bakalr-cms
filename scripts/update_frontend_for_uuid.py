#!/usr/bin/env python3
"""
Update frontend TypeScript files to use string for id fields (UUIDs)
"""
import re
from pathlib import Path

FRONTEND_DIR = Path("frontend")


def update_typescript_file(filepath):
    """Update a TypeScript file to use string for IDs"""
    with open(filepath, "r") as f:
        content = f.read()

    original = content

    # Pattern 1: Interface/type id fields
    # id: number -> id: string
    content = re.sub(r"(\s+id):\s*number", r"\1: string", content)

    # Pattern 2: ID fields in interfaces
    # userId: number -> userId: string
    content = re.sub(r"(\s+\w+[Ii]d):\s*number", r"\1: string", content)

    # Pattern 3: Optional ID fields
    # id?: number -> id?: string
    content = re.sub(r"(\s+\w*[Ii]d\??):\s*number", r"\1: string", content)

    # Pattern 4: parseInt usage for IDs - comment them out for manual review
    if "parseInt" in content and ("Id" in content or "id" in content):
        # Don't automatically change parseInt - flag for manual review
        pass

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


def main():
    """Update all TypeScript files"""
    print("🔄 Updating frontend TypeScript files for UUID...")

    updated_count = 0

    # Update types directory
    types_dir = FRONTEND_DIR / "types"
    if types_dir.exists():
        for ts_file in types_dir.glob("**/*.ts"):
            if update_typescript_file(ts_file):
                print(f"  ✓ Updated {ts_file.relative_to(FRONTEND_DIR)}")
                updated_count += 1

    # Update lib directory (API client)
    lib_dir = FRONTEND_DIR / "lib"
    if lib_dir.exists():
        for ts_file in lib_dir.glob("**/*.ts"):
            if ts_file.name != "performance.ts":  # Skip performance metrics
                if update_typescript_file(ts_file):
                    print(f"  ✓ Updated {ts_file.relative_to(FRONTEND_DIR)}")
                    updated_count += 1

    # Update app directory
    app_dir = FRONTEND_DIR / "app"
    if app_dir.exists():
        for ts_file in list(app_dir.glob("**/*.ts")) + list(app_dir.glob("**/*.tsx")):
            if update_typescript_file(ts_file):
                print(f"  ✓ Updated {ts_file.relative_to(FRONTEND_DIR)}")
                updated_count += 1

    # Update components
    components_dir = FRONTEND_DIR / "components"
    if components_dir.exists():
        for ts_file in list(components_dir.glob("**/*.ts")) + list(components_dir.glob("**/*.tsx")):
            if update_typescript_file(ts_file):
                print(f"  ✓ Updated {ts_file.relative_to(FRONTEND_DIR)}")
                updated_count += 1

    print(f"\n✅ Updated {updated_count} TypeScript files")
    print("\n⚠️  Manual review needed for:")
    print("  - parseInt() usage with IDs")
    print("  - Number comparisons with IDs")
    print("  - URL construction with IDs")
    print("  - Router params that expect numbers")


if __name__ == "__main__":
    main()
