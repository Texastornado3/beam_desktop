import tkinter as tk
import json
from tkinter import ttk, messagebox, filedialog

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Polygon
from matplotlib import patheffects

from beam_core import (
    STEEL_SECTIONS,
    LUMBER_SECTIONS,
    PointLoad,
    UniformLoad,
    analyze_beam,
    bending_stress,
    deflection_limit,
    lightest_passing_section,
)
from design_io import load_design, save_design, serialize_design


ACCENT = "#2474a6"
GREEN = "#2e7d32"
AMBER = "#f0a202"
RED = "#c62828"


class BeamDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Beam Designer")
        self.root.geometry("1250x800")
        self.root.minsize(900, 650)

        self.support = tk.StringVar(value="Simply supported")
        self.span = tk.DoubleVar(value=20.0)
        self.material = tk.StringVar(value="Steel")
        self.section = tk.StringVar(value="W12x26")
        self.deflection_option = tk.StringVar(value="L/360")
        self.point_loads: list[PointLoad] = []
        self.uniform_loads: list[UniformLoad] = [UniformLoad(1.0, 0.0, 20.0)]

        self._building_controls = False
        self._span_update_job = None
        self._drag_index = None

        self._create_layout()
        self.root.after_idle(self.refresh)

    def _create_layout(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_design)
        file_menu.add_command(label="Open", accelerator="Ctrl+O", command=self.open_design)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)
        self.root.bind("<Control-s>", lambda event: self.save_design())
        self.root.bind("<Control-o>", lambda event: self.open_design())

        outer = ttk.Frame(self.root)
        outer.pack(fill=tk.BOTH, expand=True)

        controls_container = ttk.Frame(outer, width=330)
        controls_container.pack(side=tk.LEFT, fill=tk.Y)
        controls_container.pack_propagate(False)

        canvas_scroll = tk.Canvas(controls_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(controls_container, orient=tk.VERTICAL, command=canvas_scroll.yview)
        self.controls = ttk.Frame(canvas_scroll)
        self.controls.bind(
            "<Configure>",
            lambda event: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")),
        )
        canvas_scroll.create_window((0, 0), window=self.controls, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results = ttk.Frame(outer)
        self.results.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._create_controls()
        self._create_results()

    def _create_controls(self) -> None:
        support_frame = ttk.LabelFrame(self.controls, text="Beam")
        support_frame.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(support_frame, text="Support").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Radiobutton(
            support_frame,
            text="Simply supported",
            variable=self.support,
            value="Simply supported",
            command=self.refresh,
        ).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Radiobutton(
            support_frame,
            text="Cantilever",
            variable=self.support,
            value="Cantilever",
            command=self.refresh,
        ).grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(support_frame, text="Span (ft)").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self.span_scale = ttk.Scale(
            support_frame,
            from_=4,
            to=40,
            orient=tk.HORIZONTAL,
            variable=self.span,
            command=self._on_scale,
        )
        self.span_scale.grid(row=2, column=1, sticky="ew", padx=6)
        self.span_entry = ttk.Entry(support_frame, width=8)
        self.span_entry.insert(0, "20")
        self.span_entry.grid(row=2, column=2, padx=6)
        self.span_entry.bind("<KeyRelease>", self._on_span_entry)
        support_frame.columnconfigure(1, weight=1)

        section_frame = ttk.LabelFrame(self.controls, text="Material and Section")
        section_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(section_frame, text="Material").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        material_combo = ttk.Combobox(
            section_frame,
            textvariable=self.material,
            values=["Steel", "Lumber"],
            state="readonly",
        )
        material_combo.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6)
        material_combo.bind("<<ComboboxSelected>>", self._on_material)

        ttk.Label(section_frame, text="Section").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.section_combo = ttk.Combobox(section_frame, textvariable=self.section, state="readonly")
        self.section_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=6)
        self.section_combo.bind("<<ComboboxSelected>>", lambda event: self.refresh())
        section_frame.columnconfigure(1, weight=1)

        limit_frame = ttk.LabelFrame(self.controls, text="Deflection Limit")
        limit_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Radiobutton(
            limit_frame,
            text="L/240",
            variable=self.deflection_option,
            value="L/240",
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Radiobutton(
            limit_frame,
            text="L/360",
            variable=self.deflection_option,
            value="L/360",
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=8, pady=8)

        loads_frame = ttk.LabelFrame(self.controls, text="Loads")
        loads_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        button_row = ttk.Frame(loads_frame)
        button_row.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(button_row, text="Add point load", command=self._add_point_dialog).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(button_row, text="Add uniform load", command=self._add_uniform_dialog).pack(
            side=tk.LEFT
        )
        self.loads_container = ttk.Frame(loads_frame)
        self.loads_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self._populate_sections()
        self._rebuild_load_editor()

    def _create_results(self) -> None:
        toolbar_frame = ttk.Frame(self.results)
        toolbar_frame.pack(fill=tk.X)

        self.figure = plt.figure(figsize=(9.5, 7.2), dpi=100)
        self.figure.subplots_adjust(left=0.09, right=0.98, top=0.97, bottom=0.06, hspace=0.38)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.results)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        status_frame = ttk.Frame(self.results)
        status_frame.pack(fill=tk.X, padx=8, pady=4)
        self.cursor_status = ttk.Label(status_frame, text="")
        self.cursor_status.pack(side=tk.LEFT)

        cards_frame = ttk.Frame(self.results)
        cards_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.bending_card = ttk.LabelFrame(cards_frame, text="Bending")
        self.bending_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.deflection_card = ttk.LabelFrame(cards_frame, text="Deflection")
        self.deflection_card.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        suggestion_frame = ttk.Frame(self.results)
        suggestion_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.suggestion_label = ttk.Label(suggestion_frame, text="")
        self.suggestion_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.use_section_button = ttk.Button(
            suggestion_frame, text="Use section", command=self._use_suggested_section
        )
        self.use_section_button.pack(side=tk.RIGHT)
        self.use_section_button.pack_forget()
        self._suggested_section = None

        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self._on_drag_press)
        self.canvas.mpl_connect("button_release_event", self._on_drag_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_drag_motion)

    def _on_scale(self, value: str) -> None:
        span = round(float(value), 2)
        self.span.set(span)
        if self._span_update_job:
            self.root.after_cancel(self._span_update_job)
        self._span_update_job = self.root.after(80, self._commit_span_entry)
        self.refresh()

    def _commit_span_entry(self) -> None:
        self._building_controls = True
        self.span_entry.delete(0, tk.END)
        self.span_entry.insert(0, f"{self.span.get():g}")
        self._building_controls = False

    def _on_span_entry(self, event=None) -> None:
        if self._building_controls:
            return
        try:
            value = float(self.span_entry.get())
        except ValueError:
            return
        if 4.0 <= value <= 40.0:
            self.span.set(value)
            self.refresh()

    def _on_material(self, event=None) -> None:
        self._populate_sections()
        self.refresh()

    def _populate_sections(self) -> None:
        if self.material.get() == "Steel":
            names = [section["name"] for section in STEEL_SECTIONS]
            if self.section.get() not in names:
                self.section.set("W12x26")
        else:
            names = [section["name"] for section in LUMBER_SECTIONS]
            if self.section.get() not in names:
                self.section.set("2x10")
        self.section_combo.configure(values=names)

    def save_design(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Beam Design",
            defaultextension=".beam.json",
            filetypes=[
                ("Beam Designer JSON", "*.beam.json"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            design = serialize_design(
                self.support.get(),
                self.span.get(),
                self.material.get(),
                self.section.get(),
                self.deflection_option.get(),
                self.point_loads,
                self.uniform_loads,
            )
            save_design(path, design)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Save failed",
                f"The beam design could not be saved:\n{error}",
                parent=self.root,
            )

    def open_design(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open Beam Design",
            filetypes=[
                ("Beam Designer JSON", "*.beam.json"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            design = load_design(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror(
                "Open failed",
                f"The beam design could not be opened:\n{error}",
                parent=self.root,
            )
            return

        self.support.set(design["support"])
        self.span.set(design["span_ft"])
        self.material.set(design["material"])
        self.section.set(design["section"])
        self.deflection_option.set(design["deflection_limit"])
        self.point_loads = list(design["point_loads"])
        self.uniform_loads = list(design["uniform_loads"])

        self._populate_sections()
        self._building_controls = True
        self.span_entry.delete(0, tk.END)
        self.span_entry.insert(0, f"{self.span.get():g}")
        self._building_controls = False
        self._rebuild_load_editor()
        self.refresh()

    def _add_point_dialog(self) -> None:
        position = self.span.get() / 2.0
        if self.support.get() == "Cantilever":
            position = self.span.get()
        self._open_load_dialog("Point load", magnitude="1", position=f"{position:g}")

    def _add_uniform_dialog(self) -> None:
        self._open_load_dialog(
            "Uniform load",
            magnitude="1",
            start="0",
            end=f"{self.span.get():g}",
        )

    def _open_load_dialog(
        self,
        title: str,
        magnitude: str,
        position: str | None = None,
        start: str | None = None,
        end: str | None = None,
        callback=None,
    ) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()

        fields = {}
        row = 0
        for label, value in (("Magnitude (kips/kips-ft)", magnitude),):
            ttk.Label(dialog, text=label).grid(row=row, column=0, padx=8, pady=6, sticky="w")
            entry = ttk.Entry(dialog, width=12)
            entry.insert(0, value)
            entry.grid(row=row, column=1, padx=8, pady=6)
            fields["magnitude"] = entry
            row += 1

        if position is not None:
            ttk.Label(dialog, text="Position (ft)").grid(row=row, column=0, padx=8, pady=6, sticky="w")
            entry = ttk.Entry(dialog, width=12)
            entry.insert(0, position)
            entry.grid(row=row, column=1, padx=8, pady=6)
            fields["position"] = entry
        else:
            for label, key, value in (
                ("Start (ft)", "start", start),
                ("End (ft)", "end", end),
            ):
                ttk.Label(dialog, text=label).grid(row=row, column=0, padx=8, pady=6, sticky="w")
                entry = ttk.Entry(dialog, width=12)
                entry.insert(0, value)
                entry.grid(row=row, column=1, padx=8, pady=6)
                fields[key] = entry
                row += 1

        def save() -> None:
            try:
                magnitude_value = float(fields["magnitude"].get())
                if position is not None:
                    position_value = float(fields["position"].get())
                    position_value = min(max(position_value, 0.0), self.span.get())
                    if callback:
                        callback(position_value, magnitude_value)
                    else:
                        self.point_loads.append(PointLoad(magnitude_value, position_value))
                else:
                    start_value = float(fields["start"].get())
                    end_value = float(fields["end"].get())
                    if callback:
                        callback(start_value, end_value, magnitude_value)
                    else:
                        self.uniform_loads.append(
                            UniformLoad(magnitude_value, start_value, end_value)
                        )
            except ValueError:
                messagebox.showerror("Invalid input", "Enter valid numeric values.", parent=dialog)
                return
            dialog.destroy()
            self._rebuild_load_editor()
            self.refresh()

        ttk.Button(dialog, text="Save", command=save).grid(
            row=row + 1, column=0, columnspan=2, pady=(6, 10)
        )

    def _rebuild_load_editor(self) -> None:
        for widget in self.loads_container.winfo_children():
            widget.destroy()

        if not self.point_loads and not self.uniform_loads:
            ttk.Label(self.loads_container, text="No loads").pack(pady=8)
            return

        for index, load in enumerate(self.point_loads):
            frame = ttk.Frame(self.loads_container)
            frame.pack(fill=tk.X, pady=3)
            ttk.Label(frame, text=f"Point {index + 1}", width=9).pack(side=tk.LEFT)
            magnitude = tk.StringVar(value=f"{load.magnitude:g}")
            position = tk.StringVar(value=f"{load.position:g}")
            ttk.Entry(frame, textvariable=magnitude, width=8).pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text="k").pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=position, width=8).pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text="ft").pack(side=tk.LEFT)
            magnitude.trace_add("write", lambda *_, i=index, v=magnitude, p=position: self._edit_point(i, v, p))
            position.trace_add("write", lambda *_, i=index, v=magnitude, p=position: self._edit_point(i, v, p))
            ttk.Button(frame, text="x", width=3, command=lambda i=index: self._remove_point(i)).pack(
                side=tk.RIGHT
            )

        for index, load in enumerate(self.uniform_loads):
            frame = ttk.Frame(self.loads_container)
            frame.pack(fill=tk.X, pady=3)
            ttk.Label(frame, text=f"Uniform {index + 1}", width=10).pack(side=tk.LEFT)
            magnitude = tk.StringVar(value=f"{load.magnitude:g}")
            start = tk.StringVar(value=f"{load.start:g}")
            end = tk.StringVar(value=f"{load.end:g}")
            ttk.Entry(frame, textvariable=magnitude, width=7).pack(side=tk.LEFT, padx=2)
            ttk.Entry(frame, textvariable=start, width=7).pack(side=tk.LEFT, padx=2)
            ttk.Entry(frame, textvariable=end, width=7).pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text="k/ft (from/to ft)").pack(side=tk.LEFT)
            for variable in (magnitude, start, end):
                variable.trace_add(
                    "write",
                    lambda *_, i=index, m=magnitude, s=start, e=end: self._edit_uniform(i, m, s, e),
                )
            ttk.Button(
                frame, text="x", width=3, command=lambda i=index: self._remove_uniform(i)
            ).pack(side=tk.RIGHT)

    def _edit_point(self, index: int, magnitude, position) -> None:
        try:
            magnitude_value = float(magnitude.get())
            position_value = min(max(float(position.get()), 0.0), self.span.get())
        except (ValueError, tk.TclError):
            return
        if index < len(self.point_loads):
            self.point_loads[index] = PointLoad(magnitude_value, position_value)
            self.refresh()

    def _edit_uniform(self, index: int, magnitude, start, end) -> None:
        try:
            magnitude_value = float(magnitude.get())
            start_value = float(start.get())
            end_value = float(end.get())
        except (ValueError, tk.TclError):
            return
        if index < len(self.uniform_loads):
            self.uniform_loads[index] = UniformLoad(magnitude_value, start_value, end_value)
            self.refresh()

    def _remove_point(self, index: int) -> None:
        del self.point_loads[index]
        self._rebuild_load_editor()
        self.refresh()

    def _remove_uniform(self, index: int) -> None:
        del self.uniform_loads[index]
        self._rebuild_load_editor()
        self.refresh()

    def _section_properties(self) -> tuple[float, float]:
        sections = STEEL_SECTIONS if self.material.get() == "Steel" else LUMBER_SECTIONS
        section = next(item for item in sections if item["name"] == self.section.get())
        return section["Ix"], section["Sx"]

    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        span = self.span.get()
        if span < 4.0:
            span = 4.0
        elif span > 40.0:
            span = 40.0

        Ix, Sx = self._section_properties()
        E = 29000.0 if self.material.get() == "Steel" else 1600.0
        Fb = 30.0 if self.material.get() == "Steel" else 0.900
        denominator = 240 if self.deflection_option.get() == "L/240" else 360

        result = analyze_beam(
            self.support.get(),
            span,
            self.point_loads,
            self.uniform_loads,
            E,
            Ix,
        )
        bending = bending_stress(result.max_moment, Sx)
        limit = deflection_limit(span, denominator)
        deflection_ok = abs(result.max_deflection) <= limit
        bending_ok = bending <= Fb

        self._update_cards(bending, Fb, bending_ok, abs(result.max_deflection), limit, deflection_ok)
        self._update_suggestion(result)
        self._draw(result, span)

    def _update_cards(
        self,
        bending: float,
        bending_allowable: float,
        bending_ok: bool,
        deflection: float,
        deflection_allowable: float,
        deflection_ok: bool,
    ) -> None:
        self._fill_card(
            self.bending_card,
            f"{bending:.3f} ksi",
            f"{bending_allowable:.3f} ksi",
            bending / bending_allowable,
            bending_ok,
        )
        self._fill_card(
            self.deflection_card,
            f"{deflection:.3f} in",
            f"{deflection_allowable:.3f} in",
            deflection / deflection_allowable,
            deflection_ok,
        )

    def _fill_card(
        self,
        card: ttk.LabelFrame,
        actual: str,
        allowable: str,
        ratio: float,
        passed: bool,
    ) -> None:
        for widget in card.winfo_children():
            widget.destroy()
        color = GREEN if ratio < 0.70 else (AMBER if ratio <= 1.0 else RED)
        ttk.Label(card, text=f"{actual} / {allowable}", font=("TkDefaultFont", 11, "bold")).pack(
            padx=8, pady=(6, 2), anchor="w"
        )
        bar = tk.Canvas(card, height=16, bg="white", highlightthickness=1, highlightbackground="#d0d0d0")
        bar.pack(fill=tk.X, padx=8, pady=4)
        bar.update_idletasks()
        width = max(bar.winfo_width(), 100)
        bar.create_rectangle(0, 0, width * min(ratio, 1.0), 16, fill=color, outline="")
        ttk.Label(
            card,
            text="PASS" if passed else "FAIL",
            foreground=GREEN if passed else RED,
            font=("TkDefaultFont", 11, "bold"),
        ).pack(padx=8, pady=(2, 6), anchor="e")

    def _update_suggestion(self, result) -> None:
        denominator = 240 if self.deflection_option.get() == "L/240" else 360
        suggested = lightest_passing_section(
            self.material.get(),
            self.support.get(),
            self.span.get(),
            self.point_loads,
            self.uniform_loads,
            denominator,
        )
        self._suggested_section = suggested
        if suggested:
            weight = suggested.get("weight")
            detail = f" — {weight:g} lb/ft" if weight is not None else ""
            self.suggestion_label.configure(
                text=f"Lightest passing section: {suggested['name']}{detail}"
            )
            self.use_section_button.pack(side=tk.RIGHT)
        else:
            self.suggestion_label.configure(text="No passing section in the selected material.")
            self.use_section_button.pack_forget()

    def _use_suggested_section(self) -> None:
        if self._suggested_section:
            self.section.set(self._suggested_section["name"])
            self.refresh()

    def _draw(self, result, span: float) -> None:
        self.figure.clear()
        self.figure.subplots_adjust(left=0.09, right=0.98, top=0.97, bottom=0.06, hspace=0.38)
        beam_ax, shear_ax, moment_ax, deflection_ax = self.figure.subplots(
            4, 1, sharex=True,
            gridspec_kw={"height_ratios": [1.1, 1, 1, 1]}
        )

        beam_ax.set_xlim(-0.5, span + 0.5)
        beam_ax.set_ylim(-1.2, 1.2)
        beam_ax.axis("off")
        beam_ax.plot([0, span], [0, 0], color="#333333", lw=5)

        if self.support.get() == "Simply supported":
            beam_ax.plot([0, -0.35], [-0.08, -0.55], "k-", lw=2)
            beam_ax.plot([0, 0.35], [-0.08, -0.55], "k-", lw=2)
            beam_ax.plot([span, span - 0.35], [-0.08, -0.55], "k-", lw=2)
            beam_ax.plot([span, span + 0.35], [-0.08, -0.55], "k-", lw=2)
        else:
            beam_ax.add_patch(Polygon(
                [(-0.55, -0.65), (-0.55, 0.65), (0, 0.65), (0, -0.65)],
                closed=True,
                facecolor="#dddddd",
                edgecolor="#333333",
            ))
            for y in (-0.45, -0.15, 0.15, 0.45):
                beam_ax.plot([-0.55, -0.25], [y - 0.18, y + 0.18], "k-", lw=1)

        beam_ax.annotate(
            f"L={span:g} ft",
            xy=(span / 2.0, 0),
            xytext=(0, -10),
            textcoords="offset points",
            ha="center",
            va="top",
        )
        if self.support.get() == "Simply supported":
            beam_ax.annotate(
                f"{result.left_reaction:.2f} k",
                xy=(0, 0),
                xytext=(0, 20),
                textcoords="offset points",
                ha="center",
            )
            beam_ax.annotate(
                f"{result.right_reaction:.2f} k",
                xy=(span, 0),
                xytext=(0, 20),
                textcoords="offset points",
                ha="center",
            )
        else:
            beam_ax.annotate(
                f"{result.left_reaction:.2f} k",
                xy=(0, 0),
                xytext=(20, 20),
                textcoords="offset points",
                ha="left",
            )
            beam_ax.annotate(
                f"M={result.fixed_moment:.2f} kip-ft",
                xy=(0, 0),
                xytext=(20, -20),
                textcoords="offset points",
                ha="left",
            )

        for index, load in enumerate(self.point_loads):
            position = min(max(load.position, 0.0), span)
            beam_ax.annotate(
                "",
                xy=(position, 0),
                xytext=(position, 0.75),
                arrowprops={"arrowstyle": "-|>", "color": ACCENT, "lw": 1.8},
            )
            beam_ax.text(
                position,
                0.85,
                f"{load.magnitude:g} k",
                ha="center",
                va="bottom",
                color=ACCENT,
                fontsize=8,
            )

        for load in self.uniform_loads:
            start = min(max(load.start, 0.0), span)
            end = min(max(load.end, 0.0), span)
            if end < start:
                start, end = end, start
            if end > start:
                beam_ax.plot([start, end], [0.35, 0.35], color=ACCENT, lw=1.5)
                import numpy as np

                positions = list(np.linspace(start, end, max(3, int((end - start) * 2))))
                for position in positions:
                    beam_ax.annotate(
                        "",
                        xy=(position, 0.35),
                        xytext=(position, 0.72),
                        arrowprops={"arrowstyle": "-|>", "color": ACCENT, "lw": 1},
                    )
                beam_ax.text(
                    (start + end) / 2,
                    0.82,
                    f"{load.magnitude:g} k/ft",
                    ha="center",
                    color=ACCENT,
                    fontsize=8,
                )

        self._filled_plot(
            shear_ax,
            result.x_ft,
            result.shear,
            "Shear V (kips)",
            result.max_shear,
            result.max_shear_x,
        )
        self._filled_plot(
            moment_ax,
            result.x_ft,
            result.moment,
            "Moment M (kip-ft)",
            result.max_moment,
            result.max_moment_x,
        )
        self._filled_plot(
            deflection_ax,
            result.x_ft,
            result.deflection,
            "Deflection y (in)",
            result.max_deflection,
            result.max_deflection_x,
        )
        deflection_ax.set_xlabel("Position (ft)")

        self.axes = [beam_ax, shear_ax, moment_ax, deflection_ax]
        self.result = result
        self.cursor_lines = []
        self.canvas.draw_idle()

    def _filled_plot(
        self,
        axis,
        x,
        values,
        title: str,
        max_value: float,
        max_x: float,
    ) -> None:
        axis.axhline(0, color="#999999", lw=0.8)
        axis.plot(x, values, color=ACCENT, lw=1.8)
        axis.fill_between(x, 0, values, color="#d9edf7", alpha=0.8)
        axis.set_ylabel(title)
        axis.grid(True, axis="x", alpha=0.25)
        axis.annotate(
            f"{max_value:.3g}",
            xy=(max_x, max_value),
            xytext=(5, 8),
            textcoords="offset points",
            fontsize=8,
            color="#333333",
            path_effects=[patheffects.withStroke(linewidth=2, foreground="white")],
        )

    def _on_mouse_move(self, event) -> None:
        if not hasattr(self, "axes") or event.inaxes not in self.axes:
            return
        x = event.xdata
        if x is None:
            return
        x = min(max(x, 0.0), self.span.get())
        for line in getattr(self, "cursor_lines", []):
            line.remove()
        self.cursor_lines = []
        for axis in self.axes:
            line = axis.axvline(x, color="#555555", lw=1, linestyle="--")
            self.cursor_lines.append(line)

        if hasattr(self, "result"):
            shear = float(__import__("numpy").interp(x, self.result.x_ft, self.result.shear))
            moment = float(__import__("numpy").interp(x, self.result.x_ft, self.result.moment))
            deflection = float(__import__("numpy").interp(x, self.result.x_ft, self.result.deflection))
            self.cursor_status.configure(
                text=f"x={x:.2f} ft   V={shear:.3f} k   M={moment:.3f} kip-ft   y={deflection:.3f} in"
            )
        self.canvas.draw_idle()

    def _on_drag_press(self, event) -> None:
        if event.inaxes is not getattr(self, "axes", [None])[0] or event.xdata is None:
            return
        nearest = None
        nearest_distance = 0.25
        for index, load in enumerate(self.point_loads):
            distance = abs(load.position - event.xdata)
            if distance < nearest_distance:
                nearest = index
                nearest_distance = distance
        self._drag_index = nearest

    def _on_drag_motion(self, event) -> None:
        if self._drag_index is None or event.inaxes is None or event.xdata is None:
            return
        position = round(min(max(event.xdata, 0.0), self.span.get()) * 4.0) / 4.0
        index = self._drag_index
        if index < len(self.point_loads):
            load = self.point_loads[index]
            self.point_loads[index] = PointLoad(load.magnitude, position)
            self._rebuild_load_editor()
            self.refresh()

    def _on_drag_release(self, event) -> None:
        self._drag_index = None
