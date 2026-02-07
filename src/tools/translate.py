"""Translation tool using Helsinki-NLP/Opus-MT models."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import re

if TYPE_CHECKING:
    from transformers import MarianMTModel, MarianTokenizer


# Supported language pairs (source -> English)
SUPPORTED_LANGUAGES: dict[str, str] = {
    "ja": "Helsinki-NLP/opus-mt-ja-en",
    "zh": "Helsinki-NLP/opus-mt-zh-en",
    "ko": "Helsinki-NLP/opus-mt-ko-en",
    "de": "Helsinki-NLP/opus-mt-de-en",
    "fr": "Helsinki-NLP/opus-mt-fr-en",
    "es": "Helsinki-NLP/opus-mt-es-en",
    "ru": "Helsinki-NLP/opus-mt-ru-en",
}

# Reverse models (English -> target language)
REVERSE_MODELS: dict[str, str] = {
    "ja": "Helsinki-NLP/opus-mt-en-jap",
    "zh": "Helsinki-NLP/opus-mt-en-zh",
    "ko": "Helsinki-NLP/opus-mt-en-ko",
    "de": "Helsinki-NLP/opus-mt-en-de",
    "fr": "Helsinki-NLP/opus-mt-en-fr",
    "es": "Helsinki-NLP/opus-mt-en-es",
    "ru": "Helsinki-NLP/opus-mt-en-ru",
}


class TranslationError(Exception):
    """Translation failed."""

    pass


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    original_text: str
    translated_text: str
    source_language: str
    target_language: str


def normalize_language_code(lang_code: str) -> str:
    """Normalize language code to match supported languages.

    Args:
        lang_code: The language code to normalize (e.g., "zh-cn", "zh-tw").

    Returns:
        Normalized language code (e.g., "zh").
    """
    # Handle Chinese variants
    if lang_code.startswith("zh"):
        return "zh"
    return lang_code


def detect_language(text: str) -> str:
    """Detect the language of the given text.

    Uses langdetect library for language detection.

    Args:
        text: The text to analyze.

    Returns:
        ISO 639-1 language code (e.g., "ja", "en", "zh-cn").
    """
    if not text or not text.strip():
        return "en"

    try:
        detected = detect(text)
        return str(detected)
    except LangDetectException:
        return "en"


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> tuple[MarianTokenizer, MarianMTModel]:
    """Load and cache translation model.

    Args:
        model_name: The Hugging Face model name.

    Returns:
        Tuple of (tokenizer, model).
    """
    from transformers import MarianMTModel, MarianTokenizer

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model


def translate_to_english(text: str, source_language: str) -> TranslationResult:
    """Translate text from source language to English.

    Args:
        text: The text to translate.
        source_language: ISO 639-1 language code.

    Returns:
        TranslationResult with translated text.

    Raises:
        TranslationError: If translation fails or language not supported.
    """
    if source_language == "en":
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language="en",
            target_language="en",
        )

    # Normalize language code
    normalized_lang = normalize_language_code(source_language)

    if normalized_lang not in SUPPORTED_LANGUAGES:
        raise TranslationError(f"Unsupported language: {source_language}")

    model_name = SUPPORTED_LANGUAGES[normalized_lang]
    tokenizer, model = _load_model(model_name)

    # Tokenize and translate
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated = model.generate(**inputs)
    translated_text = str(
        tokenizer.decode(translated[0], skip_special_tokens=True)  # type: ignore[no-untyped-call]
    )

    return TranslationResult(
        original_text=text,
        translated_text=translated_text,
        source_language=source_language,
        target_language="en",
    )


def translate_from_english(text: str, target_language: str) -> TranslationResult:
    """Translate text from English to target language.

    Args:
        text: The English text to translate.
        target_language: ISO 639-1 language code.

    Returns:
        TranslationResult with translated text.

    Raises:
        TranslationError: If translation fails or language not supported.
    """
    if target_language == "en":
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language="en",
            target_language="en",
        )

    # Normalize language code
    normalized_lang = normalize_language_code(target_language)

    if normalized_lang not in REVERSE_MODELS:
        raise TranslationError(f"Unsupported target language: {target_language}")

    model_name = REVERSE_MODELS[normalized_lang]
    tokenizer, model = _load_model(model_name)

    # Tokenize and translate
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated = model.generate(**inputs)
    translated_text = str(
        tokenizer.decode(translated[0], skip_special_tokens=True)  # type: ignore[no-untyped-call]
    )
    translated_text = _postprocess_translation(translated_text, normalized_lang)

    return TranslationResult(
        original_text=text,
        translated_text=translated_text,
        source_language="en",
        target_language=target_language,
    )


def _postprocess_translation(text: str, target_language: str) -> str:
    """Clean up tokenizer spacing artifacts for CJK languages."""
    if target_language not in {"ja", "zh", "ko"}:
        return text

    # Remove spaces between CJK characters and CJK punctuation
    cjk = r"\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff"
    punct = r"\u3000-\u303f\uff01-\uff60"
    text = re.sub(rf"(?<=[{cjk}{punct}])\s+(?=[{cjk}{punct}])", "", text)
    # Also remove spaces around common ASCII punctuation when adjacent to CJK.
    text = re.sub(rf"(?<=[{cjk}])\s+([,.:;!?])", r"\1", text)
    text = re.sub(rf"([,.:;!?])\s+(?=[{cjk}])", r"\1", text)

    # Collapse multiple spaces that might remain (e.g., between Latin words)
    return re.sub(r"\s{2,}", " ", text).strip()
