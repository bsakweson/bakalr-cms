"""
Translation service - wrapper for translation APIs with caching
"""
import json
import hashlib
from typing import Dict, Any, Optional, List
from deep_translator import GoogleTranslator
from deep_translator.exceptions import LanguageNotSupportedException, TranslationNotFound
import logging

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translation service with Google Translate support and caching
    For production, add DeepL using deep_translator.DeepL
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key for translation"""
        content = f"{text}:{source_lang}:{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def detect_language(self, text: str) -> tuple[str, float]:
        """
        Detect language of text using Google Translate
        Returns (language_code, confidence)
        """
        try:
            from deep_translator import single_detection
            lang = single_detection(text, api_key=None)
            return lang, 0.95  # deep-translator doesn't provide confidence
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en", 0.0
    
    def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text using Google Translate
        
        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'es', 'fr')
            source_lang: Source language code (optional, auto-detect if None)
        
        Returns:
            Dict with translated_text, detected_source_lang, confidence
        """
        if not text or not text.strip():
            return {
                "translated_text": "",
                "source_lang": source_lang or "unknown",
                "target_lang": target_lang,
                "service": "google",
                "confidence": 1.0
            }
        
        # Auto-detect source language if not provided
        if not source_lang or source_lang == "auto":
            detected_lang, _ = self.detect_language(text)
            source_lang = detected_lang
        
        # Check cache
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if cache_key in self._cache:
            logger.info(f"Translation cache hit for {source_lang} -> {target_lang}")
            return self._cache[cache_key]
        
        try:
            # Translate using Google Translate
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = translator.translate(text)
            
            response = {
                "translated_text": translated,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "service": "google",
                "confidence": 0.95
            }
            
            # Cache the result
            self._cache[cache_key] = response
            
            logger.info(f"Translated '{text[:30]}...' from {source_lang} to {target_lang}")
            return response
            
        except (LanguageNotSupportedException, TranslationNotFound) as e:
            logger.error(f"Translation not supported: {e}")
            return {
                "translated_text": text,
                "source_lang": source_lang or "unknown",
                "target_lang": target_lang,
                "service": "none",
                "confidence": 0.0,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text on failure
            return {
                "translated_text": text,
                "source_lang": source_lang or "unknown",
                "target_lang": target_lang,
                "service": "none",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def translate_dict(
        self,
        data: Dict[str, Any],
        target_lang: str,
        source_lang: Optional[str] = None,
        translatable_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Translate specific fields in a dictionary
        
        Args:
            data: Dictionary with content to translate
            target_lang: Target language code
            source_lang: Source language code (optional)
            translatable_fields: List of field names to translate (if None, translate all string values)
        
        Returns:
            Dictionary with translated fields
        """
        translated = {}
        
        for key, value in data.items():
            # Skip if not in translatable_fields list (when provided)
            if translatable_fields and key not in translatable_fields:
                translated[key] = value
                continue
            
            # Translate string values
            if isinstance(value, str) and value.strip():
                result = self.translate_text(value, target_lang, source_lang)
                translated[key] = result["translated_text"]
            
            # Recursively translate nested dicts
            elif isinstance(value, dict):
                translated[key] = self.translate_dict(
                    value,
                    target_lang,
                    source_lang,
                    translatable_fields
                )
            
            # Translate lists of strings
            elif isinstance(value, list):
                translated[key] = [
                    self.translate_text(item, target_lang, source_lang)["translated_text"]
                    if isinstance(item, str) and item.strip()
                    else item
                    for item in value
                ]
            
            # Keep other types as-is
            else:
                translated[key] = value
        
        return translated
    
    def clear_cache(self):
        """Clear translation cache"""
        self._cache.clear()
        logger.info("Translation cache cleared")


# Global translation service instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create translation service instance"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
