from typing import List, Optional

from django.conf import settings

from document_extraction.constants.extraction_constants import GEMINI_API_KEY_VARIABLE
from document_extraction.exceptions.extraction_exceptions import (
    ExtractionCredentialMissing,
)

_CACHED_CLIENT = None


def get_gemini_client():
    # Cached deliberately: a per-call client is garbage collected mid-request and
    # closes the underlying httpx session.
    global _CACHED_CLIENT
    if _CACHED_CLIENT is None:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            raise ExtractionCredentialMissing(variable_name=GEMINI_API_KEY_VARIABLE)
        from google import genai

        _CACHED_CLIENT = genai.Client(api_key=api_key)
    return _CACHED_CLIENT


def reset_gemini_client() -> None:
    global _CACHED_CLIENT
    _CACHED_CLIENT = None


def build_image_parts(page_images: List[bytes]) -> list:
    from google.genai import types

    return [
        types.Part.from_bytes(data=page_image, mime_type="image/png")
        for page_image in page_images
    ]


def build_json_config(response_schema, temperature: float = 0.0):
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=temperature,
        # A pydantic response_schema otherwise trips the library's automatic
        # function calling notice on every call.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def build_text_part(text: str):
    from google.genai import types

    return types.Part.from_text(text=text)


def generate_parsed(model: str, parts: list, response_schema) -> Optional[object]:
    response = get_gemini_client().models.generate_content(
        model=model, contents=parts, config=build_json_config(response_schema)
    )
    return response.parsed
