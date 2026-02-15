"""gmp/core/exceptions.py — 自定义异常类层次

所有 GMP 特定异常均继承自 GMPError，可通过 except GMPError 统一捕获。
DataDegradedWarning 继承自 UserWarning，用于数据降级场景的警告。
"""


class GMPError(Exception):
    """GMP 基础异常类"""


class APITimeoutError(GMPError):
    """外部 API 超时"""

    def __init__(self, service: str, timeout: int) -> None:
        self.service = service
        self.timeout = timeout
        super().__init__(f"{service} API 超时 ({timeout}s)")


class InvalidCoordinateError(GMPError):
    """坐标无效"""

    def __init__(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon
        super().__init__(f"坐标超出范围: ({lat}, {lon})")


class ViewpointNotFoundError(GMPError):
    """观景台未找到"""

    def __init__(self, viewpoint_id: str) -> None:
        self.viewpoint_id = viewpoint_id
        super().__init__(f"未找到观景台: {viewpoint_id}")


class RouteNotFoundError(GMPError):
    """线路未找到"""

    def __init__(self, route_id: str) -> None:
        self.route_id = route_id
        super().__init__(f"未找到线路: {route_id}")


class DataDegradedWarning(UserWarning):
    """数据降级警告"""


class InvalidDateError(GMPError):
    """日期无效"""

    def __init__(self, date: object, reason: str) -> None:
        self.date = date
        super().__init__(f"日期无效: {date} ({reason})")


class ServiceUnavailableError(GMPError):
    """外部服务不可用（API 失败且无缓存）"""
