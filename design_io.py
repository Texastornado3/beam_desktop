import json
import math
from pathlib import Path
from typing import Any

from beam_core import (
    LUMBER_SECTIONS,
    STEEL_SECTIONS,
    PointLoad,
    UniformLoad,
)


SCHEMA_NAME = "beam-designer"
SCHEMA_VERSION = 1


def serialize_design(
    support: str,
    span: float,
    material: str,
    section: str,
    deflection_limit: str,
    point_loads: list[PointLoad],
    uniform_loads: list[UniformLoad],
) -> dict[str, Any]:
    validate_design_values(
        support,
        span,
        material,
        section,
        deflection_limit,
        point_loads,
        uniform_loads,
    )
    return {
        "format": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "support": support,
        "span_ft": span,
        "material": material,
        "section": section,
        "deflection_limit": deflection_limit,
        "point_loads": [
            {"magnitude": load.magnitude, "position": load.position}
            for load in point_loads
        ],
        "uniform_loads": [
            {"magnitude": load.magnitude, "start": load.start, "end": load.end}
            for load in uniform_loads
        ],
    }


def validate_design_values(
    support: str,
    span: float,
    material: str,
    section: str,
    deflection_limit: str,
    point_loads: list[PointLoad],
    uniform_loads: list[UniformLoad],
) -> None:
    if support not in ("Simply supported", "Cantilever"):
        raise ValueError("Invalid support type.")
    if not 4.0 <= span <= 40.0:
        raise ValueError("Span must be between 4 and 40 ft.")
    if material not in ("Steel", "Lumber"):
        raise ValueError("Invalid material.")
    sections = STEEL_SECTIONS if material == "Steel" else LUMBER_SECTIONS
    if section not in {item["name"] for item in sections}:
        raise ValueError("Section is not valid for the selected material.")
    if deflection_limit not in ("L/240", "L/360"):
        raise ValueError("Invalid deflection limit.")
    for load in point_loads:
        if not math.isfinite(load.magnitude) or not math.isfinite(load.position):
            raise ValueError("Point-load values must be finite.")
        if not 0.0 <= load.position <= span:
            raise ValueError("Point-load position is outside the beam.")
    for load in uniform_loads:
        if not all(
            math.isfinite(value)
            for value in (load.magnitude, load.start, load.end)
        ):
            raise ValueError("Uniform-load values must be finite.")
        if load.end < load.start:
            raise ValueError("Uniform-load end must not precede its start.")


def save_design(path: str | Path, design: dict[str, Any]) -> None:
    destination = Path(path)
    with destination.open("w", encoding="utf-8") as file:
        json.dump(design, file, indent=2)
        file.write("\n")


def load_design(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as file:
        design = json.load(file)
    if not isinstance(design, dict):
        raise ValueError("The JSON file must contain a design object.")
    if design.get("format") != SCHEMA_NAME:
        raise ValueError("This is not a Beam Designer JSON file.")
    if design.get("version") != SCHEMA_VERSION:
        raise ValueError("Unsupported Beam Designer file version.")

    try:
        point_loads = [
            PointLoad(float(load["magnitude"]), float(load["position"]))
            for load in design["point_loads"]
        ]
        uniform_loads = [
            UniformLoad(
                float(load["magnitude"]),
                float(load["start"]),
                float(load["end"]),
            )
            for load in design["uniform_loads"]
        ]
        support = str(design["support"])
        span = float(design["span_ft"])
        material = str(design["material"])
        section = str(design["section"])
        deflection_limit = str(design["deflection_limit"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The saved design contains missing or invalid values.") from error

    validate_design_values(
        support,
        span,
        material,
        section,
        deflection_limit,
        point_loads,
        uniform_loads,
    )
    return {
        "support": support,
        "span_ft": span,
        "material": material,
        "section": section,
        "deflection_limit": deflection_limit,
        "point_loads": point_loads,
        "uniform_loads": uniform_loads,
    }
