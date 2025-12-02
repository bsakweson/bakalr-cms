#!/usr/bin/env python3
"""
Update API endpoints to use UUID instead of int for path/query parameters
"""
import re
from pathlib import Path

API_DIR = Path("backend/api")


def update_file(filepath):
    """Update a single API file"""
    with open(filepath, "r") as f:
        content = f.read()

    original = content

    # Add UUID import if from uuid isn't present
    if "from uuid import UUID" not in content and "import UUID" not in content:
        # Find the imports section
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("from typing import"):
                lines.insert(i + 1, "from uuid import UUID")
                content = "\n".join(lines)
                break

    # Pattern 1: Path parameters like user_id: int
    content = re.sub(r"(\w+_id):\s*int(\s*,|\s*\)|\s*=)", r"\1: UUID\2", content)

    # Pattern 2: Query parameters like user_id: Optional[int]
    content = re.sub(r"(\w+_id):\s*Optional\[int\]", r"\1: Optional[UUID]", content)

    # Pattern 3: Pydantic model fields
    content = re.sub(r"(\s+\w+_id):\s*int(\s*$)", r"\1: UUID\2", content, flags=re.MULTILINE)

    # Pattern 4: Response model id fields
    content = re.sub(r"(\s+id):\s*int(\s*$)", r"\1: UUID\2", content, flags=re.MULTILINE)

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


def main():
    """Update all API files"""
    print("🔄 Updating API endpoints for UUID...")

    updated = 0
    for py_file in API_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        if update_file(py_file):
            print(f"  ✓ Updated {py_file.name}")
            updated += 1
        else:
            print(f"  ⏭️  {py_file.name} (no changes)")

    print(f"\n✅ Updated {updated} API files")
    print("\n⚠️  Manual review needed for:")
    print("  - Complex query logic with integer comparisons")
    print("  - Database queries with .filter(Model.id == some_int)")
    print("  - Any hardcoded integer IDs in code")


if __name__ == "__main__":
    main()
