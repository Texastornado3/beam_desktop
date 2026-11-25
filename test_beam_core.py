import unittest

from beam_core import (
    LUMBER_SECTIONS,
    STEEL_SECTIONS,
    PointLoad,
    UniformLoad,
    analyze_beam,
    bending_stress,
    deflection_limit,
)


class BeamCoreValidationTests(unittest.TestCase):
    def test_simply_supported_uniform_load(self):
        result = analyze_beam(
            "Simply supported",
            20,
            [],
            [UniformLoad(1.0, 0, 20)],
            29000,
            204,
        )
        section = next(item for item in STEEL_SECTIONS if item["name"] == "W12x26")
        self.assertAlmostEqual(result.left_reaction, 10.0, places=6)
        self.assertAlmostEqual(result.right_reaction, 10.0, places=6)
        self.assertAlmostEqual(result.max_moment, 50.0, places=2)
        self.assertAlmostEqual(result.max_moment_x, 10.0, places=2)
        self.assertAlmostEqual(bending_stress(result.max_moment, section["Sx"]), 17.96, places=2)
        self.assertAlmostEqual(abs(result.max_deflection), 0.609, places=2)
        self.assertAlmostEqual(deflection_limit(20, 360), 0.667, places=3)

    def test_simply_supported_point_load(self):
        result = analyze_beam(
            "Simply supported",
            20,
            [PointLoad(10.0, 5)],
            [],
            29000,
            204,
        )
        section = next(item for item in STEEL_SECTIONS if item["name"] == "W12x26")
        self.assertAlmostEqual(result.left_reaction, 7.5, places=6)
        self.assertAlmostEqual(result.right_reaction, 2.5, places=6)
        self.assertAlmostEqual(result.max_moment, 37.5, places=2)
        self.assertAlmostEqual(bending_stress(result.max_moment, section["Sx"]), 13.47, places=2)
        self.assertAlmostEqual(abs(result.max_deflection), 0.340, places=2)

    def test_cantilever_point_load(self):
        result = analyze_beam(
            "Cantilever",
            10,
            [PointLoad(5.0, 10)],
            [],
            29000,
            204,
        )
        self.assertAlmostEqual(result.left_reaction, 5.0, places=6)
        self.assertAlmostEqual(result.fixed_moment, 50.0, places=6)
        self.assertAlmostEqual(abs(result.max_deflection), 0.487, places=2)
        self.assertAlmostEqual(deflection_limit(10, 360), 0.333, places=3)

    def test_lumber_uniform_load(self):
        result = analyze_beam(
            "Simply supported",
            12,
            [],
            [UniformLoad(0.05, 0, 12)],
            1600,
            98.93,
        )
        section = next(item for item in LUMBER_SECTIONS if item["name"] == "2x10")
        self.assertAlmostEqual(result.max_moment, 0.90, places=2)
        self.assertAlmostEqual(bending_stress(result.max_moment, section["Sx"]), 0.505, places=2)
        self.assertAlmostEqual(abs(result.max_deflection), 0.147, places=2)


if __name__ == "__main__":
    unittest.main()
