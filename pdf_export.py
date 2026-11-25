from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon, Rectangle

from beam_core import BeamResult, PointLoad, UniformLoad


PAGE_WIDTH_IN = 8.5
PAGE_HEIGHT_IN = 11.0
INK = "#263746"
MUTED = "#586b7a"
ACCENT = "#2474a6"
PASS_COLOR = "#26734d"
FAIL_COLOR = "#b42318"
RULE = "#d5dee5"


def export_calculation_pdf(
    path: str | Path,
    *,
    support: str,
    span_ft: float,
    material: str,
    section: str,
    section_properties: dict,
    point_loads: Sequence[PointLoad],
    uniform_loads: Sequence[UniformLoad],
    result: BeamResult,
    bending_stress_ksi: float,
    bending_allowable_ksi: float,
    deflection_allowable_in: float,
    bending_pass: bool,
    deflection_pass: bool,
    deflection_denominator: int,
) -> None:
    """Write a letter-sized calculation sheet and load continuation pages."""
    destination = Path(path)
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": RULE,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    ):
        with PdfPages(destination) as pdf:
            all_load_rows = _load_rows(point_loads, uniform_loads, span_ft)
            figure = plt.figure(figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white")
            _draw_calculation_page(
                figure,
                support=support,
                span_ft=span_ft,
                material=material,
                section=section,
                section_properties=section_properties,
                point_loads=point_loads,
                uniform_loads=uniform_loads,
                result=result,
                bending_stress_ksi=bending_stress_ksi,
                bending_allowable_ksi=bending_allowable_ksi,
                deflection_allowable_in=deflection_allowable_in,
                bending_pass=bending_pass,
                deflection_pass=deflection_pass,
                deflection_denominator=deflection_denominator,
                first_load_rows=all_load_rows[:8],
                load_count=len(all_load_rows),
            )
            pdf.savefig(figure, facecolor="white")
            plt.close(figure)

            remainder = all_load_rows[8:]
            for page_number, start in enumerate(range(0, len(remainder), 28), start=1):
                page_rows = remainder[start : start + 28]
                appendix = plt.figure(
                    figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
                )
                _draw_load_appendix(appendix, page_rows, page_number)
                pdf.savefig(appendix, facecolor="white")
                plt.close(appendix)


def _draw_calculation_page(
    figure,
    *,
    support: str,
    span_ft: float,
    material: str,
    section: str,
    section_properties: dict,
    point_loads: Sequence[PointLoad],
    uniform_loads: Sequence[UniformLoad],
    result: BeamResult,
    bending_stress_ksi: float,
    bending_allowable_ksi: float,
    deflection_allowable_in: float,
    bending_pass: bool,
    deflection_pass: bool,
    deflection_denominator: int,
    first_load_rows=None,
    load_count=None,
) -> None:
    loads = _load_rows(point_loads, uniform_loads, span_ft)
    if first_load_rows is None:
        first_load_rows = loads[:8]
    if load_count is None:
        load_count = len(loads)
    figure.clear()
    figure.text(0.065, 0.958, "BEAM DESIGNER", fontsize=9, weight="bold", color=ACCENT)
    figure.text(0.065, 0.925, "Calculation Sheet", fontsize=21, weight="bold", color=INK)
    figure.text(
        0.935,
        0.936,
        "STRUCTURAL ANALYSIS",
        fontsize=8,
        weight="bold",
        color=MUTED,
        ha="right",
    )
    figure.add_artist(
        Rectangle(
            (0.065, 0.908),
            0.87,
            0.0025,
            transform=figure.transFigure,
            color=ACCENT,
            linewidth=0,
        )
    )

    E = section_properties["E"]
    Fb = section_properties["Fb"]
    Ix = section_properties["Ix"]
    Sx = section_properties["Sx"]
    weight = section_properties.get("weight")
    weight_text = f"  |  Wt {weight:g} lb/ft" if weight is not None else ""

    _panel(figure, 0.065, 0.826, 0.414, 0.067)
    _panel(figure, 0.493, 0.826, 0.442, 0.067)
    figure.text(0.08, 0.877, "BEAM AND SECTION", fontsize=7, weight="bold", color=MUTED)
    figure.text(
        0.08,
        0.855,
        f"{support}  |  Span: {span_ft:g} ft  |  {material}: {section}",
        fontsize=8.1,
        weight="bold",
    )
    figure.text(
        0.08,
        0.835,
        f"E = {E:g} ksi  |  Ix = {Ix:g} in^4  |  Sx = {Sx:g} in^3{weight_text}",
        fontsize=6.4,
        color=MUTED,
    )

    reaction_text = (
        f"Reactions: Left = {result.left_reaction:.3f} k  |  "
        f"Right = {result.right_reaction:.3f} k"
        if support == "Simply supported"
        else f"Reaction: Left = {result.left_reaction:.3f} k  |  "
        f"Fixed-end moment = {result.fixed_moment:.3f} kip-ft"
    )
    figure.text(0.508, 0.877, "ANALYSIS SUMMARY", fontsize=7, weight="bold", color=MUTED)
    figure.text(0.508, 0.856, reaction_text, fontsize=7.5, weight="bold")
    figure.text(
        0.508,
        0.837,
        f"Vmax = {abs(result.max_shear):.3f} k  |  "
        f"Mmax = {result.max_moment:.3f} kip-ft  |  "
        f"|y|max = {abs(result.max_deflection):.3f} in",
        fontsize=7.1,
        color=MUTED,
    )

    figure.text(0.065, 0.805, "APPLIED LOADS", fontsize=7, weight="bold", color=MUTED)
    if len(loads) > 8:
        figure.text(
            0.935,
            0.805,
            f"{len(loads) - 8} additional loads on continuation page(s)",
            fontsize=6.8,
            color=MUTED,
            ha="right",
        )
    if not loads:
        figure.text(0.065, 0.783, "No applied loads.", fontsize=7.5, color=MUTED)
    else:
        visible_loads = list(first_load_rows)
        half = (len(visible_loads) + 1) // 2
        columns = [visible_loads[:half], visible_loads[half:]]
        for column_index, column in enumerate(columns):
            x = 0.065 + column_index * 0.44
            for row_index, (kind, description) in enumerate(column):
                y = 0.784 - row_index * 0.018
                figure.text(x, y, kind, fontsize=6.8, weight="bold", color=INK)
                figure.text(x + 0.095, y, description, fontsize=6.8, color=MUTED)

    beam_ax = figure.add_axes([0.105, 0.653, 0.82, 0.095])
    _draw_beam(beam_ax, support, span_ft, point_loads, uniform_loads, result)

    plot_axes = [
        figure.add_axes([0.14, 0.531, 0.78, 0.083]),
        figure.add_axes([0.14, 0.428, 0.78, 0.083]),
        figure.add_axes([0.14, 0.325, 0.78, 0.083]),
    ]
    _draw_result_plot(
        plot_axes[0], result.x_ft, result.shear, "Shear V (kips)", result.max_shear,
        result.max_shear_x, span_ft, show_x=False,
    )
    _draw_result_plot(
        plot_axes[1], result.x_ft, result.moment, "Moment M (kip-ft)", result.max_moment,
        result.max_moment_x, span_ft, show_x=False,
    )
    _draw_result_plot(
        plot_axes[2], result.x_ft, result.deflection, "Deflection y (in)", result.max_deflection,
        result.max_deflection_x, span_ft, show_x=True,
    )
    plot_axes[-1].set_xlabel("Position x (ft)", fontsize=7, labelpad=1)

    _panel(figure, 0.065, 0.198, 0.87, 0.102)
    bend_color = PASS_COLOR if bending_pass else FAIL_COLOR
    deflection_color = PASS_COLOR if deflection_pass else FAIL_COLOR
    figure.text(0.08, 0.279, "STRENGTH AND SERVICEABILITY CHECKS", fontsize=7, weight="bold", color=MUTED)
    figure.text(
        0.08,
        0.256,
        f"Bending: fb = {bending_stress_ksi:.3f} ksi / Fb = {bending_allowable_ksi:.3f} ksi",
        fontsize=7.5,
        color=INK,
    )
    figure.text(
        0.455,
        0.256,
        "PASS" if bending_pass else "FAIL",
        fontsize=8,
        weight="bold",
        color=bend_color,
    )
    figure.text(
        0.08,
        0.233,
        f"Deflection: |y|max = {abs(result.max_deflection):.3f} in / "
        f"L/{deflection_denominator} = {deflection_allowable_in:.3f} in",
        fontsize=7.5,
        color=INK,
    )
    figure.text(
        0.455,
        0.233,
        "PASS" if deflection_pass else "FAIL",
        fontsize=8,
        weight="bold",
        color=deflection_color,
    )
    figure.text(
        0.08,
        0.211,
        f"Allowables: Fb = {Fb:g} ksi  |  Deflection = L/{deflection_denominator} "
        f"({deflection_allowable_in:.3f} in)",
        fontsize=6.9,
        color=MUTED,
    )

    _panel(figure, 0.065, 0.075, 0.87, 0.108)
    figure.text(0.08, 0.163, "CALCULATION FORMULAS", fontsize=7, weight="bold", color=MUTED)
    formulas = (
        "Reactions: static equilibrium.  V(x) = R_left - sum(P_i for a_i <= x) "
        "- sum(q_i * loaded length to x).  M(x) = M(0) + integral[0,x] V(s) ds."
    )
    deflection_formula = (
        "Deflection: y''(x) = -M(x)/[E Ix] (consistent units); integrate twice using "
        "support boundary conditions."
    )
    checks = (
        "Checks: fb = 12 |Mmax|/Sx <= Fb;  |y|max <= L/"
        f"{deflection_denominator} (L in inches).  Simply supported: y(0)=y(L)=0; "
        "cantilever: y(0)=y'(0)=0."
    )
    figure.text(0.08, 0.143, formulas, fontsize=6.7, color=INK)
    figure.text(0.08, 0.123, deflection_formula, fontsize=6.7, color=INK)
    figure.text(0.08, 0.103, checks, fontsize=6.7, color=INK)
    figure.text(
        0.5,
        0.045,
        "Beam Designer  |  Engineering calculations are based on the displayed inputs",
        fontsize=6.5,
        color=MUTED,
        ha="center",
    )


def _draw_beam(axis, support, span_ft, point_loads, uniform_loads, result) -> None:
    axis.set_xlim(-0.9, span_ft + 0.9)
    axis.set_ylim(-1.35, 1.55)
    axis.axis("off")
    axis.plot([0, span_ft], [0, 0], color=INK, linewidth=4, solid_capstyle="round")
    if support == "Simply supported":
        axis.add_patch(Polygon([(-0.38, -0.07), (0.38, -0.07), (0, -0.55)], closed=True,
                               facecolor="#e8eef2", edgecolor=INK, linewidth=0.8))
        axis.add_patch(Polygon([(span_ft - 0.38, -0.07), (span_ft + 0.38, -0.07),
                               (span_ft, -0.55)], closed=True,
                               facecolor="#e8eef2", edgecolor=INK, linewidth=0.8))
    else:
        axis.add_patch(Rectangle((-0.65, -0.5), 0.35, 1.0, facecolor="#e8eef2",
                                edgecolor=INK, linewidth=0.8))
        for y in np.linspace(-0.42, 0.42, 5):
            axis.plot([-0.65, -0.84], [y, y - 0.14], color=INK, linewidth=0.7)

    for load in point_loads:
        x = min(max(load.position, 0.0), span_ft)
        axis.annotate("", xy=(x, 0.05), xytext=(x, 0.92),
                      arrowprops={"arrowstyle": "-|>", "color": ACCENT, "lw": 1.2})

    for load in uniform_loads:
        start = min(max(load.start, 0.0), span_ft)
        end = min(max(load.end, 0.0), span_ft)
        if end < start:
            start, end = end, start
        if end <= start:
            continue
        positions = np.linspace(start, end, max(3, min(30, int((end - start) * 2))))
        axis.plot([start, end], [0.48, 0.48], color=ACCENT, linewidth=0.9)
        for x in positions:
            axis.annotate("", xy=(x, 0.48), xytext=(x, 0.88),
                          arrowprops={"arrowstyle": "-|>", "color": ACCENT, "lw": 0.7})

    reactions = (
        [(0.0, result.left_reaction, f"{result.left_reaction:.2f} k"),
         (span_ft, result.right_reaction, f"{result.right_reaction:.2f} k")]
        if support == "Simply supported"
        else [(0.0, result.left_reaction, f"{result.left_reaction:.2f} k")]
    )
    for x, reaction, label in reactions:
        axis.annotate("", xy=(x, -0.02), xytext=(x, -0.65),
                      arrowprops={"arrowstyle": "-|>", "color": PASS_COLOR, "lw": 1.2})
        axis.text(x, -0.83, label, ha="center", va="top", fontsize=6.5, color=PASS_COLOR)
    if support == "Cantilever":
        axis.text(0.3, -1.08, f"Fixed-end moment: {result.fixed_moment:.2f} kip-ft",
                  ha="left", fontsize=6.5, color=INK)
    axis.text(span_ft / 2, -0.58, f"Span = {span_ft:g} ft",
              ha="center", va="top", fontsize=6.5, color=MUTED)


def _draw_result_plot(axis, x, values, label, max_value, max_x, span_ft, show_x) -> None:
    axis.axhline(0, color=RULE, linewidth=0.7)
    axis.plot(x, values, color=ACCENT, linewidth=1.15)
    axis.fill_between(x, 0, values, color="#dcecf5", alpha=0.9, linewidth=0)
    axis.set_xlim(0, span_ft)
    axis.set_ylabel(label, fontsize=6.8, labelpad=4)
    axis.tick_params(axis="both", labelsize=6, length=2, pad=1)
    axis.grid(axis="x", color=RULE, linewidth=0.45, alpha=0.8)
    axis.spines[["top", "right"]].set_visible(False)
    if not show_x:
        axis.tick_params(axis="x", labelbottom=False)
    if len(x):
        y = float(np.interp(max_x, x, values))
        axis.annotate(
            f"{max_value:.3g}",
            (max_x, y),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=6.2,
            color=INK,
        )
    axis.margins(y=0.22)


def _load_rows(point_loads, uniform_loads, span_ft):
    rows = []
    for index, load in enumerate(point_loads, start=1):
        position = min(max(load.position, 0.0), span_ft)
        rows.append((f"Point {index}", f"{load.magnitude:g} k at x = {position:g} ft"))
    for index, load in enumerate(uniform_loads, start=1):
        start = min(max(load.start, 0.0), span_ft)
        end = min(max(load.end, 0.0), span_ft)
        if end < start:
            start, end = end, start
        rows.append(
            (f"Uniform {index}", f"{load.magnitude:g} k/ft from {start:g} to {end:g} ft")
        )
    return rows


def _draw_load_appendix(figure, loads, page_number):
    figure.text(0.065, 0.958, "BEAM DESIGNER", fontsize=9, weight="bold", color=ACCENT)
    figure.text(0.065, 0.925, "Applied Loads — Continuation", fontsize=19, weight="bold", color=INK)
    figure.text(0.935, 0.936, f"LOADS  |  PAGE {page_number + 1}", fontsize=8,
                weight="bold", color=MUTED, ha="right")
    figure.add_artist(Rectangle((0.065, 0.908), 0.87, 0.0025,
                                transform=figure.transFigure, color=ACCENT, linewidth=0))
    for index, (kind, description) in enumerate(loads):
        column, row = divmod(index, 14)
        x = 0.08 + column * 0.44
        y = 0.875 - row * 0.052
        _panel(figure, x - 0.01, y - 0.013, 0.405, 0.039, facecolor="#fbfcfd")
        figure.text(x, y, kind, fontsize=8, weight="bold", color=INK)
        figure.text(x + 0.105, y, description, fontsize=7.5, color=MUTED)
    figure.text(0.5, 0.045, "Beam Designer  |  Applied loads continued",
                fontsize=6.5, color=MUTED, ha="center")


def _panel(figure, x, y, width, height, facecolor="#f7f9fb"):
    figure.add_artist(
        Rectangle(
            (x, y),
            width,
            height,
            transform=figure.transFigure,
            facecolor=facecolor,
            edgecolor=RULE,
            linewidth=0.6,
            zorder=-1,
        )
    )
