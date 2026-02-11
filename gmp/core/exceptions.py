"""GMP 异常层级定义

所有 GMP 异常均继承自 GMPError。
字段定义严格遵循 design/07-code-interface.md §7.2。
"""


class GMPError(Exception):
    """基础异常类"""
    pass


class APITimeoutError(GMPError):
    """外部 API 超时"""
    def __init__(self, service: str, timeout: int):
        self.service = service
        self.timeout = timeout
        super().__init__(f"{service} API 超时 ({timeout}s)")


class InvalidCoordinateError(GMPError):
    """坐标无效"""
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        super().__init__(f"坐标超出范围: ({lat}, {lon})")


class ViewpointNotFoundError(GMPError):
    """观景台未找到"""
    def __init__(self, viewpoint_id: str):
        self.viewpoint_id = viewpoint_id
        super().__init__(f"未找到观景台: {viewpoint_id}")


class DataDegradedWarning(UserWarning):
    """数据降级警告"""
    pass
