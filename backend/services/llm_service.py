"""
LLM service abstraction with provider fallback.
Supports Rapidfire, Gemini, and OpenAI in configurable order.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from backend.config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER_ORDER,
    OPENAI_API_KEY,
    RAPIDFIRE_API_KEY,
    RAPIDFIRE_BASE_URL,
    RAPIDFIRE_MODEL,
)

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    used_fallback: bool


class LLMService:
    """Provider-agnostic text generation with fallback order."""

    def __init__(
        self,
        provider_order: list[str] | None = None,
        rapidfire_client: Any = None,
        openai_api_key: str = "",
        gemini_api_key: str = "",
        rapidfire_api_key: str = "",
        rapidfire_base_url: str = "",
    ):
        self.provider_order = provider_order or LLM_PROVIDER_ORDER
        self.rapidfire_client = rapidfire_client
        self.openai_api_key = openai_api_key or OPENAI_API_KEY
        self.gemini_api_key = gemini_api_key or GEMINI_API_KEY
        self.rapidfire_api_key = rapidfire_api_key or RAPIDFIRE_API_KEY
        self.rapidfire_base_url = rapidfire_base_url or RAPIDFIRE_BASE_URL

    async def generate_email(
        self,
        prompt: str,
        context_documents: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> LLMResult:
        """Try providers in configured order and return first successful response."""
        context_documents = context_documents or []
        errors: list[str] = []

        for idx, provider in enumerate(self.provider_order):
            try:
                if provider == "rapidfire":
                    text = await self._generate_with_rapidfire(
                        prompt=prompt,
                        context_documents=context_documents,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if text:
                        return LLMResult(
                            text=text,
                            provider="rapidfire",
                            model=RAPIDFIRE_MODEL,
                            used_fallback=idx > 0,
                        )

                elif provider == "gemini":
                    text = await self._generate_with_gemini(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if text:
                        return LLMResult(
                            text=text,
                            provider="gemini",
                            model=GEMINI_MODEL,
                            used_fallback=idx > 0,
                        )

                elif provider == "openai":
                    text = await self._generate_with_openai(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if text:
                        return LLMResult(
                            text=text,
                            provider="openai",
                            model="gpt-4o",
                            used_fallback=idx > 0,
                        )
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))

    async def generate_with_provider(
        self,
        provider: str,
        prompt: str,
        context_documents: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> LLMResult:
        """Force-call a single provider without fallback."""
        context_documents = context_documents or []
        provider = provider.strip().lower()

        if provider == "rapidfire":
            text = await self._generate_with_rapidfire(
                prompt=prompt,
                context_documents=context_documents,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResult(
                text=text,
                provider="rapidfire",
                model=RAPIDFIRE_MODEL,
                used_fallback=False,
            )

        if provider == "gemini":
            text = await self._generate_with_gemini(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResult(
                text=text,
                provider="gemini",
                model=GEMINI_MODEL,
                used_fallback=False,
            )

        if provider == "openai":
            text = await self._generate_with_openai(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResult(
                text=text,
                provider="openai",
                model="gpt-4o",
                used_fallback=False,
            )

        raise RuntimeError(f"Unsupported provider '{provider}'")

    async def _generate_with_rapidfire(
        self,
        prompt: str,
        context_documents: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if self.rapidfire_client:
            return await self.rapidfire_client.generate(
                prompt=prompt,
                context_documents=context_documents,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        if not (self.rapidfire_api_key and self.rapidfire_base_url):
            raise RuntimeError("Rapidfire client/key/base_url not configured")

        payload = {
            "model": RAPIDFIRE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "context_documents": context_documents,
        }
        headers = {
            "Authorization": f"Bearer {self.rapidfire_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.rapidfire_base_url.rstrip('/')}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # OpenAI-style response parsing
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or data.get("output_text") or ""
        if not content:
            raise RuntimeError("Rapidfire response missing content")
        return content

    async def _generate_with_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self.gemini_api_key:
            raise RuntimeError("Gemini API key not configured")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={self.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini response has no candidates")
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise RuntimeError("Gemini response missing text")
        return text

    async def _generate_with_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not HAS_OPENAI:
            raise RuntimeError("openai package not installed")
        if not self.openai_api_key:
            raise RuntimeError("OpenAI API key not configured")

        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def embed_text(self, text: str) -> list[float]:
        """
        Embedding backend selection:
        - EMBEDDING_PROVIDER=openai|gemini|auto
        - auto preference: OpenAI -> Gemini
        """
        provider = EMBEDDING_PROVIDER
        if provider == "auto":
            if self.openai_api_key:
                provider = "openai"
            elif self.gemini_api_key:
                provider = "gemini"
            else:
                raise RuntimeError("No embedding provider configured: set OPENAI_API_KEY or GEMINI_API_KEY")

        if provider == "openai":
            return await self._embed_with_openai(text)
        if provider == "gemini":
            return await self._embed_with_gemini(text)
        raise RuntimeError(f"Unsupported embedding provider '{provider}'")

    async def _embed_with_openai(self, text: str) -> list[float]:
        if not HAS_OPENAI:
            raise RuntimeError("openai package not installed for embeddings")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")

        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIM,
        )
        return response.data[0].embedding

    async def _embed_with_gemini(self, text: str) -> list[float]:
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini embeddings")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{EMBEDDING_MODEL}:embedContent?key={self.gemini_api_key}"
        )
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT",
            "outputDimensionality": EMBEDDING_DIM,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        embedding = (data.get("embedding") or {}).get("values") or []
        if not embedding:
            raise RuntimeError("Gemini embedding response missing values")
        return embedding
