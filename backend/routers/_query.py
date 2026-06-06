from __future__ import annotations


def qv(value):
    """Unwrap FastAPI Query/Path defaults that some older calling paths leave wrapped."""
    return getattr(value, "default", value)
