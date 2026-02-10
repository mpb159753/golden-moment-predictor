import unittest
from gmp.core.exceptions import (
    GMPError, APITimeoutError, InvalidCoordinateError,
    ViewpointNotFoundError, DataDegradedWarning
)

class TestExceptions(unittest.TestCase):
    def test_api_timeout_error(self):
        err = APITimeoutError("WeatherService", 5)
        self.assertIn("WeatherService", str(err))
        self.assertIn("5s", str(err))

    def test_invalid_coordinate_error(self):
        err = InvalidCoordinateError(91.0, 181.0)
        self.assertIn("91.0", str(err))

    def test_viewpoint_not_found(self):
        err = ViewpointNotFoundError("vp_unknown")
        self.assertIn("vp_unknown", str(err))

if __name__ == '__main__':
    unittest.main()
