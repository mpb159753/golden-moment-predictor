"""异常处理中间件 — 统一错误响应格式

设计依据:
- design/05-api.md §5.4
- design/08-operations.md §8.1

映射:
  ViewpointNotFoundError → 404
  APITimeoutError        → 408
  InvalidCoordinateError → 422
  ServiceUnavailableError→ 503
  GMPError (其他)        → 500
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from gmp.core.exceptions import (
    APITimeoutError,
    GMPError,
    InvalidCoordinateError,
    ViewpointNotFoundError,
)

logger = logging.getLogger(__name__)

# 异常类型 → (HTTP 状态码, 错误类型名称)
_EXCEPTION_MAP: dict[type, tuple[int, str]] = {
    ViewpointNotFoundError: (404, "ViewpointNotFound"),
    APITimeoutError:        (408, "APITimeout"),
    InvalidCoordinateError: (422, "InvalidParameter"),
}


async def gmp_exception_handler(request: Request, exc: GMPError) -> JSONResponse:
    """统一异常处理中间件

    将 GMPError 及其子类转换为标准 JSON 错误响应。
    """
    exc_type = type(exc)
    status_code, error_type = _EXCEPTION_MAP.get(exc_type, (500, "InternalError"))

    logger.warning(
        "gmp_error",
        extra={
            "error_type": error_type,
            "status_code": status_code,
            "detail": str(exc),
            "path": str(request.url),
        },
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": error_type,
                "message": str(exc),
                "code": status_code,
            }
        },
    )


async def service_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    """ServiceUnavailableError 处理 (定义在 core.exceptions 模块中)"""
    logger.warning(
        "service_degraded",
        extra={"detail": str(exc), "path": str(request.url)},
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "type": "ServiceDegraded",
                "message": str(exc),
                "code": 503,
            }
        },
        headers={"X-Data-Freshness": "stale"},
    )
