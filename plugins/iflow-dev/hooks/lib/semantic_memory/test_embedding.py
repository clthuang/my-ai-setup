"""Tests for semantic_memory.embedding module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from semantic_memory.embedding import (
    EmbeddingProvider,
    GeminiProvider,
    OllamaProvider,
)
from semantic_memory import EmbeddingError


# ---------------------------------------------------------------------------
# EmbeddingProvider Protocol tests
# ---------------------------------------------------------------------------


class TestEmbeddingProviderProtocol:
    def test_protocol_is_runtime_checkable(self):
        """EmbeddingProvider should be decorated with @runtime_checkable."""
        assert hasattr(EmbeddingProvider, "__protocol_attrs__") or hasattr(
            EmbeddingProvider, "__abstractmethods__"
        ) or isinstance(EmbeddingProvider, type)
        # A class implementing all methods should pass isinstance check
        class _FakeProvider:
            @property
            def dimensions(self) -> int:
                return 768

            @property
            def provider_name(self) -> str:
                return "fake"

            @property
            def model_name(self) -> str:
                return "fake-model"

            def embed(self, text: str, task_type: str = "query") -> np.ndarray:
                return np.zeros(768, dtype=np.float32)

            def embed_batch(
                self, texts: list[str], task_type: str = "document"
            ) -> list[np.ndarray]:
                return [np.zeros(768, dtype=np.float32)]

        assert isinstance(_FakeProvider(), EmbeddingProvider)

    def test_non_conforming_class_fails_isinstance(self):
        """A class missing required methods should NOT match the protocol."""
        class _Incomplete:
            pass

        assert not isinstance(_Incomplete(), EmbeddingProvider)

    def test_protocol_has_embed_method(self):
        """Protocol should declare an embed method."""
        assert hasattr(EmbeddingProvider, "embed")

    def test_protocol_has_embed_batch_method(self):
        """Protocol should declare an embed_batch method."""
        assert hasattr(EmbeddingProvider, "embed_batch")

    def test_protocol_has_dimensions_property(self):
        """Protocol should declare a dimensions property."""
        assert hasattr(EmbeddingProvider, "dimensions")

    def test_protocol_has_provider_name_property(self):
        """Protocol should declare a provider_name property."""
        assert hasattr(EmbeddingProvider, "provider_name")

    def test_protocol_has_model_name_property(self):
        """Protocol should declare a model_name property."""
        assert hasattr(EmbeddingProvider, "model_name")


# ---------------------------------------------------------------------------
# GeminiProvider tests (all using mocks -- no real API calls)
# ---------------------------------------------------------------------------


def _make_embed_response(values: list[float]) -> MagicMock:
    """Create a mock Gemini embed_content response."""
    embedding = MagicMock()
    embedding.values = values
    response = MagicMock()
    response.embeddings = [embedding]
    return response


def _make_batch_embed_response(batch_values: list[list[float]]) -> MagicMock:
    """Create a mock Gemini embed_content response for batch calls."""
    embeddings = []
    for values in batch_values:
        emb = MagicMock()
        emb.values = values
        embeddings.append(emb)
    response = MagicMock()
    response.embeddings = embeddings
    return response


class TestGeminiProviderInit:
    @patch("semantic_memory.embedding.genai")
    def test_creates_client_with_api_key(self, mock_genai):
        """GeminiProvider should create a genai.Client with the given API key."""
        provider = GeminiProvider(api_key="test-key-123")
        mock_genai.Client.assert_called_once_with(api_key="test-key-123")

    @patch("semantic_memory.embedding.genai")
    def test_default_model(self, mock_genai):
        """Default model should be gemini-embedding-001."""
        provider = GeminiProvider(api_key="key")
        assert provider.model_name == "gemini-embedding-001"

    @patch("semantic_memory.embedding.genai")
    def test_custom_model(self, mock_genai):
        """Should accept a custom model name."""
        provider = GeminiProvider(api_key="key", model="custom-embed-model")
        assert provider.model_name == "custom-embed-model"

    @patch("semantic_memory.embedding.genai")
    def test_default_dimensions(self, mock_genai):
        """Default dimensions should be 768."""
        provider = GeminiProvider(api_key="key")
        assert provider.dimensions == 768

    @patch("semantic_memory.embedding.genai")
    def test_custom_dimensions(self, mock_genai):
        """Should accept custom dimensions."""
        provider = GeminiProvider(api_key="key", dimensions=384)
        assert provider.dimensions == 384

    @patch("semantic_memory.embedding.genai")
    def test_provider_name(self, mock_genai):
        """provider_name should return 'gemini'."""
        provider = GeminiProvider(api_key="key")
        assert provider.provider_name == "gemini"

    @patch("semantic_memory.embedding.types.EmbedContentConfig", side_effect=TypeError("no task_type"))
    @patch("semantic_memory.embedding.genai")
    def test_raises_runtime_error_on_old_sdk(self, mock_genai, mock_config):
        """Should raise RuntimeError if SDK doesn't support task_type."""
        with pytest.raises(RuntimeError, match="google-genai SDK does not support task_type"):
            GeminiProvider(api_key="key")

    @patch("semantic_memory.embedding.genai")
    def test_task_type_map_has_document_and_query(self, mock_genai):
        """TASK_TYPE_MAP should map 'document' and 'query'."""
        assert GeminiProvider.TASK_TYPE_MAP == {
            "document": "RETRIEVAL_DOCUMENT",
            "query": "RETRIEVAL_QUERY",
        }


class TestGeminiProviderEmbed:
    @patch("semantic_memory.embedding.genai")
    def test_embed_returns_ndarray(self, mock_genai):
        """embed() should return a numpy float32 array."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_embed_response(
            [0.1, 0.2, 0.3]
        )

        provider = GeminiProvider(api_key="key", dimensions=3)
        result = provider.embed("test text")
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    @patch("semantic_memory.embedding.genai")
    def test_embed_returns_correct_values(self, mock_genai):
        """embed() should return the values from the API response."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_embed_response(
            [1.0, 2.0, 3.0]
        )

        provider = GeminiProvider(api_key="key", dimensions=3)
        result = provider.embed("hello")
        np.testing.assert_array_almost_equal(result, [1.0, 2.0, 3.0])

    @patch("semantic_memory.embedding.genai")
    def test_embed_default_task_type_is_query(self, mock_genai):
        """embed() default task_type should be 'query' -> RETRIEVAL_QUERY."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_embed_response(
            [0.1]
        )

        provider = GeminiProvider(api_key="key", dimensions=1)
        provider.embed("test")

        call_kwargs = mock_client.models.embed_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.task_type == "RETRIEVAL_QUERY"

    @patch("semantic_memory.embedding.genai")
    def test_embed_document_task_type(self, mock_genai):
        """embed(task_type='document') should use RETRIEVAL_DOCUMENT."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_embed_response(
            [0.1]
        )

        provider = GeminiProvider(api_key="key", dimensions=1)
        provider.embed("test", task_type="document")

        call_kwargs = mock_client.models.embed_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.task_type == "RETRIEVAL_DOCUMENT"

    @patch("semantic_memory.embedding.genai")
    def test_embed_passes_model_name(self, mock_genai):
        """embed() should pass the configured model name to the API."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_embed_response(
            [0.1]
        )

        provider = GeminiProvider(api_key="key", model="my-model", dimensions=1)
        provider.embed("test")

        call_kwargs = mock_client.models.embed_content.call_args
        assert call_kwargs.kwargs.get("model") or call_kwargs[1].get("model") == "my-model"

    @patch("semantic_memory.embedding.genai")
    def test_embed_passes_output_dimensionality(self, mock_genai):
        """embed() should pass output_dimensionality in the config."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_embed_response(
            [0.1] * 384
        )

        provider = GeminiProvider(api_key="key", dimensions=384)
        provider.embed("test")

        call_kwargs = mock_client.models.embed_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.output_dimensionality == 384

    @patch("semantic_memory.embedding.genai")
    def test_embed_wraps_api_errors_in_embedding_error(self, mock_genai):
        """embed() should wrap API exceptions in EmbeddingError."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.side_effect = Exception("API failure")

        provider = GeminiProvider(api_key="key")
        with pytest.raises(EmbeddingError, match="Gemini embedding failed"):
            provider.embed("test")

    @patch("semantic_memory.embedding.genai")
    def test_embed_invalid_task_type_raises_embedding_error(self, mock_genai):
        """embed() with an unknown task_type should raise EmbeddingError."""
        provider = GeminiProvider(api_key="key")
        with pytest.raises(EmbeddingError, match="Unknown task_type"):
            provider.embed("test", task_type="invalid")


class TestGeminiProviderEmbedBatch:
    @patch("semantic_memory.embedding.genai")
    def test_embed_batch_returns_list_of_ndarrays(self, mock_genai):
        """embed_batch() should return a list of numpy arrays."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_batch_embed_response(
            [[0.1, 0.2], [0.3, 0.4]]
        )

        provider = GeminiProvider(api_key="key", dimensions=2)
        result = provider.embed_batch(["text1", "text2"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(v, np.ndarray) for v in result)

    @patch("semantic_memory.embedding.genai")
    def test_embed_batch_returns_correct_values(self, mock_genai):
        """embed_batch() should return correct values for each text."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_batch_embed_response(
            [[1.0, 2.0], [3.0, 4.0]]
        )

        provider = GeminiProvider(api_key="key", dimensions=2)
        result = provider.embed_batch(["a", "b"])
        np.testing.assert_array_almost_equal(result[0], [1.0, 2.0])
        np.testing.assert_array_almost_equal(result[1], [3.0, 4.0])

    @patch("semantic_memory.embedding.genai")
    def test_embed_batch_default_task_type_is_document(self, mock_genai):
        """embed_batch() default task_type should be 'document'."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_batch_embed_response(
            [[0.1]]
        )

        provider = GeminiProvider(api_key="key", dimensions=1)
        provider.embed_batch(["text"])

        call_kwargs = mock_client.models.embed_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.task_type == "RETRIEVAL_DOCUMENT"

    @patch("semantic_memory.embedding.genai")
    def test_embed_batch_wraps_api_errors(self, mock_genai):
        """embed_batch() should wrap API errors in EmbeddingError."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.side_effect = Exception("batch fail")

        provider = GeminiProvider(api_key="key")
        with pytest.raises(EmbeddingError, match="Gemini batch embedding failed"):
            provider.embed_batch(["a", "b"])

    @patch("semantic_memory.embedding.genai")
    def test_embed_batch_invalid_task_type_raises(self, mock_genai):
        """embed_batch() with unknown task_type should raise EmbeddingError."""
        provider = GeminiProvider(api_key="key")
        with pytest.raises(EmbeddingError, match="Unknown task_type"):
            provider.embed_batch(["test"], task_type="bogus")

    @patch("semantic_memory.embedding.genai")
    def test_embed_batch_float32_dtype(self, mock_genai):
        """embed_batch() results should be float32."""
        mock_client = mock_genai.Client.return_value
        mock_client.models.embed_content.return_value = _make_batch_embed_response(
            [[0.5, 0.6]]
        )

        provider = GeminiProvider(api_key="key", dimensions=2)
        result = provider.embed_batch(["text"])
        assert result[0].dtype == np.float32


class TestGeminiProviderProtocolConformance:
    @patch("semantic_memory.embedding.genai")
    def test_isinstance_check(self, mock_genai):
        """GeminiProvider should satisfy the EmbeddingProvider protocol."""
        provider = GeminiProvider(api_key="key")
        assert isinstance(provider, EmbeddingProvider)


# ---------------------------------------------------------------------------
# OllamaProvider stub tests
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    def test_embed_raises_not_implemented(self):
        """OllamaProvider.embed() should raise NotImplementedError."""
        provider = OllamaProvider()
        with pytest.raises(NotImplementedError, match="Ollama provider not yet implemented"):
            provider.embed("test")

    def test_embed_batch_raises_not_implemented(self):
        """OllamaProvider.embed_batch() should raise NotImplementedError."""
        provider = OllamaProvider()
        with pytest.raises(NotImplementedError, match="Ollama provider not yet implemented"):
            provider.embed_batch(["test"])

    def test_dimensions_raises_not_implemented(self):
        """OllamaProvider.dimensions should raise NotImplementedError."""
        provider = OllamaProvider()
        with pytest.raises(NotImplementedError, match="Ollama provider not yet implemented"):
            _ = provider.dimensions

    def test_provider_name(self):
        """OllamaProvider.provider_name should return 'ollama'."""
        provider = OllamaProvider()
        assert provider.provider_name == "ollama"

    def test_model_name(self):
        """OllamaProvider.model_name should return 'not-configured'."""
        provider = OllamaProvider()
        assert provider.model_name == "not-configured"


# ---------------------------------------------------------------------------
# EmbeddingError re-export test
# ---------------------------------------------------------------------------


class TestEmbeddingErrorReExport:
    def test_embedding_error_importable_from_init(self):
        """EmbeddingError should be importable from semantic_memory."""
        from semantic_memory import EmbeddingError as E
        assert E is not None
        assert issubclass(E, Exception)

    def test_embedding_error_importable_from_embedding(self):
        """EmbeddingError should be re-exported from embedding module."""
        from semantic_memory.embedding import EmbeddingError as E
        assert E is not None
        assert issubclass(E, Exception)
