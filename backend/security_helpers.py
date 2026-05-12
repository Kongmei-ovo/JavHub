from __future__ import annotations

from fastapi.responses import JSONResponse


AUTH_EXEMPT_PATHS = {"/health"}
AUTH_DOC_PATHS = {"/docs", "/openapi.json", "/redoc"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def path_matches(path: str, prefixes: set[str]) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


def auth_error(status_code: int, detail: str, code: str = "ERR_UNAUTHORIZED") -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
    )


def requires_auth_config(path: str, method: str) -> bool:
    if path_matches(path, AUTH_DOC_PATHS):
        return True
    return method in WRITE_METHODS
