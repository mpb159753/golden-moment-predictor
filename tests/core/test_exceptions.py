"""测试 gmp.core.exceptions 异常层级"""

import warnings

import pytest

from gmp.core.exceptions import (
    APITimeoutError,
    DataDegradedWarning,
    GMPError,
    InvalidCoordinateError,
    ViewpointNotFoundError,
)


class TestGMPErrorHierarchy:
    def test_gmp_error_hierarchy(self):
        """所有异常继承 GMPError"""
        assert issubclass(APITimeoutError, GMPError)
        assert issubclass(InvalidCoordinateError, GMPError)
        assert issubclass(ViewpointNotFoundError, GMPError)

        # GMPError 继承 Exception
        assert issubclass(GMPError, Exception)

    def test_catch_by_base_class(self):
        """可以用 GMPError 统一捕获"""
        with pytest.raises(GMPError):
            raise APITimeoutError("open-meteo", 15)

        with pytest.raises(GMPError):
            raise ViewpointNotFoundError("nonexistent")

        with pytest.raises(GMPError):
            raise InvalidCoordinateError(999.0, -999.0)


class TestAPITimeoutError:
    def test_api_timeout_message(self):
        """APITimeoutError 消息格式正确"""
        err = APITimeoutError(service="open-meteo", timeout=15)
        assert err.service == "open-meteo"
        assert err.timeout == 15
        assert "open-meteo" in str(err)
        assert "15" in str(err)
        assert "超时" in str(err)


class TestInvalidCoordinateError:
    def test_invalid_coordinate_message(self):
        """InvalidCoordinateError 消息格式正确"""
        err = InvalidCoordinateError(lat=999.0, lon=-999.0)
        assert err.lat == 999.0
        assert err.lon == -999.0
        assert "999.0" in str(err)
        assert "坐标超出范围" in str(err)


class TestViewpointNotFoundError:
    def test_viewpoint_not_found(self):
        """ViewpointNotFoundError 包含 viewpoint_id"""
        err = ViewpointNotFoundError("zheduo_gongga")
        assert err.viewpoint_id == "zheduo_gongga"
        assert "zheduo_gongga" in str(err)
        assert "未找到观景台" in str(err)


class TestDataDegradedWarning:
    def test_data_degraded_warning(self):
        """DataDegradedWarning 是 UserWarning 子类"""
        assert issubclass(DataDegradedWarning, UserWarning)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.warn("测试降级", DataDegradedWarning)
            assert len(w) == 1
            assert issubclass(w[0].category, DataDegradedWarning)
