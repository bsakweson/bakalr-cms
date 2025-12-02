"""
Locale and Translation models for multi-language support
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class Locale(Base, IDMixin, TimestampMixin):
    """
    Locale model - supported languages per organization
    """

    __tablename__ = "locales"

    # Organization (Tenant)
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Locale Info
    code = Column(String(10), nullable=False, index=True)  # e.g., "en", "es", "fr-FR"
    name = Column(String(100), nullable=False)  # e.g., "English", "Spanish"
    native_name = Column(String(100), nullable=True)  # e.g., "Español" for Spanish

    # Settings
    is_default = Column(Boolean, default=False, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Auto-translation settings
    auto_translate = Column(Boolean, default=True, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="locales")
    translations = relationship(
        "Translation", back_populates="locale", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Locale(id={self.id}, code='{self.code}', name='{self.name}')>"


class Translation(Base, IDMixin, TimestampMixin):
    """
    Translation model - stores translated content for entries
    """

    __tablename__ = "translations"

    # Content Entry
    content_entry_id = Column(
        GUID, ForeignKey("content_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Locale
    locale_id = Column(
        GUID, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Translation data (matches the content entry data structure)
    translated_data = Column(Text, nullable=False)  # JSON string

    # Translation metadata
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, completed, failed, manual
    source_locale = Column(String(10), nullable=True)  # Original locale code

    # Translation service used
    translation_service = Column(String(50), nullable=True)  # google, deepl, manual

    # Quality score (0-1)
    quality_score = Column(Float, nullable=True)

    # Manual override
    is_manual = Column(Boolean, default=False, nullable=False)

    # Versioning
    version = Column(Integer, default=1, nullable=False)

    # Relationships
    content_entry = relationship("ContentEntry", back_populates="translations")
    locale = relationship("Locale", back_populates="translations")

    def __repr__(self):
        return f"<Translation(id={self.id}, entry_id={self.content_entry_id}, locale_id={self.locale_id}, status='{self.status}')>"


class TranslationGlossary(Base, IDMixin, TimestampMixin):
    """
    Translation Glossary - custom terms per organization
    """

    __tablename__ = "translation_glossaries"

    # Organization (Tenant)
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Source term
    source_term = Column(String(255), nullable=False, index=True)
    source_locale = Column(String(10), nullable=False)

    # Target term
    target_term = Column(String(255), nullable=False)
    target_locale = Column(String(10), nullable=False)

    # Context
    context = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TranslationGlossary(id={self.id}, '{self.source_term}' -> '{self.target_term}')>"
