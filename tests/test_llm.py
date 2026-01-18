"""Tests for LLM utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCallLLM:
    """Tests for the call_llm function."""

    async def test_call_llm_returns_string(self) -> None:
        """call_llm should return a string response."""
        from src.llm import call_llm

        mock_response = MagicMock()
        mock_response.content = "This is a test response"

        with patch("src.llm.ChatOllama") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_instance

            result = await call_llm("Test prompt")

            assert isinstance(result, str)
            assert result == "This is a test response"

    async def test_call_llm_uses_specified_model(self) -> None:
        """call_llm should use the specified model."""
        from src.llm import call_llm

        mock_response = MagicMock()
        mock_response.content = "Response"

        with patch("src.llm.ChatOllama") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_instance

            await call_llm("Test prompt", model="custom-model:1b")

            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["model"] == "custom-model:1b"

    async def test_call_llm_default_model(self) -> None:
        """call_llm should use worker_model by default."""
        from src.config import settings
        from src.llm import call_llm

        mock_response = MagicMock()
        mock_response.content = "Response"

        with patch("src.llm.ChatOllama") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_instance

            await call_llm("Test prompt")

            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["model"] == settings.worker_model

    async def test_call_llm_handles_timeout(self) -> None:
        """call_llm should raise LLMError on timeout."""
        from src.llm import LLMError, call_llm

        with patch("src.llm.ChatOllama") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(side_effect=TimeoutError())
            mock_chat.return_value = mock_instance

            with pytest.raises(LLMError) as exc_info:
                await call_llm("Test prompt")

            assert "timeout" in str(exc_info.value).lower()

    async def test_call_llm_handles_connection_error(self) -> None:
        """call_llm should raise LLMError on connection error."""
        from src.llm import LLMError, call_llm

        with patch("src.llm.ChatOllama") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )
            mock_chat.return_value = mock_instance

            with pytest.raises(LLMError) as exc_info:
                await call_llm("Test prompt")

            assert "connection" in str(exc_info.value).lower()


class TestLLMError:
    """Tests for the LLMError exception class."""

    def test_llm_error_is_exception(self) -> None:
        """LLMError should be an Exception subclass."""
        from src.llm import LLMError

        assert issubclass(LLMError, Exception)

    def test_llm_error_message(self) -> None:
        """LLMError should store the error message."""
        from src.llm import LLMError

        error = LLMError("Test error message")
        assert str(error) == "Test error message"
