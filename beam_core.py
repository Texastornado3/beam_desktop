from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np


SupportType = Literal["Simply supported", "Cantilever"]


STEEL_SECTIONS = [
    {"name": "W8x10", "Ix": 30.8, "Sx": 7.81, "weight": 10.0},
    {"name": "W10x12", "Ix": 53.8, "Sx": 10.9, "weight": 12.0},
    {"name": "W12x26", "Ix": 204.0, "Sx": 33.4, "weight": 26.0},
    {"name": "W14x22", "Ix": 199.0, "Sx": 29.0, "weight": 22.0},
    {"name": "W16x26", "Ix": 301.0, "Sx": 38.4, "weight": 26.0},
    {"name": "W18x35", "Ix": 510.0, "Sx": 57.6, "weight": 35.0},
    {"name": "W21x44", "Ix": 843.0, "Sx": 81.6, "weight": 44.0},
    {"name": "W24x55", "Ix": 1350.0, "Sx": 114.0, "weight": 55.0},
]

LUMBER_SECTIONS = [
    {"name": "2x8", "Ix": 47.63, "Sx": 13.14},
    {"name": "2x10", "Ix": 98.93, "Sx": 21.39},
    {"name": "2x12", "Ix": 177.98, "Sx": 31.64},
]


@dataclass(frozen=True)
class PointLoad:
    magnitude: float
    position: float


@dataclass(frozen=True)
class UniformLoad:
    magnitude: float
    start: float
    end: float


@dataclass(frozen=True)
class BeamResult:
    x_ft: np.ndarray
    shear: np.ndarray
    moment: np.ndarray
    deflection: np.ndarray
    left_reaction: float
    right_reaction: float
    fixed_moment: float
    max_shear: float
    max_shear_x: float
    max_moment: float
    max_moment_x: float
    max_deflection: float
    max_deflection_x: float


def cumulative_trapezoid(values: np.ndarray, dx: float) -> np.ndarray:
    result = np.zeros_like(values)
    result[1:] = np.cumsum((values[:-1] + values[1:]) * 0.5 * dx)
    return result


def clipped_uniform_load(load: UniformLoad, span: float) -> UniformLoad:
    start = min(max(load.start, 0.0), span)
    end = min(max(load.end, 0.0), span)
    if end < start:
        start, end = end, start
    return UniformLoad(load.magnitude, start, end)


def reaction_and_internal_values(
    support: SupportType,
    span: float,
    point_loads: Iterable[PointLoad],
    uniform_loads: Iterable[UniformLoad],
) -> tuple[float, float, float]:
    points = list(point_loads)
    uniforms = [clipped_uniform_load(load, span) for load in uniform_loads]

    if support == "Cantilever":
        left_reaction = sum(load.magnitude for load in points)
        left_reaction += sum(
            load.magnitude * (load.end - load.start) for load in uniforms
        )
        fixed_moment = sum(
            load.magnitude * min(max(load.position, 0.0), span)
            for load in points
        )
        for load in uniforms:
            length = load.end - load.start
            centroid = (load.start + load.end) / 2.0
            fixed_moment += load.magnitude * length * centroid
        return left_reaction, 0.0, fixed_moment

    left_reaction = 0.0
    right_reaction = 0.0
    for load in points:
        position = min(max(load.position, 0.0), span)
        left_reaction += load.magnitude * (span - position) / span
        right_reaction += load.magnitude * position / span
    for load in uniforms:
        length = load.end - load.start
        centroid = (load.start + load.end) / 2.0
        total = load.magnitude * length
        left_reaction += total * (span - centroid) / span
        right_reaction += total * centroid / span
    return left_reaction, right_reaction, 0.0


def analyze_beam(
    support: SupportType,
    span: float,
    point_loads: Iterable[PointLoad],
    uniform_loads: Iterable[UniformLoad],
    E_ksi: float,
    Ix_in4: float,
) -> BeamResult:
    if not 4.0 <= span <= 40.0:
        raise ValueError("Span must be between 4 and 40 ft.")

    points = [
        PointLoad(load.magnitude, min(max(load.position, 0.0), span))
        for load in point_loads
    ]
    uniforms = [clipped_uniform_load(load, span) for load in uniform_loads]
    left_reaction, right_reaction, fixed_moment = reaction_and_internal_values(
        support, span, points, uniforms
    )

    breakpoints = {0.0, span}
    for load in points:
        breakpoints.add(load.position)
    for load in uniforms:
        breakpoints.add(load.start)
        breakpoints.add(load.end)

    base = np.arange(0.0, span + 0.01, 0.02)
    x_ft = np.unique(np.concatenate([base, np.array(sorted(breakpoints))]))

    shear = np.zeros_like(x_ft)
    moment = np.zeros_like(x_ft)
    if support == "Simply supported":
        shear[:] = left_reaction
    else:
        shear[:] = left_reaction

    for i, x in enumerate(x_ft):
        v = left_reaction
        if support == "Simply supported":
            m = left_reaction * x
            for load in points:
                if x >= load.position:
                    v -= load.magnitude
                    m -= load.magnitude * (x - load.position)
            for load in uniforms:
                length = load.end - load.start
                if x >= load.end:
                    v -= load.magnitude * length
                    m -= load.magnitude * length * (x - (load.start + load.end) / 2.0)
                elif x >= load.start:
                    distance = x - load.start
                    v -= load.magnitude * distance
                    m -= load.magnitude * distance * distance / 2.0
        else:
            m = 0.0
            for load in points:
                if x <= load.position:
                    v += 0.0
                    m += load.magnitude * (load.position - x)
                    if x >= load.position:
                        v -= load.magnitude
            for load in uniforms:
                if x < load.start:
                    m += 0.5 * load.magnitude * (
                        (load.end - x) ** 2 - (load.start - x) ** 2
                    )
                elif x < load.end:
                    m += 0.5 * load.magnitude * (load.end - x) ** 2

            v = left_reaction
            for load in points:
                if x >= load.position:
                    v -= load.magnitude
            for load in uniforms:
                if x >= load.end:
                    v -= load.magnitude * (load.end - load.start)
                elif x >= load.start:
                    v -= load.magnitude * (x - load.start)
        shear[i] = v
        moment[i] = m

    x_in = x_ft * 12.0
    dx_in = x_in[1:] - x_in[:-1]
    dx_in = np.append(dx_in, dx_in[-1] if len(dx_in) else 12.0)
    curvature = np.zeros_like(x_ft)
    for i in range(len(x_ft)):
        curvature[i] = -moment[i] * 12.0 / (E_ksi * Ix_in4)

    slope = cumulative_trapezoid(curvature, dx_in if False else 12.0)
    if support == "Simply supported":
        slope_constant = -cumulative_trapezoid(
            curvature, 12.0
        )[-1] if False else 0.0

    if support == "Simply supported":
        irregular_dx = np.diff(x_in)
        theta = np.zeros_like(x_in)
        theta[1:] = np.cumsum(
            (curvature[:-1] + curvature[1:]) * 0.5 * irregular_dx
        )
        theta0 = 0.0
        deflection_curve = np.zeros_like(x_in)
        deflection_curve[1:] = np.cumsum(
            (theta[:-1] + theta[1:] + 2.0 * theta0) * 0.5 * irregular_dx
        )
        theta0 = -deflection_curve[-1] / x_in[-1]
        theta = theta + theta0
        deflection_curve = np.zeros_like(x_in)
        deflection_curve[1:] = np.cumsum(
            (theta[:-1] + theta[1:]) * 0.5 * irregular_dx
        )
    else:
        irregular_dx = np.diff(x_in)
        theta = np.zeros_like(x_in)
        theta[1:] = np.cumsum(
            (curvature[:-1] + curvature[1:]) * 0.5 * irregular_dx
        )
        deflection_curve = np.zeros_like(x_in)
        deflection_curve[1:] = np.cumsum(
            (theta[:-1] + theta[1:]) * 0.5 * irregular_dx
        )

    max_shear_index = int(np.argmax(np.abs(shear)))
    max_moment_index = int(np.argmax(np.abs(moment)))
    max_deflection_index = int(np.argmax(np.abs(deflection_curve)))

    return BeamResult(
        x_ft=x_ft,
        shear=shear,
        moment=moment,
        deflection=deflection_curve,
        left_reaction=left_reaction,
        right_reaction=right_reaction,
        fixed_moment=fixed_moment,
        max_shear=float(shear[max_shear_index]),
        max_shear_x=float(x_ft[max_shear_index]),
        max_moment=float(abs(moment[max_moment_index]) if moment[max_moment_index] != 0 else 0.0),
        max_moment_x=float(x_ft[max_moment_index]),
        max_deflection=float(deflection_curve[max_deflection_index]),
        max_deflection_x=float(x_ft[max_deflection_index]),
    )


def bending_stress(moment_kip_ft: float, section_modulus_in3: float) -> float:
    return abs(moment_kip_ft) * 12.0 / section_modulus_in3


def deflection_limit(span_ft: float, denominator: int) -> float:
    return span_ft * 12.0 / denominator


def lightest_passing_section(
    material: str,
    support: SupportType,
    span: float,
    point_loads: Iterable[PointLoad],
    uniform_loads: Iterable[UniformLoad],
    deflection_denominator: int,
) -> dict | None:
    E_ksi = 29000.0 if material == "Steel" else 1600.0
    allowable_bending = 30.0 if material == "Steel" else 0.900
    sections = STEEL_SECTIONS if material == "Steel" else LUMBER_SECTIONS
    limit = deflection_limit(span, deflection_denominator)
    passing = []

    for section in sections:
        result = analyze_beam(
            support, span, point_loads, uniform_loads, E_ksi, section["Ix"]
        )
        stress = bending_stress(result.max_moment, section["Sx"])
        if stress <= allowable_bending and abs(result.max_deflection) <= limit:
            passing.append(section)

    if not passing:
        return None
    if material == "Steel":
        return sorted(passing, key=lambda section: (section["weight"], -section["Ix"]))[0]
    return passing[0]
