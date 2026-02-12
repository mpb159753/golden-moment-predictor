"""异常处理中间件 — 统一错误响应格式

设计依据:
- design/05-api.md §5.4
- design/08-operations.md §8.1

映射:
  ViewpointNotFoundError → 404
  APITimeoutError        → 408
  InvalidCoordinateError → 422
  ServiceUnavailableError→ 503 (附加 X-Data-Freshness: stale)
  GMPError (其他)        → 500
"""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from gmp.core.exceptions import (
    APITimeoutError,
    GMPError,
    InvalidCoordinateError,
    ServiceUnavailableError,
    ViewpointNotFoundError,
)

logger = structlog.get_logger(__name__)

# 异常类型 → (HTTP 状态码, 错误类型名称)
# 顺序重要: 子类必须在基类之前，由 isinstance 顺序匹配
_EXCEPTION_MAP: list[tuple[type, int, str]] = [
    (ViewpointNotFoundError, 404, "ViewpointNotFound"),
    (APITimeoutError,        408, "APITimeout"),
    (InvalidCoordinateError, 422, "InvalidParameter"),
    (ServiceUnavailableError, 503, "ServiceDegraded"),
]

# 需附加 X-Data-Freshness: stale 的状态码
_STALE_STATUS_CODES: set[int] = {503}


async def gmp_exception_handler(request: Request, exc: GMPError) -> JSONResponse:
    """统一异常处理中间件

    将 GMPError 及其子类转换为标准 JSON 错误响应。
    使用 isinstance 匹配，支持异常子类自动继承父类映射。
    """
    status_code, error_type = 500, "InternalError"

    for exc_cls, code, etype in _EXCEPTION_MAP:
        if isinstance(exc, exc_cls):
            status_code, error_type = code, etype
            break

    logger.warning(
        "gmp_error",
        error_type=error_type,
        status_code=status_code,
        detail=str(exc),
        path=str(request.url),
    )

    headers = {}
    if status_code in _STALE_STATUS_CODES:
        headers["X-Data-Freshness"] = "stale"

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": error_type,
                "message": str(exc),
                "code": status_code,
            }
        },
        headers=headers or None,
    )
