#!/usr/bin/env python3
"""
Seed roles and permissions to the database.

Run this script to add/update the default roles and permissions.

Usage:
    poetry run python scripts/seed_roles.py
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.seed_permissions import init_permissions

if __name__ == "__main__":
    print("🔧 Seeding roles and permissions...")
    init_permissions()
    print("✅ Done!")
