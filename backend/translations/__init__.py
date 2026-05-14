"""Pluggable translation module."""
from translations.service import (
    TranslatorService,
    apply_translation,
    get_translator_service,
    translate_item,
)

__all__ = [
    "TranslatorService",
    "apply_translation",
    "get_translator_service",
    "translate_item",
]
