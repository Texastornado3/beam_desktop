import re
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from beam_core import (
    PointLoad,
    UniformLoad,
    analyze_beam,
    bending_stress,
    deflection_limit,
)
from pdf_export import _draw_calculation_page, export_calculation_pdf


class PdfExportTests(unittest.TestCase):
    def export(self, path, point_loads=None, uniform_loads=None):
        point_loads = point_loads or []
        uniform_loads = uniform_loads or [UniformLoad(1.0, 0.0, 20.0)]
        result = analyze_beam(
            "Simply supported",
            20.0,
            point_loads,
            uniform_loads,
            29000.0,
            204.0,
        )
        stress = bending_stress(result.max_moment, 33.4)
        limit = deflection_limit(20.0, 360)
        export_calculation_pdf(
            path,
            support="Simply supported",
            span_ft=20.0,
            material="Steel",
            section="W12x26",
            section_properties={
                "E": 29000.0,
                "Fb": 30.0,
                "Ix": 204.0,
                "Sx": 33.4,
                "weight": 26.0,
            },
            point_loads=point_loads,
            uniform_loads=uniform_loads,
            result=result,
            bending_stress_ksi=stress,
            bending_allowable_ksi=30.0,
            deflection_allowable_in=limit,
            bending_pass=stress <= 30.0,
            deflection_pass=abs(result.max_deflection) <= limit,
            deflection_denominator=360,
        )

    def test_exports_letter_sized_calculation_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calculation.pdf"
            self.export(path)
            content = path.read_bytes()

        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertRegex(content, rb"/MediaBox\s*\[\s*0\s+0\s+612\s+792\s*\]")
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", content)), 1)

    def test_long_load_list_continues_on_letter_page(self):
        loads = [PointLoad(0.5, 1.0 + index * 1.5) for index in range(10)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "many-loads.pdf"
            self.export(path, point_loads=loads, uniform_loads=[])
            content = path.read_bytes()

        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", content)), 2)
        self.assertGreater(len(content), 5000)

    def test_calculation_sheet_text_stays_inside_page(self):
        result = analyze_beam(
            "Simply supported",
            20.0,
            [],
            [UniformLoad(1.0, 0.0, 20.0)],
            29000.0,
            204.0,
        )
        figure = plt.figure(figsize=(8.5, 11.0))
        _draw_calculation_page(
            figure,
            support="Simply supported",
            span_ft=20.0,
            material="Steel",
            section="W12x26",
            section_properties={
                "E": 29000.0,
                "Fb": 30.0,
                "Ix": 204.0,
                "Sx": 33.4,
                "weight": 26.0,
            },
            point_loads=[],
            uniform_loads=[UniformLoad(1.0, 0.0, 20.0)],
            result=result,
            bending_stress_ksi=bending_stress(result.max_moment, 33.4),
            bending_allowable_ksi=30.0,
            deflection_allowable_in=deflection_limit(20.0, 360),
            bending_pass=True,
            deflection_pass=True,
            deflection_denominator=360,
        )
        canvas = FigureCanvasAgg(figure)
        canvas.draw()
        renderer = canvas.get_renderer()
        page = figure.bbox
        for label in figure.texts:
            bounds = label.get_window_extent(renderer)
            self.assertGreaterEqual(bounds.x0, page.x0, label.get_text())
            self.assertGreaterEqual(bounds.y0, page.y0, label.get_text())
            self.assertLessEqual(bounds.x1, page.x1, label.get_text())
            self.assertLessEqual(bounds.y1, page.y1, label.get_text())
        plt.close(figure)


if __name__ == "__main__":
    unittest.main()
