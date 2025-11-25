"""
Security vulnerability scanner for Bakalr CMS

Checks for common security issues and misconfigurations.
Run with: poetry run python scripts/security_check.py
"""
import os
import sys
from pathlib import Path
import re
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv(project_root / ".env")


class SecurityChecker:
    """Security vulnerability scanner"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
    
    def add_issue(self, category: str, message: str, severity: str = "ERROR"):
        """Add a security issue"""
        self.issues.append({
            "severity": severity,
            "category": category,
            "message": message
        })
    
    def add_warning(self, category: str, message: str):
        """Add a security warning"""
        self.warnings.append({
            "category": category,
            "message": message
        })
    
    def add_passed(self, check: str):
        """Add a passed check"""
        self.passed.append(check)
    
    def check_secrets(self):
        """Check for secrets in code"""
        print("\n🔍 Checking for hardcoded secrets...")
        
        # Patterns for common secrets
        patterns = {
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "Generic API Key": r"['\"](?:api[_-]?key|apikey)['\"]:\s*['\"][a-zA-Z0-9]{20,}['\"]",
            "Generic Secret": r"['\"](?:secret|password)['\"]:\s*['\"][^'\"]{8,}['\"]",
            "Private Key": r"-----BEGIN (?:RSA )?PRIVATE KEY-----",
            "JWT Token": r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}",
        }
        
        # Files to check
        python_files = list(Path("backend").rglob("*.py"))
        
        found_secrets = False
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for secret_type, pattern in patterns.items():
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            self.add_issue(
                                "Hardcoded Secrets",
                                f"Possible {secret_type} found in {file_path}",
                                "CRITICAL"
                            )
                            found_secrets = True
            except Exception as e:
                continue
        
        if not found_secrets:
            self.add_passed("No hardcoded secrets detected")
    
    def check_environment_variables(self):
        """Check required environment variables"""
        print("🔍 Checking environment configuration...")
        
        required_vars = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "DATABASE_URL",
        ]
        
        missing = []
        weak_secrets = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing.append(var)
            elif var in ["SECRET_KEY", "JWT_SECRET_KEY"]:
                if len(value) < 32:
                    weak_secrets.append(var)
        
        if missing:
            self.add_issue(
                "Environment Variables",
                f"Missing required environment variables: {', '.join(missing)}",
                "CRITICAL"
            )
        else:
            self.add_passed("All required environment variables present")
        
        if weak_secrets:
            self.add_warning(
                "Weak Secrets",
                f"Weak secrets detected (< 32 chars): {', '.join(weak_secrets)}"
            )
    
    def check_cors_configuration(self):
        """Check CORS configuration"""
        print("🔍 Checking CORS configuration...")
        
        try:
            from backend.core.csp import CORS_SETTINGS
            
            # Check for overly permissive CORS
            if "*" in CORS_SETTINGS.get("allow_origins", []):
                self.add_issue(
                    "CORS Configuration",
                    "CORS allows all origins (*) - this is insecure for production",
                    "HIGH"
                )
            else:
                self.add_passed("CORS configuration is restrictive")
            
            if not CORS_SETTINGS.get("allow_credentials", False):
                self.add_warning(
                    "CORS Configuration",
                    "CORS credentials not enabled - may affect authentication"
                )
        except Exception as e:
            self.add_warning("CORS Configuration", f"Could not check CORS settings: {e}")
    
    def check_sql_injection_protection(self):
        """Check for potential SQL injection vulnerabilities"""
        print("🔍 Checking SQL injection protection...")
        
        # Check for string concatenation in queries
        python_files = list(Path("backend").rglob("*.py"))
        
        dangerous_patterns = [
            r'\.execute\(["\'].*%s.*["\'].*%',  # String formatting
            r'\.execute\(f["\'].*{.*}.*["\']',  # f-strings
            r'\.execute\(["\'].*\+.*\+.*["\']', # String concatenation
        ]
        
        found_issues = False
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern in dangerous_patterns:
                        if re.search(pattern, content):
                            self.add_warning(
                                "SQL Injection Risk",
                                f"Potential SQL injection risk in {file_path} - verify parameterized queries are used"
                            )
                            found_issues = True
                            break
            except Exception:
                continue
        
        if not found_issues:
            self.add_passed("No obvious SQL injection vulnerabilities detected")
    
    def check_xss_protection(self):
        """Check for XSS protection"""
        print("🔍 Checking XSS protection...")
        
        # Check if security headers middleware exists
        middleware_file = Path("backend/middleware/security.py")
        
        if middleware_file.exists():
            try:
                with open(middleware_file, 'r') as f:
                    content = f.read()
                    
                    if "X-Content-Type-Options" in content:
                        self.add_passed("X-Content-Type-Options header configured")
                    else:
                        self.add_warning("XSS Protection", "X-Content-Type-Options header not configured")
                    
                    if "X-XSS-Protection" in content:
                        self.add_passed("X-XSS-Protection header configured")
                    else:
                        self.add_warning("XSS Protection", "X-XSS-Protection header not configured")
            except Exception as e:
                self.add_warning("XSS Protection", f"Could not verify security headers: {e}")
        else:
            self.add_issue(
                "XSS Protection",
                "Security headers middleware not found",
                "HIGH"
            )
    
    def check_csrf_protection(self):
        """Check for CSRF protection"""
        print("🔍 Checking CSRF protection...")
        
        middleware_file = Path("backend/middleware/security.py")
        
        if middleware_file.exists():
            try:
                with open(middleware_file, 'r') as f:
                    content = f.read()
                    
                    if "CSRFProtection" in content:
                        self.add_passed("CSRF protection middleware configured")
                    else:
                        self.add_warning("CSRF Protection", "CSRF protection middleware not found")
            except Exception as e:
                self.add_warning("CSRF Protection", f"Could not verify CSRF protection: {e}")
        else:
            self.add_warning("CSRF Protection", "Security middleware file not found")
    
    def check_file_permissions(self):
        """Check sensitive file permissions"""
        print("🔍 Checking file permissions...")
        
        sensitive_files = [
            ".env",
            "bakalr_cms.db",
            "alembic.ini",
        ]
        
        for file_name in sensitive_files:
            file_path = Path(file_name)
            if file_path.exists():
                # Check if file is world-readable
                stat_info = file_path.stat()
                mode = stat_info.st_mode
                
                # Check world-readable permission (others can read)
                if mode & 0o004:
                    self.add_warning(
                        "File Permissions",
                        f"{file_name} is world-readable - consider restricting permissions"
                    )
                else:
                    self.add_passed(f"{file_name} has restrictive permissions")
    
    def check_dependency_vulnerabilities(self):
        """Check for known vulnerabilities in dependencies"""
        print("🔍 Checking dependencies for known vulnerabilities...")
        
        self.add_warning(
            "Dependency Security",
            "Run 'poetry audit' or 'pip-audit' to check for known vulnerabilities"
        )
    
    def run_all_checks(self):
        """Run all security checks"""
        print("=" * 60)
        print("Bakalr CMS Security Scanner")
        print("=" * 60)
        
        self.check_secrets()
        self.check_environment_variables()
        self.check_cors_configuration()
        self.check_sql_injection_protection()
        self.check_xss_protection()
        self.check_csrf_protection()
        self.check_file_permissions()
        self.check_dependency_vulnerabilities()
        
        # Print results
        print("\n" + "=" * 60)
        print("Security Scan Results")
        print("=" * 60)
        
        if self.issues:
            print(f"\n❌ Critical Issues ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   [{issue['severity']}] {issue['category']}: {issue['message']}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   {warning['category']}: {warning['message']}")
        
        if self.passed:
            print(f"\n✅ Passed Checks ({len(self.passed)}):")
            for check in self.passed:
                print(f"   {check}")
        
        print("\n" + "=" * 60)
        
        # Summary
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        total_passed = len(self.passed)
        
        print(f"Summary: {total_passed} passed, {total_warnings} warnings, {total_issues} critical issues")
        
        if total_issues > 0:
            print("\n⚠️  CRITICAL ISSUES FOUND - Please address before deploying to production!")
            return False
        elif total_warnings > 0:
            print("\n⚠️  Warnings found - Review and address as needed")
            return True
        else:
            print("\n✅ No critical security issues detected!")
            return True


def main():
    checker = SecurityChecker()
    success = checker.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
