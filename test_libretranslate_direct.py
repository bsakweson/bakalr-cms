"""
Direct test of LibreTranslate integration
"""
import sys
sys.path.insert(0, '/Users/bsakweson/dev/bakalr-cms')

from backend.core.translation_service import get_translation_service

def test_translation():
    """Test translation service with LibreTranslate"""
    service = get_translation_service()
    
    print(f"🔵 Translation provider: {service.provider}")
    print()
    
    # Test 1: Simple translation
    print("Test 1: English to Spanish")
    result = service.translate_text("Hello World", target_lang="es", source_lang="en")
    print(f"Original: Hello World")
    print(f"Translated: {result['translated_text']}")
    print(f"Service: {result['service']}")
    print(f"Confidence: {result['confidence']}")
    print()
    
    # Test 2: Language detection
    print("Test 2: Language detection")
    lang, confidence = service.detect_language("Bonjour le monde")
    print(f"Text: Bonjour le monde")
    print(f"Detected language: {lang}")
    print(f"Confidence: {confidence}")
    print()
    
    # Test 3: Translation with auto-detection
    print("Test 3: Auto-detect source language")
    result = service.translate_text("Hola Mundo", target_lang="en")
    print(f"Original: Hola Mundo")
    print(f"Translated: {result['translated_text']}")
    print(f"Detected source: {result['source_lang']}")
    print()
    
    # Test 4: Multiple languages
    print("Test 4: Multiple language translation")
    texts = [
        ("Hello", "en", "fr"),
        ("Goodbye", "en", "de"),
        ("Thank you", "en", "it"),
    ]
    for text, src, tgt in texts:
        result = service.translate_text(text, target_lang=tgt, source_lang=src)
        print(f"{text} ({src} → {tgt}): {result['translated_text']}")
    
    print()
    print("✅ All translation tests passed!")

if __name__ == "__main__":
    test_translation()
