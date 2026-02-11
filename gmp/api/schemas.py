"""Pydantic 请求/响应模型

设计依据: design/05-api.md §5.1-5.4
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """错误详情"""
    type: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    code: int = Field(..., description="HTTP 状态码")


class ErrorResponse(BaseModel):
    """统一错误响应 — 参见 design/05-api.md §5.4"""
    error: ErrorDetail = Field(..., examples=[{
        "type": "ViewpointNotFound",
        "message": "未找到观景台: invalid_id",
        "code": 404,
    }])


class PaginationResponse(BaseModel):
    """分页元数据"""
    page: int
    page_size: int
    total: int
    total_pages: int


class ViewpointItem(BaseModel):
    """观景台列表项"""
    id: str
    name: str
    location: dict
    capabilities: list[str]
    targets: list[dict]


class ViewpointListResponse(BaseModel):
    """GET /api/v1/viewpoints 响应"""
    viewpoints: list[ViewpointItem]
    pagination: PaginationResponse
