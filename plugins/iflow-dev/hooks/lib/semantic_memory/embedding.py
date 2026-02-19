"""Embedding providers for the semantic memory system.

Defines the EmbeddingProvider protocol and concrete implementations.
"""
from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

import numpy as np

from google import genai
from google.genai import types

from semantic_memory import EmbeddingError


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers.

    Any class implementing this protocol can generate vector embeddings
    from text.  Two task types are supported: ``"query"`` (for search
    queries) and ``"document"`` (for content to be indexed).
    """

    @property
    def dimensions(self) -> int:
        """Number of dimensions in the embedding vectors."""
        ...

    @property
    def provider_name(self) -> str:
        """Short identifier for the provider (e.g. 'gemini', 'ollama')."""
        ...

    @property
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        ...

    def embed(self, text: str, task_type: str = "query") -> np.ndarray:
        """Generate an embedding vector for a single text.

        Parameters
        ----------
        text:
            The text to embed.
        task_type:
            Either ``"query"`` or ``"document"``.

        Returns
        -------
        numpy.ndarray
            A float32 vector of length :attr:`dimensions`.
        """
        ...

    def embed_batch(
        self, texts: list[str], task_type: str = "document"
    ) -> list[np.ndarray]:
        """Generate embedding vectors for multiple texts.

        Parameters
        ----------
        texts:
            List of texts to embed.
        task_type:
            Either ``"query"`` or ``"document"``.

        Returns
        -------
        list[numpy.ndarray]
            A list of float32 vectors, one per input text.
        """
        ...


class GeminiProvider:
    """Embedding provider using the Google Gemini API.

    Parameters
    ----------
    api_key:
        Google API key for authentication.
    model:
        Gemini embedding model name.
    dimensions:
        Desired output dimensionality of embedding vectors.
    """

    TASK_TYPE_MAP = {
        "document": "RETRIEVAL_DOCUMENT",
        "query": "RETRIEVAL_QUERY",
    }

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimensions: int = 768,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

        # Verify SDK supports task_type at init (fail fast).
        try:
            types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=dimensions,
            )
        except TypeError as e:
            raise RuntimeError(
                "google-genai SDK does not support task_type. "
                f"Upgrade: uv add 'google-genai>=1.0'. Error: {e}"
            ) from e

    @property
    def dimensions(self) -> int:
        """Number of dimensions in the embedding vectors."""
        return self._dimensions

    @property
    def provider_name(self) -> str:
        """Short identifier for the provider."""
        return "gemini"

    @property
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        return self._model

    def _resolve_task_type(self, task_type: str) -> str:
        """Map a short task_type to the Gemini SDK constant.

        Raises EmbeddingError for unknown task types.
        """
        try:
            return self.TASK_TYPE_MAP[task_type]
        except KeyError:
            raise EmbeddingError(
                f"Unknown task_type {task_type!r}. "
                f"Valid types: {list(self.TASK_TYPE_MAP)}"
            )

    def embed(self, text: str, task_type: str = "query") -> np.ndarray:
        """Generate an embedding vector for a single text.

        Parameters
        ----------
        text:
            The text to embed.
        task_type:
            Either ``"query"`` or ``"document"``.

        Returns
        -------
        numpy.ndarray
            A float32 vector of length :attr:`dimensions`.

        Raises
        ------
        EmbeddingError
            If the API call fails or the task_type is invalid.
        """
        sdk_task_type = self._resolve_task_type(task_type)

        try:
            result = self._client.models.embed_content(
                model=self._model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=sdk_task_type,
                    output_dimensionality=self._dimensions,
                ),
            )
            return np.array(result.embeddings[0].values, dtype=np.float32)
        except Exception as e:
            raise EmbeddingError(f"Gemini embedding failed: {e}") from e

    def embed_batch(
        self, texts: list[str], task_type: str = "document"
    ) -> list[np.ndarray]:
        """Generate embedding vectors for multiple texts.

        Uses the Gemini SDK batch capability by passing a list of
        contents in a single API call.

        Parameters
        ----------
        texts:
            List of texts to embed.
        task_type:
            Either ``"query"`` or ``"document"``.

        Returns
        -------
        list[numpy.ndarray]
            A list of float32 vectors, one per input text.

        Raises
        ------
        EmbeddingError
            If the API call fails or the task_type is invalid.
        """
        sdk_task_type = self._resolve_task_type(task_type)

        try:
            result = self._client.models.embed_content(
                model=self._model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=sdk_task_type,
                    output_dimensionality=self._dimensions,
                ),
            )
            return [
                np.array(emb.values, dtype=np.float32)
                for emb in result.embeddings
            ]
        except Exception as e:
            raise EmbeddingError(f"Gemini batch embedding failed: {e}") from e


class NormalizingWrapper:
    """Wrapper that L2-normalizes vectors from any EmbeddingProvider.

    Pre-normalized vectors make cosine similarity equivalent to a dot
    product, which is important for fast matmul-based retrieval.

    Parameters
    ----------
    inner:
        The underlying embedding provider to wrap.
    """

    _ZERO_THRESHOLD = 1e-9

    def __init__(self, inner: EmbeddingProvider) -> None:
        self._inner = inner

    @property
    def dimensions(self) -> int:
        """Number of dimensions in the embedding vectors."""
        return self._inner.dimensions

    @property
    def provider_name(self) -> str:
        """Short identifier for the provider."""
        return self._inner.provider_name

    @property
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        return self._inner.model_name

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """L2-normalize a single vector.

        Raises
        ------
        EmbeddingError
            If the vector norm is below the zero threshold.
        """
        norm = float(np.linalg.norm(vec))
        if norm < self._ZERO_THRESHOLD:
            raise EmbeddingError("Zero vector detected")
        return vec / norm

    def embed(self, text: str, task_type: str = "query") -> np.ndarray:
        """Generate a unit-length embedding vector for a single text.

        Parameters
        ----------
        text:
            The text to embed.
        task_type:
            Either ``"query"`` or ``"document"``.

        Returns
        -------
        numpy.ndarray
            A float32 unit vector of length :attr:`dimensions`.

        Raises
        ------
        EmbeddingError
            If the inner provider returns a zero vector.
        """
        raw = self._inner.embed(text, task_type)
        return self._normalize(raw)

    def embed_batch(
        self, texts: list[str], task_type: str = "document"
    ) -> list[np.ndarray]:
        """Generate unit-length embedding vectors for multiple texts.

        Parameters
        ----------
        texts:
            List of texts to embed.
        task_type:
            Either ``"query"`` or ``"document"``.

        Returns
        -------
        list[numpy.ndarray]
            A list of float32 unit vectors, one per input text.

        Raises
        ------
        EmbeddingError
            If any vector in the batch is a zero vector.
        """
        raw_batch = self._inner.embed_batch(texts, task_type)
        return [self._normalize(vec) for vec in raw_batch]


# Provider name -> environment variable name for API key
_PROVIDER_ENV_KEYS: dict[str, str | None] = {
    "gemini": "GEMINI_API_KEY",
    "voyage": "VOYAGE_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def create_provider(config: dict) -> EmbeddingProvider | None:
    """Create an embedding provider from configuration.

    Reads ``memory_embedding_provider`` and ``memory_embedding_model``
    from *config*, checks for the required API key in the environment,
    and returns a :class:`NormalizingWrapper`-wrapped provider instance.

    Returns ``None`` if:
    - The required API key environment variable is not set.
    - The provider name is not recognized.
    - Provider construction fails (e.g. missing SDK).

    Parameters
    ----------
    config:
        Dictionary with ``memory_embedding_provider`` and
        ``memory_embedding_model`` keys.

    Returns
    -------
    EmbeddingProvider | None
        A NormalizingWrapper-wrapped provider, or None.
    """
    provider_name = config.get("memory_embedding_provider", "")
    model = config.get("memory_embedding_model", "")

    # Look up required env var
    env_key = _PROVIDER_ENV_KEYS.get(provider_name)
    # For providers not in the map, return None (unknown provider)
    if provider_name not in _PROVIDER_ENV_KEYS:
        return None

    # Check API key if one is required
    api_key: str | None = None
    if env_key is not None:
        api_key = os.environ.get(env_key)
        if not api_key:
            return None

    try:
        if provider_name == "gemini":
            inner = GeminiProvider(api_key=api_key, model=model)
        else:
            # Provider is in the env-key map but has no constructor yet
            # (e.g. voyage, openai -- future implementations)
            return None

        return NormalizingWrapper(inner)
    except Exception:
        return None
