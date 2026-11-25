# Beam Designer Desktop Application

## Purpose
A Python desktop beam design tool for engineers and students. The user sets
up a beam, places loads on it, and picks a steel or lumber section. The app
shows the shear, moment, and deflection diagrams and checks whether the beam
is strong and stiff enough, updating immediately as any input changes.

## Platform
- Build the application with Python, Tkinter, and Matplotlib.
- Use Tkinter widgets for the window, controls, input validation, and
  dialogs.
- Embed Matplotlib figures and canvas controls in Tkinter frames.
- Target a conventional desktop window rather than a browser or phone layout.
- Use a system-compatible sans-serif font and a clean, professional
  appearance with a light background, white panels, restrained borders, and
  one accent color.

## Users
A civil engineering student checking a homework beam, or an engineer sizing
a floor beam or deck joist.

## Inputs
- Support type: Simply supported or Cantilever (fixed at the left end).
  Provide a desktop radio-button or option-menu control.
- Span: 4 to 40 ft, set with a Tkinter scale and a synchronized number entry.
- Loads, listed in a scrollable panel where each load can be edited or
  removed:
  - Point loads: magnitude (kips, downward positive) and position (ft).
    A new point load starts at midspan (at the free end of a cantilever).
  - Uniform loads: magnitude (kips/ft) and start and end positions (ft).
  - "Add point load" and "Add uniform load" buttons.
  - Point loads can be dragged along the beam in the embedded Matplotlib
    drawing. The drag position snaps to 0.25 ft.
  - Loads that extend past the end of the beam are cut off at the end.
- Material and section, selected from these tables:

  Steel W-shapes (E = 29,000 ksi, allowable bending stress Fb = 30 ksi):

  | Section | Ix (in^4) | Sx (in^3) | Weight (lb/ft) |
  |---------|-----------|-----------|----------------|
  | W8x10   | 30.8      | 7.81      | 10 |
  | W10x12  | 53.8      | 10.9      | 12 |
  | W12x26  | 204       | 33.4      | 26 |
  | W14x22  | 199       | 29.0      | 22 |
  | W16x26  | 301       | 38.4      | 26 |
  | W18x35  | 510       | 57.6      | 35 |
  | W21x44  | 843       | 81.6      | 44 |
  | W24x55  | 1350      | 114       | 55 |

  Douglas Fir-Larch No. 2 lumber (E = 1,600 ksi, Fb = 0.900 ksi):

  | Section | Ix (in^4) | Sx (in^3) |
  |---------|-----------|-----------|
  | 2x8     | 47.63     | 13.14     |
  | 2x10    | 98.93     | 21.39     |
  | 2x12    | 177.98    | 31.64     |

- Deflection limit: L/240 or L/360 (default L/360).
- Self-weight is ignored.

## Calculations
- Reactions from statics.
- Shear V(x) and moment M(x) along the beam, at 1 ft spacing or finer,
  plus exactly at every load point and load start/end.
- Deflection y(x) by integrating M/EI twice with the boundary conditions
  for the support type (y = 0 at both supports; or y = 0 and slope = 0 at
  the fixed end).
- Bending stress fb = |M max| x 12 / Sx (ksi). Bending check passes if
  fb <= Fb.
- Deflection check passes if |y max| <= L/240 or L/360 (L in inches).
- Lightest passing section: of the sections in the chosen material, the
  lightest steel section that passes both checks (if two weigh the same,
  the one with the larger Ix), or the first lumber size in the table
  that passes.
- Units: kips, ft, and kip-ft on screen; inches for deflection.
- Implement the calculations independently of the Tkinter and Matplotlib
  presentation layer so they can be tested separately.

## Outputs
- A beam drawing with the supports, load arrows (point loads as single
  arrows, uniform loads as a row of small arrows), and the reactions.
- Three Matplotlib diagrams stacked under the beam and lined up with it on
  the same x scale: shear (kips), moment (kip-ft), and deflected shape
  (in). Each diagram is filled and shows its maximum value labeled at its
  location.
- Moving the mouse over any diagram shows a vertical cursor across all three
  plots with the values of V, M, and y at that x. A Tkinter status line may
  also show the cursor values.
- Two desktop check cards: Bending and Deflection. Each shows the actual
  value, the allowable value, a bar for the ratio (green under 70%, amber
  70-100%, red over 100%), and PASS or FAIL.
- A line suggesting the lightest passing section, with a "Use section"
  button that applies it to the selected section.
- Include an "Export CSV" button that uses a native operating-system Save
  dialog. Export the currently displayed beam result table with one row per
  calculated position and these column headers:
  `Position x (ft),Shear V (kips),Moment M (kip-ft),Deflection y (inches)`
- Write the CSV using comma separators, Excel-compatible UTF-8 encoding, and
  Windows-style line endings. Values must reflect the current beam support,
  span, loads, material, section, and deflection limit. The export does not
  alter the beam calculations or saved design.
- Everything updates immediately whenever any input changes. The display
  should avoid blocking or requiring a separate "Calculate" button.

## Desktop Interface
- Open one resizable application window with a left controls panel and a right
  results panel.
- Include a File menu with Save and Open options. Both commands use native
  operating-system file selection dialogs.
- Place Save Design, Open Design, and Export CSV buttons in one dedicated
  application toolbar above the entire left-controls and right-results layout,
  separate from the Matplotlib navigation toolbar.
- Place bending and deflection PASS/FAIL results in a fixed panel directly
  below the input controls, outside the scrollable input area. These results
  must remain visible when the application window or Matplotlib canvas is
  resized.
- Save designs as Beam Designer JSON files. The saved data includes the beam
  support type, span, material, section, deflection limit, and every point
  and uniform load.
- Opening a valid saved design restores all saved inputs, rebuilds the load
  list, and immediately recalculates and redraws the beam, diagrams, and
  strength and deflection checks. Opening an invalid or unsupported file
  leaves the current design unchanged and shows an error dialog.
- Provide Ctrl+S for Save and Ctrl+O for Open as desktop keyboard shortcuts.
- Keep controls in clearly grouped labeled frames. Use a vertical scrollbar
  for the left panel if the available height is small.
- Place the beam drawing and diagrams in the right Matplotlib canvas.
- Show check cards and the lightest-section suggestion below or beside the
  canvas in a results area that remains usable while the window is resized.
- Use visible labels and units on every input. Use Tkinter tooltips or
  adjacent help text to explain formulas where hover help is useful.
- Use a scrollable load list and in-place edit/remove controls.
- All plots, labels, results, and controls must remain readable at common
  desktop window sizes. Provide a Matplotlib toolbar for pan/zoom and
  save/open-image operations if supported by the embedded canvas.
- Preserve the same content and behavior on narrower desktop windows through
  two-panel stacking or compact layout, rather than assuming a browser or
  mobile layout.

## Look and feel
- Opens with an example already loaded (20 ft simply supported W12x26
  with a 1 kip/ft uniform load over the full span), so it is useful the
  moment it opens.
- Clean and professional, with a light background, white cards or labeled
  frames, restrained separators, one accent color, a modern system font,
  and generous spacing. No clutter.
- Inputs have short labels with units.
- Tooltips or adjacent help text explain the bending and deflection formula
  used by each check.

## Validation
1. Simply supported, 20 ft, W12x26, uniform 1 kip/ft over the full span:
   reactions 10 k and 10 k; max shear 10 k; max moment 50.0 kip-ft at
   10 ft; fb = 17.96 ksi; max deflection 0.609 in at 10 ft; L/360 =
   0.667 in; both checks pass.
2. Simply supported, 20 ft, W12x26, point load 10 k at 5 ft: reactions
   7.5 k (left) and 2.5 k (right); max moment 37.5 kip-ft at 5 ft;
   fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.
3. Cantilever, 10 ft, W12x26, point load 5 k at the free end: reaction
   5 k and fixed-end moment 50 kip-ft; max deflection 0.487 in at the free
   end (PL^3/3EI); L/360 = 0.333 in, so deflection fails.
4. Simply supported 12 ft 2x10 joist, uniform 0.05 kip/ft: max moment
   0.90 kip-ft; fb = 0.505 ksi; max deflection 0.147 in; both pass.

## Out of scope
- Self-weight, shear stress, lateral-torsional buckling, load
  combinations, and continuous beams.
- Building or implementing the application itself; this specification is
  documentation only.
