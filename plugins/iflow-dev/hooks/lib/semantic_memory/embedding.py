"""Embedding providers for the semantic memory system.

Defines the EmbeddingProvider protocol and concrete implementations.
"""
from __future__ import annotations

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


class OllamaProvider:
    """Stub embedding provider for Ollama.

    Not yet implemented -- all embedding methods raise
    ``NotImplementedError``.
    """

    @property
    def dimensions(self) -> int:
        """Not implemented."""
        raise NotImplementedError("Ollama provider not yet implemented")

    @property
    def provider_name(self) -> str:
        """Short identifier for the provider."""
        return "ollama"

    @property
    def model_name(self) -> str:
        """Placeholder model name."""
        return "not-configured"

    def embed(self, text: str, task_type: str = "query") -> np.ndarray:
        """Not implemented."""
        raise NotImplementedError("Ollama provider not yet implemented")

    def embed_batch(
        self, texts: list[str], task_type: str = "document"
    ) -> list[np.ndarray]:
        """Not implemented."""
        raise NotImplementedError("Ollama provider not yet implemented")
