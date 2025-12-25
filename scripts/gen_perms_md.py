#!/usr/bin/env python3
"""Generate permissions matrix markdown."""

from backend.db.session import SessionLocal
from backend.models.rbac import Role, Permission

db = SessionLocal()
permissions = db.query(Permission).order_by(Permission.category, Permission.name).all()
roles = db.query(Role).filter(Role.organization_id != None).all()
role_names = ["owner", "admin", "manager", "sales", "inventory_manager", "editor", "employee", "contributor", "api_consumer", "viewer"]

role_perms = {}
for role in roles:
    if role.name not in role_perms:
        role_perms[role.name] = set()
    role_perms[role.name].update(p.name for p in role.permissions)

# Print markdown table
header = "| Permission | Category |"
for rn in role_names:
    header += f" {rn} |"
print(header)

sep = "|------------|----------|"
for _ in role_names:
    sep += ":-----:|"
print(sep)

for p in permissions:
    is_owner_only = p.name in role_perms.get("owner", set()) and p.name not in role_perms.get("admin", set())
    perm_name = f"**{p.name}**" if is_owner_only else p.name
    cat = p.category or ""
    row = f"| {perm_name} | {cat} |"
    for rn in role_names:
        has = "✓" if p.name in role_perms.get(rn, set()) else ""
        row += f" {has} |"
    print(row)

db.close()
