"""Small Gemini REST adapter. No model output is fabricated when unavailable."""
import json
import re
import urllib.error
import urllib.request
from . import config
from .retrieval import normalize


class ProviderError(Exception):
    pass


class Gemini:
    def _post(self, model, method, payload):
        if not config.api_key():
            raise ProviderError("Add GEMINI_API_KEY to your local .env and restart. Search-only mode needs no key.")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise ProviderError("Invalid model name in local configuration.")
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}",
            data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": config.api_key()})
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.loads(response.read(5_000_000))
        except urllib.error.HTTPError as exc:
            messages = {400: "The model rejected the request. Check model compatibility and configuration.",
                        401: "The API key was rejected.", 403: "The key or account cannot access this model.",
                        404: "This model is unavailable. Check its name and your account access.",
                        429: "API quota reached. Wait before trying again or check AI Studio quotas."}
            raise ProviderError(messages.get(exc.code, "The AI provider is unavailable. Try again later.")) from None
        except (OSError, ValueError) as exc:
            raise ProviderError("The AI provider could not be reached or returned an unreadable response.") from None

    def embed(self, texts, query=False):
        requests = [{"model": "models/" + config.EMBEDDING_MODEL,
                     "content": {"parts": [{"text": text}]},
                     "taskType": "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT",
                     "outputDimensionality": config.DIMENSIONS} for text in texts]
        data = self._post(config.EMBEDDING_MODEL, "batchEmbedContents", {"requests": requests})
        try:
            vectors = [normalize(v["values"], config.DIMENSIONS) for v in data["embeddings"]]
            if len(vectors) != len(texts):
                raise ValueError("Wrong batch size")
            return vectors
        except (ValueError, KeyError, TypeError):
            raise ProviderError("The embedding response was invalid. No incompatible vectors were stored.") from None

    def generate(self, system, prompt):
        data = self._post(config.GENERATION_MODEL, "generateContent", {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 4096}})
        try:
            candidate = data["candidates"][0]
            if candidate.get("finishReason") not in (None, "STOP"):
                raise ValueError("Incomplete or blocked response")
            parts = candidate["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            result = json.loads(text)
            return result, data.get("usageMetadata", {})
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("The model did not return a complete JSON answer. No generated answer was accepted.") from None
