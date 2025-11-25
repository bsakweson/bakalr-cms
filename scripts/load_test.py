#!/usr/bin/env python3
"""
Load testing script for Bakalr CMS

This script performs load testing on the API endpoints to identify
performance bottlenecks and ensure the system can handle expected load.

Requirements:
    pip install locust

Usage:
    # Run with web UI
    locust -f scripts/load_test.py --host=http://localhost:8000

    # Run headless
    locust -f scripts/load_test.py --host=http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless

    # With specific test scenarios
    locust -f scripts/load_test.py --host=http://localhost:8000 \
        --tags read  # Only run read tests
"""
import os
import random

from locust import HttpUser, between, tag, task


class BakalrCMSUser(HttpUser):
    """
    Simulated user interacting with Bakalr CMS
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Called when a simulated user starts"""
        self.token = None
        self.org_id = None
        self.content_type_id = None

        # Try to login if credentials are provided
        email = os.getenv("TEST_USER_EMAIL", "admin@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "admin123")

        try:
            response = self.client.post(
                "/api/v1/auth/login", json={"email": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.org_id = data.get("organization_id")
        except Exception as e:
            print(f"Login failed: {e}")

    @property
    def headers(self):
        """Get auth headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @tag("read", "health")
    @task(10)
    def health_check(self):
        """Check system health"""
        self.client.get("/health")

    @tag("read", "health")
    @task(5)
    def readiness_check(self):
        """Check system readiness"""
        self.client.get("/health/ready")

    @tag("read", "content")
    @task(20)
    def list_content(self):
        """List content entries"""
        if not self.token:
            return

        params = {
            "skip": random.randint(0, 10) * 10,
            "limit": 10,
        }
        self.client.get(
            "/api/v1/content/entries",
            params=params,
            headers=self.headers,
            name="/api/v1/content/entries",
        )

    @tag("read", "content")
    @task(15)
    def get_content(self):
        """Get a single content entry"""
        if not self.token:
            return

        # Assume content IDs 1-100
        content_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/content/entries/{content_id}",
            headers=self.headers,
            name="/api/v1/content/entries/[id]",
        )

    @tag("write", "content")
    @task(5)
    def create_content(self):
        """Create a new content entry"""
        if not self.token or not self.content_type_id:
            return

        payload = {
            "content_type_id": self.content_type_id,
            "title": f"Load Test Entry {random.randint(1000, 9999)}",
            "slug": f"load-test-{random.randint(1000, 9999)}",
            "status": "draft",
            "fields": {
                "body": "This is a test entry created during load testing.",
            },
        }

        self.client.post(
            "/api/v1/content/entries",
            json=payload,
            headers=self.headers,
            name="/api/v1/content/entries [create]",
        )

    @tag("read", "search")
    @task(10)
    def search_content(self):
        """Search content"""
        if not self.token:
            return

        queries = [
            "test",
            "example",
            "content",
            "article",
            "page",
        ]

        self.client.get(
            "/api/v1/search",
            params={"q": random.choice(queries)},
            headers=self.headers,
            name="/api/v1/search",
        )

    @tag("read", "media")
    @task(8)
    def list_media(self):
        """List media files"""
        if not self.token:
            return

        params = {
            "skip": random.randint(0, 5) * 10,
            "limit": 10,
        }
        self.client.get("/api/v1/media", params=params, headers=self.headers, name="/api/v1/media")

    @tag("read", "translation")
    @task(7)
    def list_translations(self):
        """List translations"""
        if not self.token:
            return

        self.client.get("/api/v1/translation", headers=self.headers, name="/api/v1/translation")

    @tag("read", "users")
    @task(5)
    def list_users(self):
        """List users"""
        if not self.token:
            return

        self.client.get("/api/v1/users", headers=self.headers, name="/api/v1/users")

    @tag("read", "roles")
    @task(5)
    def list_roles(self):
        """List roles"""
        if not self.token:
            return

        self.client.get("/api/v1/roles", headers=self.headers, name="/api/v1/roles")


class AdminUser(HttpUser):
    """
    Simulated admin user with higher privileges
    """

    wait_time = between(2, 5)

    def on_start(self):
        """Login as admin"""
        self.token = None

        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("ADMIN_PASSWORD", "admin123")

        try:
            response = self.client.post(
                "/api/v1/auth/login", json={"email": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
        except Exception as e:
            print(f"Admin login failed: {e}")

    @property
    def headers(self):
        """Get auth headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @tag("admin", "metrics")
    @task(5)
    def view_performance_metrics(self):
        """View performance metrics"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/metrics/performance", headers=self.headers, name="/api/v1/metrics/performance"
        )

    @tag("admin", "metrics")
    @task(3)
    def view_system_metrics(self):
        """View system metrics"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/metrics/system", headers=self.headers, name="/api/v1/metrics/system"
        )

    @tag("admin", "audit")
    @task(5)
    def view_audit_logs(self):
        """View audit logs"""
        if not self.token:
            return

        self.client.get("/api/v1/audit-logs", headers=self.headers, name="/api/v1/audit-logs")

    @tag("admin", "webhooks")
    @task(3)
    def list_webhooks(self):
        """List webhooks"""
        if not self.token:
            return

        self.client.get("/api/v1/webhooks", headers=self.headers, name="/api/v1/webhooks")
