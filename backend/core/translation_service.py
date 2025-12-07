"""
Translation service - wrapper for translation APIs with caching
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import requests
from deep_translator import GoogleTranslator
from deep_translator.exceptions import LanguageNotSupportedException, TranslationNotFound

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Language code mapping for LibreTranslate
# Maps our locale codes to LibreTranslate's expected codes
LIBRETRANSLATE_LANG_MAP = {
    "zh": "zh-Hans",  # Chinese -> Chinese Simplified
    "zh-CN": "zh-Hans",  # Chinese (China) -> Chinese Simplified
    "zh-TW": "zh-Hant",  # Chinese (Taiwan) -> Chinese Traditional (if supported)
}

# Reverse mapping for detection results
LIBRETRANSLATE_LANG_REVERSE_MAP = {
    "zh-Hans": "zh",
    "zh-Hant": "zh",
}


class TranslationService:
    """
    Translation service supporting multiple providers:
    - LibreTranslate (free, self-hosted, recommended)
    - Google Translate
    - DeepL (coming soon)
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self.provider = settings.TRANSLATION_PROVIDER.lower()
        logger.info(f"Translation service initialized with provider: {self.provider}")

    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key for translation"""
        content = f"{text}:{source_lang}:{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()

    def detect_language(self, text: str) -> tuple[str, float]:
        """
        Detect language of text
        Returns (language_code, confidence)
        """
        if self.provider == "libretranslate":
            try:
                url = f"{settings.LIBRETRANSLATE_URL}/detect"
                headers = {}
                if settings.LIBRETRANSLATE_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.LIBRETRANSLATE_API_KEY}"

                response = requests.post(url, json={"q": text}, headers=headers, timeout=10)
                response.raise_for_status()

                result = response.json()
                if result and len(result) > 0:
                    return result[0]["language"], result[0]["confidence"]
                return "en", 0.0

            except Exception as e:
                logger.error(f"LibreTranslate language detection failed: {e}")
                return "en", 0.0

        else:  # Google Translate or fallback
            try:
                from deep_translator import single_detection

                lang = single_detection(text, api_key=None)
                return lang, 0.95  # deep-translator doesn't provide confidence
            except Exception as e:
                logger.error(f"Language detection failed: {e}")
                return "en", 0.0

    def translate_text(
        self, text: str, target_lang: str, source_lang: Optional[str] = None
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
                "confidence": 1.0,
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
            if self.provider == "libretranslate":
                # Use LibreTranslate
                url = f"{settings.LIBRETRANSLATE_URL}/translate"
                headers = {"Content-Type": "application/json"}
                if settings.LIBRETRANSLATE_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.LIBRETRANSLATE_API_KEY}"

                # Map language codes for LibreTranslate compatibility
                lt_source = LIBRETRANSLATE_LANG_MAP.get(source_lang, source_lang)
                lt_target = LIBRETRANSLATE_LANG_MAP.get(target_lang, target_lang)

                payload = {
                    "q": text,
                    "source": lt_source,
                    "target": lt_target,
                    "format": "text",
                }

                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()

                result = response.json()
                translated = result.get("translatedText", text)

                response_data = {
                    "translated_text": translated,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "service": "libretranslate",
                    "confidence": 0.95,
                }

                # Cache the result
                self._cache[cache_key] = response_data
                logger.info(f"Translated '{text[:30]}...' from {source_lang} to {target_lang}")
                return response_data

            else:  # Google Translate (fallback)
                # Translate using Google Translate
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated = translator.translate(text)

                response_data = {
                    "translated_text": translated,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "service": "google",
                    "confidence": 0.95,
                }

                # Cache the result
                self._cache[cache_key] = response_data

                logger.info(f"Translated '{text[:30]}...' from {source_lang} to {target_lang}")
                return response_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Translation API request failed: {e}")
            return {
                "translated_text": text,
                "source_lang": source_lang or "unknown",
                "target_lang": target_lang,
                "service": "none",
                "confidence": 0.0,
                "error": str(e),
            }
        except (LanguageNotSupportedException, TranslationNotFound) as e:
            logger.error(f"Translation not supported: {e}")
            return {
                "translated_text": text,
                "source_lang": source_lang or "unknown",
                "target_lang": target_lang,
                "service": "none",
                "confidence": 0.0,
                "error": str(e),
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
                "error": str(e),
            }

    def translate_dict(
        self,
        data: Dict[str, Any],
        target_lang: str,
        source_lang: Optional[str] = None,
        translatable_fields: Optional[List[str]] = None,
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

            # Skip fields that shouldn't be translated (URLs, IDs, technical fields)
            skip_keys = {"href", "url", "link", "src", "id", "key", "slug", "code", "path", "route"}
            if key.lower() in skip_keys:
                translated[key] = value
                continue

            # Translate string values (but skip URLs)
            if isinstance(value, str) and value.strip():
                # Skip URLs and paths
                if value.startswith(("http://", "https://", "/", "#", "mailto:", "tel:")):
                    translated[key] = value
                else:
                    result = self.translate_text(value, target_lang, source_lang)
                    translated[key] = result["translated_text"]

            # Recursively translate nested dicts
            # Pass None for translatable_fields to translate ALL nested strings
            # since we're already inside a translatable field
            elif isinstance(value, dict):
                translated[key] = self.translate_dict(value, target_lang, source_lang, None)

            # Translate lists (strings or dicts)
            elif isinstance(value, list):
                translated_list = []
                for item in value:
                    if isinstance(item, str) and item.strip():
                        # Translate string items
                        result = self.translate_text(item, target_lang, source_lang)
                        translated_list.append(result["translated_text"])
                    elif isinstance(item, dict):
                        # Recursively translate dict items in list
                        translated_list.append(
                            self.translate_dict(item, target_lang, source_lang, None)
                        )
                    else:
                        # Keep other types as-is
                        translated_list.append(item)
                translated[key] = translated_list

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
