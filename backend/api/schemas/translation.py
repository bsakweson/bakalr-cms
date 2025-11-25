"""
Translation and Locale API schemas
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# Locale Schemas

class LocaleCreate(BaseModel):
    """Schema for creating a locale"""
    code: str = Field(..., description="Locale code (e.g., 'en', 'es', 'fr-FR')")
    name: str = Field(..., description="Locale name (e.g., 'English', 'Spanish')")
    native_name: Optional[str] = Field(None, description="Native name (e.g., 'Español')")
    is_default: bool = Field(False, description="Is this the default locale?")
    is_enabled: bool = Field(True, description="Is this locale enabled?")
    auto_translate: bool = Field(True, description="Enable automatic translation?")


class LocaleUpdate(BaseModel):
    """Schema for updating a locale"""
    name: Optional[str] = None
    native_name: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
    auto_translate: Optional[bool] = None


class LocaleResponse(BaseModel):
    """Schema for locale response"""
    id: int
    organization_id: int
    code: str
    name: str
    native_name: Optional[str]
    is_default: bool
    is_enabled: bool
    auto_translate: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Translation Schemas

class TranslationCreate(BaseModel):
    """Schema for creating a translation"""
    content_entry_id: int
    locale_id: int
    translated_data: Dict[str, Any]
    source_locale: Optional[str] = None
    is_manual: bool = False


class TranslationUpdate(BaseModel):
    """Schema for updating a translation"""
    translated_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    quality_score: Optional[float] = None
    is_manual: Optional[bool] = None


class TranslationResponse(BaseModel):
    """Schema for translation response"""
    id: int
    content_entry_id: int
    locale_id: int
    translated_data: Dict[str, Any]
    status: str
    source_locale: Optional[str]
    translation_service: Optional[str]
    quality_score: Optional[float]
    is_manual: bool
    version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TranslationListResponse(BaseModel):
    """Schema for paginated translation list"""
    items: List[TranslationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TranslateRequest(BaseModel):
    """Schema for translation request"""
    content_entry_id: int
    target_locale_ids: List[int] = Field(..., description="List of locale IDs to translate to")
    force_retranslate: bool = Field(False, description="Force re-translation even if exists")


class TranslateResponse(BaseModel):
    """Schema for translation job response"""
    content_entry_id: int
    translations: List[TranslationResponse]
    message: str


# Translation Glossary Schemas

class GlossaryCreate(BaseModel):
    """Schema for creating a glossary entry"""
    source_term: str
    source_locale: str
    target_term: str
    target_locale: str
    context: Optional[str] = None


class GlossaryUpdate(BaseModel):
    """Schema for updating a glossary entry"""
    source_term: Optional[str] = None
    target_term: Optional[str] = None
    context: Optional[str] = None


class GlossaryResponse(BaseModel):
    """Schema for glossary entry response"""
    id: int
    organization_id: int
    source_term: str
    source_locale: str
    target_term: str
    target_locale: str
    context: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LocaleDetectionResponse(BaseModel):
    """Schema for locale detection response"""
    detected_locale: str
    confidence: float
    fallback_chain: List[str]
    source: str  # header, user_preference, ip, default
