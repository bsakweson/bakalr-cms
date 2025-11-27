"""
Performance monitoring utilities and metrics collection
"""

import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psutil


class PerformanceMonitor:
    """Track application performance metrics"""

    def __init__(self):
        self.request_times = defaultdict(list)
        self.endpoint_stats = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "errors": 0,
            }
        )
        self.start_time = time.time()

    def record_request(self, endpoint: str, duration: float, status_code: int):
        """Record a request's performance metrics"""
        self.request_times[endpoint].append(duration)

        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)

        if status_code >= 400:
            stats["errors"] += 1

        # Keep only last 1000 requests per endpoint
        if len(self.request_times[endpoint]) > 1000:
            self.request_times[endpoint] = self.request_times[endpoint][-1000:]

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics for an endpoint or all endpoints"""
        if endpoint:
            if endpoint not in self.endpoint_stats:
                return {}

            stats = self.endpoint_stats[endpoint]
            times = self.request_times[endpoint]

            return {
                "endpoint": endpoint,
                "total_requests": stats["count"],
                "total_time_seconds": round(stats["total_time"], 2),
                "avg_time_ms": (
                    round((stats["total_time"] / stats["count"]) * 1000, 2)
                    if stats["count"] > 0
                    else 0
                ),
                "min_time_ms": (
                    round(stats["min_time"] * 1000, 2) if stats["min_time"] != float("inf") else 0
                ),
                "max_time_ms": round(stats["max_time"] * 1000, 2),
                "median_time_ms": round(statistics.median(times) * 1000, 2) if times else 0,
                "p95_time_ms": (
                    round(statistics.quantiles(times, n=20)[18] * 1000, 2)
                    if len(times) >= 20
                    else 0
                ),
                "p99_time_ms": (
                    round(statistics.quantiles(times, n=100)[98] * 1000, 2)
                    if len(times) >= 100
                    else 0
                ),
                "error_rate": (
                    round((stats["errors"] / stats["count"]) * 100, 2) if stats["count"] > 0 else 0
                ),
                "requests_per_second": round(stats["count"] / (time.time() - self.start_time), 2),
            }

        # Return all endpoints
        return {ep: self.get_endpoint_stats(ep) for ep in self.endpoint_stats.keys()}

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get process-specific metrics
        process = psutil.Process()
        process_memory = process.memory_info()

        return {
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
                "memory_total_mb": round(memory.total / (1024 * 1024), 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            },
            "process": {
                "memory_rss_mb": round(process_memory.rss / (1024 * 1024), 2),
                "memory_vms_mb": round(process_memory.vms / (1024 * 1024), 2),
                "cpu_percent": round(process.cpu_percent(), 2),
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
            },
            "uptime_seconds": round(time.time() - self.start_time, 2),
        }

    def get_slowest_endpoints(self, limit: int = 10) -> list:
        """Get the slowest endpoints by average response time"""
        endpoints = []
        for endpoint, stats in self.endpoint_stats.items():
            if stats["count"] > 0:
                avg_time = (stats["total_time"] / stats["count"]) * 1000
                endpoints.append(
                    {
                        "endpoint": endpoint,
                        "avg_time_ms": round(avg_time, 2),
                        "count": stats["count"],
                    }
                )

        return sorted(endpoints, key=lambda x: x["avg_time_ms"], reverse=True)[:limit]

    def reset_stats(self):
        """Reset all performance statistics"""
        self.request_times.clear()
        self.endpoint_stats.clear()
        self.start_time = time.time()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


class RequestTimer:
    """Context manager for timing requests"""

    def __init__(self, endpoint: str, status_code: int = 200):
        self.endpoint = endpoint
        self.status_code = status_code
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        # Update status code if there was an exception
        if exc_type is not None:
            self.status_code = 500

        performance_monitor.record_request(self.endpoint, duration, self.status_code)


# Performance budgets (in milliseconds)
PERFORMANCE_BUDGETS = {
    "api_response": 200,  # API endpoints should respond within 200ms
    "database_query": 50,  # Database queries should complete within 50ms
    "cache_operation": 10,  # Cache operations should complete within 10ms
    "file_upload": 5000,  # File uploads should complete within 5 seconds
}


def check_performance_budget(operation: str, duration_ms: float) -> bool:
    """Check if an operation meets its performance budget"""
    budget = PERFORMANCE_BUDGETS.get(operation)
    if budget is None:
        return True

    return duration_ms <= budget


def get_performance_report() -> Dict[str, Any]:
    """Get a comprehensive performance report"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "system_metrics": performance_monitor.get_system_metrics(),
        "endpoint_stats": performance_monitor.get_endpoint_stats(),
        "slowest_endpoints": performance_monitor.get_slowest_endpoints(),
        "performance_budgets": PERFORMANCE_BUDGETS,
    }
