"""
Geo-Location Service - Track and resolve IP addresses to geographic locations.
Uses ip-api.com (free) with fallback to ipinfo.io.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from backend.core.cache import CacheService
from backend.core.config import settings


@dataclass
class GeoLocation:
    """Geographic location data"""

    ip: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_code: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    as_name: Optional[str] = None
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    is_hosting: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "country": self.country,
            "country_code": self.country_code,
            "region": self.region,
            "region_code": self.region_code,
            "city": self.city,
            "zip_code": self.zip_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "isp": self.isp,
            "org": self.org,
            "as_name": self.as_name,
            "is_vpn": self.is_vpn,
            "is_proxy": self.is_proxy,
            "is_tor": self.is_tor,
            "is_hosting": self.is_hosting,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @property
    def display_location(self) -> str:
        """Human-readable location string"""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.region:
            parts.append(self.region)
        if self.country:
            parts.append(self.country)

        if parts:
            return ", ".join(parts)
        return "Unknown Location"

    @property
    def is_suspicious(self) -> bool:
        """Check if the IP is potentially suspicious"""
        return self.is_vpn or self.is_proxy or self.is_tor or self.is_hosting


class GeoLocationService:
    """
    Service for resolving IP addresses to geographic locations.
    Uses caching to minimize API calls.
    """

    # Cache TTL: 24 hours (IPs don't change location often)
    CACHE_TTL = 86400

    # ip-api.com free tier: 45 requests/minute
    IP_API_URL = "http://ip-api.com/json"

    # ipinfo.io free tier: 50k requests/month
    IPINFO_URL = "https://ipinfo.io"

    def __init__(self):
        self.cache = CacheService()
        self.ipinfo_token = getattr(settings, "IPINFO_TOKEN", None)

    def _get_cache_key(self, ip: str) -> str:
        return f"geolocation:{ip}"

    async def resolve_ip(self, ip: str) -> GeoLocation:
        """
        Resolve an IP address to geographic location.
        Results are cached for 24 hours.
        """
        # Check for local/private IPs
        if self._is_private_ip(ip):
            return GeoLocation(
                ip=ip,
                country="Local",
                city="Private Network",
                resolved_at=datetime.now(timezone.utc),
            )

        # Check cache
        cache_key = self._get_cache_key(ip)
        cached = self.cache.get(cache_key)
        if cached:
            return GeoLocation(**cached)

        # Try ip-api.com first (free, no auth needed)
        location = await self._resolve_with_ip_api(ip)

        # Fallback to ipinfo.io if ip-api failed
        if not location.country and self.ipinfo_token:
            location = await self._resolve_with_ipinfo(ip)

        # Cache the result
        if location.country:
            self.cache.set(cache_key, location.to_dict(), ttl=self.CACHE_TTL)

        return location

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/local"""
        private_prefixes = [
            "127.",
            "10.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "192.168.",
            "::1",
            "fe80:",
            "fc00:",
            "fd00:",
        ]
        return any(ip.startswith(prefix) for prefix in private_prefixes)

    async def _resolve_with_ip_api(self, ip: str) -> GeoLocation:
        """Resolve using ip-api.com"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.IP_API_URL}/{ip}",
                    params={
                        "fields": "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,proxy,hosting",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get("status") == "success":
                        return GeoLocation(
                            ip=ip,
                            country=data.get("country"),
                            country_code=data.get("countryCode"),
                            region=data.get("regionName"),
                            region_code=data.get("region"),
                            city=data.get("city"),
                            zip_code=data.get("zip"),
                            latitude=data.get("lat"),
                            longitude=data.get("lon"),
                            timezone=data.get("timezone"),
                            isp=data.get("isp"),
                            org=data.get("org"),
                            as_name=data.get("as"),
                            is_proxy=data.get("proxy", False),
                            is_hosting=data.get("hosting", False),
                            resolved_at=datetime.now(timezone.utc),
                        )
        except Exception as e:
            print(f"ip-api.com lookup failed for {ip}: {e}")

        return GeoLocation(ip=ip, resolved_at=datetime.now(timezone.utc))

    async def _resolve_with_ipinfo(self, ip: str) -> GeoLocation:
        """Resolve using ipinfo.io"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if self.ipinfo_token:
                    headers["Authorization"] = f"Bearer {self.ipinfo_token}"

                response = await client.get(
                    f"{self.IPINFO_URL}/{ip}/json",
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()

                    # Parse location coordinates
                    lat, lon = None, None
                    if data.get("loc"):
                        parts = data["loc"].split(",")
                        if len(parts) == 2:
                            lat = float(parts[0])
                            lon = float(parts[1])

                    # Check privacy flags
                    privacy = data.get("privacy", {})

                    return GeoLocation(
                        ip=ip,
                        country=data.get("country"),
                        country_code=data.get("country"),
                        region=data.get("region"),
                        city=data.get("city"),
                        zip_code=data.get("postal"),
                        latitude=lat,
                        longitude=lon,
                        timezone=data.get("timezone"),
                        org=data.get("org"),
                        is_vpn=privacy.get("vpn", False),
                        is_proxy=privacy.get("proxy", False),
                        is_tor=privacy.get("tor", False),
                        is_hosting=privacy.get("hosting", False),
                        resolved_at=datetime.now(timezone.utc),
                    )
        except Exception as e:
            print(f"ipinfo.io lookup failed for {ip}: {e}")

        return GeoLocation(ip=ip, resolved_at=datetime.now(timezone.utc))

    async def get_location_string(self, ip: str) -> str:
        """Get human-readable location string for an IP"""
        location = await self.resolve_ip(ip)
        return location.display_location

    async def is_suspicious_ip(self, ip: str) -> bool:
        """Check if an IP is potentially suspicious (VPN, proxy, Tor, etc.)"""
        location = await self.resolve_ip(ip)
        return location.is_suspicious

    async def check_location_change(
        self,
        ip: str,
        previous_ip: Optional[str],
        threshold_km: float = 500,
    ) -> dict:
        """
        Check if there's a significant location change between IPs.
        Returns dict with is_significant, distance, and locations.
        """
        if not previous_ip or ip == previous_ip:
            return {"is_significant": False, "distance_km": 0}

        current = await self.resolve_ip(ip)
        previous = await self.resolve_ip(previous_ip)

        # Can't calculate distance without coordinates
        if not all([current.latitude, current.longitude, previous.latitude, previous.longitude]):
            return {
                "is_significant": current.country_code != previous.country_code,
                "distance_km": None,
                "current_location": current.display_location,
                "previous_location": previous.display_location,
            }

        # Calculate distance using Haversine formula
        distance = self._haversine_distance(
            current.latitude,
            current.longitude,
            previous.latitude,
            previous.longitude,
        )

        return {
            "is_significant": distance > threshold_km,
            "distance_km": round(distance, 2),
            "current_location": current.display_location,
            "previous_location": previous.display_location,
        }

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two coordinates in kilometers"""
        import math

        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


# Singleton instance
_geo_service: Optional[GeoLocationService] = None


def get_geolocation_service() -> GeoLocationService:
    """Get or create the geolocation service singleton"""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoLocationService()
    return _geo_service
