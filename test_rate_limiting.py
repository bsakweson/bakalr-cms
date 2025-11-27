#!/usr/bin/env python3
"""
Rate Limiting Test Suite
Tests rate limiting on various API endpoints to ensure limits are enforced correctly.
"""

import asyncio
import time
from typing import Dict, List
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Test configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"

# Test credentials (update with your test user)
TEST_USER = {
    "email": "test@example.com",
    "password": "TestPassword123!"
}


class RateLimitTester:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=10.0)
        self.token = None
        self.results = []

    async def setup(self):
        """Setup: login to get access token"""
        console.print("\n[bold cyan]Setting up test environment...[/bold cyan]")
        
        try:
            # Try to login
            response = await self.client.post(
                f"{API_VERSION}/auth/login",
                json=TEST_USER
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                console.print(f"[green]✓ Logged in successfully[/green]")
                return True
            elif response.status_code == 429:
                console.print(f"[yellow]⚠ Rate limit hit during setup. Wait and retry.[/yellow]")
                return False
            else:
                console.print(f"[yellow]⚠ Login failed (status {response.status_code}). Testing with anonymous requests only.[/yellow]")
                return True
        except Exception as e:
            console.print(f"[red]✗ Setup failed: {e}[/red]")
            return False

    def get_headers(self) -> Dict:
        """Get headers with auth token if available"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def test_endpoint(self, name: str, method: str, endpoint: str, 
                           expected_limit: int, data: Dict = None) -> Dict:
        """Test a single endpoint's rate limit"""
        console.print(f"\n[bold]Testing: {name}[/bold]")
        console.print(f"Endpoint: [cyan]{method} {endpoint}[/cyan]")
        console.print(f"Expected limit: [yellow]{expected_limit} requests[/yellow]")
        
        success_count = 0
        rate_limited = False
        rate_limit_at = None
        start_time = time.time()
        
        # Send requests until rate limited
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Sending requests...", total=expected_limit + 10)
            
            for i in range(expected_limit + 10):
                try:
                    if method == "GET":
                        response = await self.client.get(
                            endpoint,
                            headers=self.get_headers()
                        )
                    elif method == "POST":
                        response = await self.client.post(
                            endpoint,
                            headers=self.get_headers(),
                            json=data or {}
                        )
                    
                    if response.status_code == 429:
                        rate_limited = True
                        rate_limit_at = i + 1
                        console.print(f"[yellow]Rate limited at request {rate_limit_at}[/yellow]")
                        
                        # Check for rate limit headers
                        headers = response.headers
                        if "X-RateLimit-Limit" in headers:
                            console.print(f"  X-RateLimit-Limit: {headers['X-RateLimit-Limit']}")
                        if "X-RateLimit-Remaining" in headers:
                            console.print(f"  X-RateLimit-Remaining: {headers['X-RateLimit-Remaining']}")
                        if "Retry-After" in headers:
                            console.print(f"  Retry-After: {headers['Retry-After']}s")
                        break
                    else:
                        success_count += 1
                    
                    progress.update(task, advance=1)
                    
                    # Small delay to avoid overwhelming the server
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    break
        
        duration = time.time() - start_time
        
        # Determine if test passed
        passed = rate_limited and (rate_limit_at is not None)
        
        result = {
            "name": name,
            "endpoint": endpoint,
            "expected_limit": expected_limit,
            "success_count": success_count,
            "rate_limited": rate_limited,
            "rate_limit_at": rate_limit_at,
            "duration": duration,
            "passed": passed
        }
        
        if passed:
            console.print(f"[green]✓ Test PASSED[/green]")
        else:
            console.print(f"[red]✗ Test FAILED - Rate limit not enforced[/red]")
        
        self.results.append(result)
        return result

    async def test_graphql_rate_limit(self):
        """Test GraphQL endpoint rate limiting"""
        console.print(f"\n[bold]Testing: GraphQL Rate Limiting[/bold]")
        console.print(f"Endpoint: [cyan]POST /api/v1/graphql[/cyan]")
        console.print(f"Expected limit: [yellow]100 requests per minute[/yellow]")
        
        success_count = 0
        rate_limited = False
        rate_limit_at = None
        
        query = """
        query {
            me {
                id
                email
            }
        }
        """
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Sending GraphQL requests...", total=110)
            
            for i in range(110):
                try:
                    response = await self.client.post(
                        f"{API_VERSION}/graphql",
                        headers=self.get_headers(),
                        json={"query": query}
                    )
                    
                    if response.status_code == 429:
                        rate_limited = True
                        rate_limit_at = i + 1
                        console.print(f"[yellow]Rate limited at request {rate_limit_at}[/yellow]")
                        break
                    else:
                        success_count += 1
                    
                    progress.update(task, advance=1)
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    break
        
        result = {
            "name": "GraphQL Rate Limit",
            "endpoint": "/api/v1/graphql",
            "expected_limit": 100,
            "success_count": success_count,
            "rate_limited": rate_limited,
            "rate_limit_at": rate_limit_at,
            "passed": rate_limited and (rate_limit_at is not None)
        }
        
        if result["passed"]:
            console.print(f"[green]✓ GraphQL rate limit working[/green]")
        else:
            console.print(f"[red]✗ GraphQL rate limit not enforced[/red]")
        
        self.results.append(result)

    async def run_tests(self):
        """Run all rate limit tests"""
        console.print("\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]")
        console.print("[bold magenta]   Rate Limiting Test Suite   [/bold magenta]")
        console.print("[bold magenta]═══════════════════════════════════════════════[/bold magenta]")
        
        if not await self.setup():
            console.print("\n[red]Setup failed. Exiting.[/red]")
            return
        
        # Test 1: Auth endpoints (strict limits)
        await self.test_endpoint(
            name="Login Rate Limit",
            method="POST",
            endpoint=f"{API_VERSION}/auth/login",
            expected_limit=10,  # 10 per minute
            data={"email": "nonexistent@example.com", "password": "wrong"}
        )
        
        await asyncio.sleep(2)  # Wait between tests
        
        # Test 2: Content listing (higher limits)
        if self.token:
            await self.test_endpoint(
                name="Content List Rate Limit",
                method="GET",
                endpoint=f"{API_VERSION}/content/entries",
                expected_limit=100  # 100 per minute for authenticated users
            )
            
            await asyncio.sleep(2)
        
        # Test 3: GraphQL
        if self.token:
            await self.test_graphql_rate_limit()
        
        # Display results table
        self.display_results()
        
        await self.client.aclose()

    def display_results(self):
        """Display test results in a table"""
        console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   Test Results Summary   [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan", width=30)
        table.add_column("Expected", justify="right", style="yellow")
        table.add_column("Rate Limited At", justify="right", style="yellow")
        table.add_column("Status", justify="center")
        
        passed = 0
        failed = 0
        
        for result in self.results:
            status = "[green]✓ PASS[/green]" if result["passed"] else "[red]✗ FAIL[/red]"
            if result["passed"]:
                passed += 1
            else:
                failed += 1
            
            table.add_row(
                result["name"],
                str(result["expected_limit"]),
                str(result["rate_limit_at"]) if result["rate_limit_at"] else "N/A",
                status
            )
        
        console.print(table)
        
        # Summary
        console.print(f"\n[bold]Total Tests:[/bold] {len(self.results)}")
        console.print(f"[green]Passed:[/green] {passed}")
        console.print(f"[red]Failed:[/red] {failed}")
        
        if failed == 0:
            console.print("\n[bold green]✓ All rate limiting tests passed![/bold green]")
        else:
            console.print(f"\n[bold red]✗ {failed} test(s) failed[/bold red]")


async def quick_test():
    """Quick test of rate limiting on login endpoint"""
    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Quick Rate Limit Test (Login Endpoint)   [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
    
    console.print("Testing: [yellow]POST /api/v1/auth/login[/yellow]")
    console.print("Expected limit: [yellow]10 requests per minute[/yellow]\n")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        success = 0
        rate_limited = False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Sending requests...", total=15)
            
            for i in range(15):
                response = await client.post(
                    f"{API_VERSION}/auth/login",
                    json={"email": "test@example.com", "password": "wrong"}
                )
                
                if response.status_code == 429:
                    rate_limited = True
                    console.print(f"\n[yellow]✓ Rate limited at request {i + 1}[/yellow]")
                    
                    # Show response
                    console.print(f"Response: {response.json()}")
                    
                    # Show headers
                    if "Retry-After" in response.headers:
                        console.print(f"Retry-After: {response.headers['Retry-After']}s")
                    break
                else:
                    success += 1
                
                progress.update(task, advance=1)
                await asyncio.sleep(0.05)
        
        if rate_limited:
            console.print(f"\n[green]✓ Rate limiting is working! Limited after {success} requests.[/green]")
        else:
            console.print(f"\n[red]✗ No rate limiting detected after 15 requests[/red]")


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        await quick_test()
    else:
        tester = RateLimitTester()
        await tester.run_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
