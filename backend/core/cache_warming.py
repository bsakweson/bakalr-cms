"""
Cache warming service for preloading frequently accessed content.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import desc

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry

logger = logging.getLogger(__name__)


class CacheWarmingService:
    """Service for warming up cache with popular content."""

    def __init__(self):
        self.is_warming = False

    async def warm_popular_content(self, limit: int = 50, days_lookback: int = 7) -> int:
        """
        Warm cache with most recently published/updated content.

        Args:
            limit: Number of content entries to warm
            days_lookback: Only consider content from last N days

        Returns:
            Number of entries cached
        """
        if self.is_warming:
            logger.info("Cache warming already in progress, skipping")
            return 0

        self.is_warming = True
        cached_count = 0

        try:
            db = SessionLocal()
            try:
                # Get recently published content
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)

                entries = (
                    db.query(ContentEntry)
                    .filter(ContentEntry.updated_at >= cutoff_date)
                    .order_by(desc(ContentEntry.updated_at))
                    .limit(limit)
                    .all()
                )

                logger.info(f"Warming cache with {len(entries)} content entries")

                for entry in entries:
                    try:
                        # Cache by ID
                        cache_key = f"content_entry:{entry.id}"
                        await cache_manager.set(cache_key, entry, ttl=3600)  # 1 hour

                        # Cache by slug
                        slug_key = f"content_slug:{entry.slug}"
                        await cache_manager.set(slug_key, entry, ttl=3600)

                        cached_count += 1

                    except Exception as e:
                        logger.error(f"Failed to cache entry {entry.id}: {e}")

                logger.info(f"Successfully warmed cache with {cached_count} entries")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
        finally:
            self.is_warming = False

        return cached_count

    async def warm_content_types(self) -> int:
        """
        Warm cache with content type definitions.

        Returns:
            Number of content types cached
        """
        from backend.models.content import ContentType

        cached_count = 0
        db = SessionLocal()

        try:
            content_types = db.query(ContentType).all()

            for ct in content_types:
                try:
                    cache_key = f"content_type:{ct.id}"
                    await cache_manager.set(
                        cache_key, ct, ttl=7200  # 2 hours (types change rarely)
                    )

                    # Also cache by name
                    name_key = f"content_type_name:{ct.name}"
                    await cache_manager.set(name_key, ct, ttl=7200)

                    cached_count += 1

                except Exception as e:
                    logger.error(f"Failed to cache content type {ct.id}: {e}")

            logger.info(f"Warmed cache with {cached_count} content types")

        finally:
            db.close()

        return cached_count

    async def warm_translations(self, locales: Optional[List[str]] = None) -> int:
        """
        Warm cache with translation entries.

        Args:
            locales: Specific locales to warm (default: all)

        Returns:
            Number of translations cached
        """
        from backend.models.translation import Locale, Translation

        cached_count = 0
        db = SessionLocal()

        try:
            query = db.query(Translation)

            if locales:
                locale_objs = db.query(Locale).filter(Locale.code.in_(locales)).all()
                locale_ids = [loc.id for loc in locale_objs]
                query = query.filter(Translation.locale_id.in_(locale_ids))

            translations = query.limit(1000).all()  # Limit to avoid memory issues

            for trans in translations:
                try:
                    cache_key = f"translation:{trans.entry_id}:{trans.locale_id}"
                    await cache_manager.set(cache_key, trans, ttl=3600)
                    cached_count += 1

                except Exception as e:
                    logger.error(f"Failed to cache translation {trans.id}: {e}")

            logger.info(f"Warmed cache with {cached_count} translations")

        finally:
            db.close()

        return cached_count

    async def warm_all(self) -> dict:
        """
        Warm all cache categories.

        Returns:
            Dictionary with counts for each category
        """
        logger.info("Starting comprehensive cache warming")

        results = {
            "content_entries": await self.warm_popular_content(),
            "content_types": await self.warm_content_types(),
            "translations": await self.warm_translations(),
        }

        total = sum(results.values())
        logger.info(f"Cache warming complete: {total} total items cached")

        return results


# Global instance
cache_warming_service = CacheWarmingService()
