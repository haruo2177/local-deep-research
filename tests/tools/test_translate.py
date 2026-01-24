"""Tests for the translation tool."""

from __future__ import annotations

import pytest


class TestTranslationResult:
    """Tests for TranslationResult dataclass."""

    def test_fields_exist(self) -> None:
        """TranslationResult should have all required fields."""
        from src.tools.translate import TranslationResult

        result = TranslationResult(
            original_text="original",
            translated_text="translated",
            source_language="ja",
            target_language="en",
        )
        assert result.original_text == "original"
        assert result.translated_text == "translated"
        assert result.source_language == "ja"
        assert result.target_language == "en"


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_detect_english(self) -> None:
        """Should detect English text."""
        from src.tools.translate import detect_language

        # Use longer text to avoid misdetection
        text = "This is a longer English sentence that should be detected correctly."
        assert detect_language(text) == "en"

    def test_detect_japanese(self) -> None:
        """Should detect Japanese text."""
        from src.tools.translate import detect_language

        assert detect_language("こんにちは、元気ですか？") == "ja"

    def test_detect_chinese(self) -> None:
        """Should detect Chinese text."""
        from src.tools.translate import detect_language

        assert detect_language("你好，你好吗？") == "zh-cn"

    def test_detect_korean(self) -> None:
        """Should detect Korean text."""
        from src.tools.translate import detect_language

        assert detect_language("안녕하세요, 어떻게 지내세요?") == "ko"

    def test_empty_text_defaults_to_english(self) -> None:
        """Should default to English for empty text."""
        from src.tools.translate import detect_language

        assert detect_language("") == "en"


class TestTranslateToEnglish:
    """Tests for translate_to_english function."""

    @pytest.mark.slow
    def test_japanese_to_english(self) -> None:
        """Should translate Japanese to English."""
        from src.tools.translate import translate_to_english

        result = translate_to_english("こんにちは", "ja")
        assert result.source_language == "ja"
        assert result.target_language == "en"
        assert len(result.translated_text) > 0

    def test_english_passthrough(self) -> None:
        """Should return same text for English input."""
        from src.tools.translate import translate_to_english

        result = translate_to_english("Hello world", "en")
        assert result.translated_text == "Hello world"
        assert result.source_language == "en"
        assert result.target_language == "en"

    def test_unsupported_language_raises(self) -> None:
        """Should raise TranslationError for unsupported language."""
        from src.tools.translate import TranslationError, translate_to_english

        with pytest.raises(TranslationError):
            translate_to_english("text", "xyz")


class TestTranslateFromEnglish:
    """Tests for translate_from_english function."""

    @pytest.mark.slow
    def test_english_to_japanese(self) -> None:
        """Should translate English to Japanese."""
        from src.tools.translate import translate_from_english

        result = translate_from_english("Hello", "ja")
        assert result.source_language == "en"
        assert result.target_language == "ja"
        assert len(result.translated_text) > 0

    def test_english_passthrough(self) -> None:
        """Should return same text for English target."""
        from src.tools.translate import translate_from_english

        result = translate_from_english("Hello world", "en")
        assert result.translated_text == "Hello world"
        assert result.source_language == "en"
        assert result.target_language == "en"

    def test_unsupported_language_raises(self) -> None:
        """Should raise TranslationError for unsupported language."""
        from src.tools.translate import TranslationError, translate_from_english

        with pytest.raises(TranslationError):
            translate_from_english("text", "xyz")


class TestSupportedLanguages:
    """Tests for supported languages."""

    def test_supported_languages_constant_exists(self) -> None:
        """SUPPORTED_LANGUAGES should exist and have expected languages."""
        from src.tools.translate import SUPPORTED_LANGUAGES

        assert "ja" in SUPPORTED_LANGUAGES
        assert "zh" in SUPPORTED_LANGUAGES
        assert "ko" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES
        assert "fr" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES
        assert "ru" in SUPPORTED_LANGUAGES

    def test_reverse_models_constant_exists(self) -> None:
        """REVERSE_MODELS should exist and have expected languages."""
        from src.tools.translate import REVERSE_MODELS

        assert "ja" in REVERSE_MODELS
        assert "zh" in REVERSE_MODELS
        assert "ko" in REVERSE_MODELS


class TestNormalizeLanguageCode:
    """Tests for normalize_language_code function."""

    def test_normalize_zh_cn(self) -> None:
        """Should normalize zh-cn to zh."""
        from src.tools.translate import normalize_language_code

        assert normalize_language_code("zh-cn") == "zh"

    def test_normalize_zh_tw(self) -> None:
        """Should normalize zh-tw to zh."""
        from src.tools.translate import normalize_language_code

        assert normalize_language_code("zh-tw") == "zh"

    def test_passthrough_ja(self) -> None:
        """Should pass through ja unchanged."""
        from src.tools.translate import normalize_language_code

        assert normalize_language_code("ja") == "ja"

    def test_passthrough_en(self) -> None:
        """Should pass through en unchanged."""
        from src.tools.translate import normalize_language_code

        assert normalize_language_code("en") == "en"
