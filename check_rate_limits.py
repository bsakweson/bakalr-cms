#!/usr/bin/env python3
"""
Check all API endpoints for rate limiting decorators.
"""
import os
import re
from pathlib import Path

def check_rate_limits():
    api_dir = Path("backend/api")
    
    results = {
        "protected": [],
        "unprotected": [],
        "total_endpoints": 0
    }
    
    # Skip router.py as it's just importing
    skip_files = ["router.py", "__init__.py"]
    
    for file_path in api_dir.glob("*.py"):
        if file_path.name in skip_files:
            continue
            
        with open(file_path, "r") as f:
            content = f.read()
            lines = content.split("\n")
            
        # Find all router decorators
        for i, line in enumerate(lines):
            # Match @router.(get|post|put|patch|delete)
            if re.match(r'^\s*@router\.(get|post|put|patch|delete)', line):
                results["total_endpoints"] += 1
                
                # Check if there's a @limiter.limit decorator within 10 lines before OR after
                has_limiter = False
                for j in range(max(0, i-10), min(len(lines), i+11)):
                    if "@limiter.limit" in lines[j]:
                        has_limiter = True
                        break
                
                # Extract endpoint path
                match = re.search(r'@router\.\w+\("([^"]*)"', line)
                path = match.group(1) if match else "unknown"
                
                endpoint_info = {
                    "file": file_path.name,
                    "line": i + 1,
                    "path": path,
                    "decorator": line.strip()
                }
                
                if has_limiter:
                    results["protected"].append(endpoint_info)
                else:
                    results["unprotected"].append(endpoint_info)
    
    # Print results
    print("=" * 70)
    print("RATE LIMITING COVERAGE REPORT")
    print("=" * 70)
    print(f"\nTotal endpoints: {results['total_endpoints']}")
    print(f"Protected: {len(results['protected'])} ({len(results['protected'])/results['total_endpoints']*100:.1f}%)")
    print(f"Unprotected: {len(results['unprotected'])} ({len(results['unprotected'])/results['total_endpoints']*100:.1f}%)")
    
    if results["unprotected"]:
        print("\n" + "=" * 70)
        print("⚠️  UNPROTECTED ENDPOINTS")
        print("=" * 70)
        for ep in results["unprotected"]:
            print(f"\n📁 {ep['file']}:{ep['line']}")
            print(f"   Path: {ep['path']}")
            print(f"   {ep['decorator']}")
    else:
        print("\n" + "=" * 70)
        print("✅ ALL ENDPOINTS ARE PROTECTED!")
        print("=" * 70)
    
    return results

if __name__ == "__main__":
    results = check_rate_limits()
    
    # Exit with error code if there are unprotected endpoints
    exit(1 if results["unprotected"] else 0)
