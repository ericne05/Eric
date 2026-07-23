"""
Deterministic Embedding Provider (Development/Testing).

Produces stable, reproducible embeddings based on text hash.
Ensures test results are always consistent across runs.
Swappable via DI: container.add_singleton(IEmbeddingProvider, GeminiEmbeddingProvider)
"""

import hashlib
import struct

from core.memory.interfaces import IEmbeddingProvider


class DeterministicEmbeddingProvider(IEmbeddingProvider):
    """
    Generates deterministic embedding vectors from text content.

    The same text always produces the same vector, making tests
    reproducible and assertions stable. Uses SHA-256 hash to derive
    floating-point components.

    Args:
        dim: Dimensionality of the output vectors.
    """

    def __init__(self, dim: int = 768) -> None:
        self._dim = dim

    def embed(self, text: str) -> list[float]:
        """
        Generate a deterministic embedding for a single text.

        Uses SHA-256 hash extended to fill the required dimension.
        Output values are normalized to the range [-1.0, 1.0].
        """
        return self._hash_to_vector(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def dimension(self) -> int:
        """Return the configured dimensionality."""
        return self._dim

    def _hash_to_vector(self, text: str) -> list[float]:
        """
        Convert text to a deterministic float vector via SHA-256 hashing.

        Strategy: hash the text with incrementing salt to produce enough
        bytes, then convert each 4-byte chunk to a float in [-1, 1].
        """
        vector: list[float] = []
        chunk_index = 0

        while len(vector) < self._dim:
            # Hash text with a chunk index salt for more bytes
            salted = f"{text}:{chunk_index}"
            digest = hashlib.sha256(salted.encode("utf-8")).digest()

            # Each 32-byte digest gives us 8 floats (4 bytes each)
            for i in range(0, len(digest), 4):
                if len(vector) >= self._dim:
                    break
                # Unpack 4 bytes as unsigned int, then normalize to [-1, 1]
                (value,) = struct.unpack(">I", digest[i : i + 4])
                normalized = (value / (2**32 - 1)) * 2.0 - 1.0
                vector.append(normalized)

            chunk_index += 1

        return vector[: self._dim]
