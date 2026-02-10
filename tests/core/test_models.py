import unittest
from datetime import datetime
from gmp.core.models import (
    Location, Target, Viewpoint, SunEvents,
    MoonStatus, StargazingWindow, AnalysisResult, ScoreResult,
    DataRequirement, DataContext
)

class TestModels(unittest.TestCase):
    def test_location_initialization(self):
        loc = Location(lat=30.0, lon=102.0, altitude=3000)
        self.assertEqual(loc.lat, 30.0)
        self.assertEqual(loc.lon, 102.0)
        self.assertEqual(loc.altitude, 3000)

    def test_target_defaults(self):
        target = Target(name="Gongga", lat=29.0, lon=101.0, altitude=7556, weight="primary")
        self.assertIsNone(target.applicable_events)

    def test_viewpoint_structure(self):
        loc = Location(lat=30.0, lon=102.0, altitude=3000)
        target = Target(name="Gongga", lat=29.0, lon=101.0, altitude=7556, weight="primary")
        vp = Viewpoint(
            id="vp_001",
            name="Test Viewpoint",
            location=loc,
            capabilities=["sunrise"],
            targets=[target]
        )
        self.assertEqual(vp.name, "Test Viewpoint")
        self.assertEqual(len(vp.targets), 1)

    def test_data_requirement_defaults(self):
        req = DataRequirement()
        self.assertFalse(req.needs_l2_target)
        self.assertFalse(req.needs_astro)
        self.assertIsNone(req.season_months)

if __name__ == '__main__':
    unittest.main()
