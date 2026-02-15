"""tests/unit/test_exceptions.py — 自定义异常类测试"""

import warnings

import pytest

from gmp.core.exceptions import (
    GMPError,
    APITimeoutError,
    InvalidCoordinateError,
    ViewpointNotFoundError,
    RouteNotFoundError,
    DataDegradedWarning,
    InvalidDateError,
    ServiceUnavailableError,
)


# ==================== GMPError 层次 ====================

class TestGMPErrorHierarchy:
    """所有自定义异常均为 GMPError 子类，可统一捕获"""

    def test_api_timeout_is_gmp_error(self):
        assert issubclass(APITimeoutError, GMPError)

    def test_invalid_coordinate_is_gmp_error(self):
        assert issubclass(InvalidCoordinateError, GMPError)

    def test_viewpoint_not_found_is_gmp_error(self):
        assert issubclass(ViewpointNotFoundError, GMPError)

    def test_route_not_found_is_gmp_error(self):
        assert issubclass(RouteNotFoundError, GMPError)

    def test_invalid_date_is_gmp_error(self):
        assert issubclass(InvalidDateError, GMPError)

    def test_service_unavailable_is_gmp_error(self):
        assert issubclass(ServiceUnavailableError, GMPError)

    def test_data_degraded_is_not_gmp_error(self):
        assert not issubclass(DataDegradedWarning, GMPError)

    def test_data_degraded_is_user_warning(self):
        assert issubclass(DataDegradedWarning, UserWarning)

    def test_catch_all_gmp_errors(self):
        """except GMPError 可统一捕获所有自定义异常"""
        errors = [
            APITimeoutError("test-svc", 30),
            InvalidCoordinateError(91.0, 181.0),
            ViewpointNotFoundError("vp-404"),
            RouteNotFoundError("rt-404"),
            InvalidDateError("2025-13-01", "月份超出范围"),
            ServiceUnavailableError("外部服务不可用"),
        ]
        for err in errors:
            with pytest.raises(GMPError):
                raise err


# ==================== APITimeoutError ====================

class TestAPITimeoutError:
    def test_attributes(self):
        err = APITimeoutError("open-meteo", 30)
        assert err.service == "open-meteo"
        assert err.timeout == 30

    def test_str_message(self):
        err = APITimeoutError("open-meteo", 30)
        assert "open-meteo" in str(err)
        assert "30" in str(err)


# ==================== InvalidCoordinateError ====================

class TestInvalidCoordinateError:
    def test_attributes(self):
        err = InvalidCoordinateError(91.0, 181.0)
        assert err.lat == 91.0
        assert err.lon == 181.0

    def test_str_message(self):
        err = InvalidCoordinateError(91.0, 181.0)
        msg = str(err)
        assert "91.0" in msg
        assert "181.0" in msg


# ==================== ViewpointNotFoundError ====================

class TestViewpointNotFoundError:
    def test_attributes(self):
        err = ViewpointNotFoundError("niubei")
        assert err.viewpoint_id == "niubei"

    def test_str_message(self):
        err = ViewpointNotFoundError("niubei")
        assert "niubei" in str(err)


# ==================== RouteNotFoundError ====================

class TestRouteNotFoundError:
    def test_attributes(self):
        err = RouteNotFoundError("lixiao")
        assert err.route_id == "lixiao"

    def test_str_message(self):
        err = RouteNotFoundError("lixiao")
        assert "lixiao" in str(err)


# ==================== InvalidDateError ====================

class TestInvalidDateError:
    def test_attributes(self):
        err = InvalidDateError("2025-13-01", "月份超出范围")
        assert err.date == "2025-13-01"

    def test_str_message(self):
        err = InvalidDateError("2025-13-01", "月份超出范围")
        msg = str(err)
        assert "2025-13-01" in msg
        assert "月份超出范围" in msg


# ==================== ServiceUnavailableError ====================

class TestServiceUnavailableError:
    def test_raise_and_catch(self):
        with pytest.raises(ServiceUnavailableError):
            raise ServiceUnavailableError("Open-Meteo 不可用")

    def test_str_message(self):
        err = ServiceUnavailableError("Open-Meteo 不可用")
        assert "Open-Meteo 不可用" in str(err)


# ==================== DataDegradedWarning ====================

class TestDataDegradedWarning:
    def test_issue_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.warn("数据降级", DataDegradedWarning)
            assert len(w) == 1
            assert issubclass(w[0].category, DataDegradedWarning)
