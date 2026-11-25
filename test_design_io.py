import json
import tempfile
import unittest
import csv
from pathlib import Path

from beam_core import PointLoad, UniformLoad
from design_io import (
    SCHEMA_NAME,
    SCHEMA_VERSION,
    load_design,
    save_design,
    serialize_design,
    export_results_csv,
)


class DesignIoTests(unittest.TestCase):
    def test_round_trip_restores_all_inputs(self):
        design = serialize_design(
            "Cantilever",
            10.0,
            "Lumber",
            "2x10",
            "L/240",
            [PointLoad(5.0, 10.0)],
            [UniformLoad(0.05, -2.0, 12.0)],
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cantilever.beam.json"
            save_design(path, design)
            restored = load_design(path)

        self.assertEqual(restored["support"], "Cantilever")
        self.assertEqual(restored["span_ft"], 10.0)
        self.assertEqual(restored["material"], "Lumber")
        self.assertEqual(restored["section"], "2x10")
        self.assertEqual(restored["deflection_limit"], "L/240")
        self.assertEqual(
            [(load.magnitude, load.position) for load in restored["point_loads"]],
            [(5.0, 10.0)],
        )
        self.assertEqual(
            [
                (load.magnitude, load.start, load.end)
                for load in restored["uniform_loads"]
            ],
            [(0.05, -2.0, 12.0)],
        )

    def test_save_schema_is_versioned_json(self):
        design = serialize_design(
            "Simply supported",
            20.0,
            "Steel",
            "W12x26",
            "L/360",
            [],
            [UniformLoad(1.0, 0.0, 20.0)],
        )
        self.assertEqual(design["format"], SCHEMA_NAME)
        self.assertEqual(design["version"], SCHEMA_VERSION)
        json.dumps(design)

    def test_invalid_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.beam.json"
            path.write_text(
                json.dumps({"format": "not-beam-designer", "version": 1}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_design(path)

    def test_export_results_csv_headers_and_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            export_results_csv(
                path,
                [0.0, 10.0, 20.0],
                [10.0, 0.0, -10.0],
                [0.0, 50.0, 0.0],
                [0.0, -0.609, 0.0],
            )
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))

        self.assertEqual(
            rows[0],
            [
                "Position x (ft)",
                "Shear V (kips)",
                "Moment M (kip-ft)",
                "Deflection y (inches)",
            ],
        )
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[2], ["10.000000", "0.000000", "50.000000", "-0.609000"])


if __name__ == "__main__":
    unittest.main()
