import json
import logging
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from . import config, store, pipeline
from .provider import ProviderError

log = logging.getLogger(__name__)


def api_errors(function):
    @wraps(function)
    def wrapped(request):
        try:
            return function(request)
        except ProviderError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            return JsonResponse({"error": str(exc)[:240]}, status=400)
        except Exception:
            # Never expose the provider exception, key, request body or transcript text.
            log.error("Transcript assistant request failed unexpectedly.")
            return JsonResponse({"error": "An unexpected local error occurred. Retry or restart the app."}, status=500)
    return wrapped


def body(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeError):
        raise ValueError("Send a valid JSON object.") from None
    if not isinstance(data, dict):
        raise ValueError("Send a JSON object.")
    return data


@require_GET
@ensure_csrf_cookie
def home(request):
    return render(request, "index.html")


@require_GET
@api_errors
def status(request):
    return JsonResponse({"documents": store.documents(), "configured": bool(config.api_key()),
                         "embedding_model": config.EMBEDDING_MODEL, "generation_model": config.GENERATION_MODEL})


@require_POST
@api_errors
def upload(request):
    source = request.FILES.get("file")
    if not source or not source.name.lower().endswith((".txt", ".srt", ".vtt")):
        raise ValueError("Choose a UTF-8 .txt, .srt, or .vtt transcript.")
    if source.size > 2_000_000:
        raise ValueError("Use a transcript file smaller than 2 MB.")
    text = source.read().decode("utf-8-sig")
    document_id, created = store.ingest(text, source.name)
    return JsonResponse({"id": document_id, "created": created})


@require_POST
@api_errors
def index(request):
    return JsonResponse(pipeline.build_index())


@require_POST
@api_errors
def ask(request):
    data = body(request)
    document_id = data.get("document_id", "")
    if not isinstance(document_id, str) or not isinstance(data.get("mode", "keyword"), str):
        raise ValueError("Invalid transcript or retrieval mode.")
    if type(data.get("top_k", 4)) is not int or type(data.get("generate", False)) is not bool:
        raise ValueError("Invalid source count or answer setting.")
    return JsonResponse(pipeline.ask(data.get("question"), data.get("mode", "keyword"),
                        data.get("top_k", 4), document_id, data.get("generate", False)))


@require_POST
@api_errors
def notes(request):
    data = body(request)
    document_id = data.get("document_id")
    if not isinstance(document_id, str) or not document_id:
        raise ValueError("Choose a single transcript for notes.")
    return JsonResponse(pipeline.notes(document_id))


def csrf_failure(request, reason=""):
    return JsonResponse({"error": "The page security token expired. Reload and try again."}, status=403)
