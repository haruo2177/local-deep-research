"""Tests for the Translator nodes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestTranslatorInputNode:
    """Tests for translator_input_node function."""

    @pytest.mark.asyncio
    async def test_detects_language_and_sets_state(self) -> None:
        """Should detect language and set source_language in state."""
        from src.nodes.translator import translator_input_node

        with (
            patch("src.nodes.translator.detect_language") as mock_detect,
            patch("src.nodes.translator.translate_to_english") as mock_translate,
        ):
            mock_detect.return_value = "ja"
            mock_result = MagicMock()
            mock_result.translated_text = "Hello"
            mock_translate.return_value = mock_result
            state = {"task": "こんにちは"}

            result = await translator_input_node(state)

            assert result["source_language"] == "ja"
            assert result["original_task"] == "こんにちは"
            assert result["task"] == "Hello"

    @pytest.mark.asyncio
    async def test_english_task_unchanged(self) -> None:
        """Should not translate English tasks."""
        from src.nodes.translator import translator_input_node

        with patch("src.nodes.translator.detect_language") as mock_detect:
            mock_detect.return_value = "en"
            state = {"task": "What is AI?"}

            result = await translator_input_node(state)

            assert result["source_language"] == "en"
            assert result["original_task"] == "What is AI?"
            # Task should remain unchanged for English
            assert result.get("task") == "What is AI?"

    @pytest.mark.asyncio
    async def test_translation_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should skip translation when disabled."""
        monkeypatch.setenv("ENABLE_TRANSLATION", "false")

        # Reload settings with new environment variable
        from src.config import Settings

        mock_settings = Settings()

        with patch("src.nodes.translator.settings", mock_settings):
            from src.nodes.translator import translator_input_node

            state = {"task": "こんにちは"}
            result = await translator_input_node(state)

            assert result["source_language"] == "en"
            assert result["original_task"] == "こんにちは"

    @pytest.mark.asyncio
    async def test_handles_detection_failure(self) -> None:
        """Should default to English when language detection fails."""
        from src.nodes.translator import translator_input_node

        with patch("src.nodes.translator.detect_language") as mock_detect:
            mock_detect.side_effect = Exception("Detection failed")
            state = {"task": "some text"}

            result = await translator_input_node(state)

            assert result["source_language"] == "en"


class TestTranslatorOutputNode:
    """Tests for translator_output_node function."""

    @pytest.mark.asyncio
    async def test_translates_report_to_source_language(self) -> None:
        """Should translate report back to source language."""
        from src.nodes.translator import translator_output_node

        with patch("src.nodes.translator.translate_from_english") as mock_translate:
            mock_result = MagicMock()
            mock_result.translated_text = "翻訳されたレポート"
            mock_translate.return_value = mock_result
            state = {"report": "Translated report", "source_language": "ja"}

            result = await translator_output_node(state)

            assert result["report"] == "翻訳されたレポート"

    @pytest.mark.asyncio
    async def test_english_source_no_translation(self) -> None:
        """Should not translate when source is English."""
        from src.nodes.translator import translator_output_node

        state = {"report": "English report", "source_language": "en"}
        result = await translator_output_node(state)

        # Empty dict means no changes
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_report_no_translation(self) -> None:
        """Should not translate when report is empty."""
        from src.nodes.translator import translator_output_node

        state = {"report": "", "source_language": "ja"}
        result = await translator_output_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_translation_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should skip translation when disabled."""
        monkeypatch.setenv("ENABLE_TRANSLATION", "false")

        from src.config import Settings

        mock_settings = Settings()

        with patch("src.nodes.translator.settings", mock_settings):
            from src.nodes.translator import translator_output_node

            state = {"report": "Report text", "source_language": "ja"}
            result = await translator_output_node(state)

            assert result == {}

    @pytest.mark.asyncio
    async def test_handles_translation_failure(self) -> None:
        """Should keep original report when translation fails."""
        from src.nodes.translator import translator_output_node
        from src.tools.translate import TranslationError

        with patch("src.nodes.translator.translate_from_english") as mock_translate:
            mock_translate.side_effect = TranslationError("Translation failed")
            state = {"report": "English report", "source_language": "ja"}

            result = await translator_output_node(state)

            # Empty dict means no changes (keep original report)
            assert result == {}
