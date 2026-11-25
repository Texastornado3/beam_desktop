import tkinter as tk
import unittest

from beam_app import BeamDesignerApp


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("1250x800")
        self.app = BeamDesignerApp(self.root)
        self.root.update_idletasks()

    def tearDown(self):
        self.root.destroy()

    def test_action_buttons_are_in_application_toolbar(self):
        labels = set()
        for child in descendants(self.app.app_toolbar):
            try:
                labels.add(child.cget("text"))
            except tk.TclError:
                pass
        self.assertTrue(
            {"Save Design", "Open Design", "Export CSV", "Export PDF"}.issubset(labels)
        )
        button_labels = [
            child.cget("text")
            for child in self.app.app_toolbar.winfo_children()
            if isinstance(child, tk.Widget) and child.winfo_class() == "TButton"
        ]
        self.assertEqual(
            button_labels.index("Export PDF"),
            button_labels.index("Export CSV") + 1,
        )

    def test_check_cards_are_in_fixed_control_panel(self):
        self.assertIn(
            self.app.bending_card,
            tuple(descendants(self.app.checks_container)),
        )
        self.assertIn(
            self.app.deflection_card,
            tuple(descendants(self.app.checks_container)),
        )
        self.assertNotIn(
            self.app.bending_card,
            tuple(descendants(self.app.results)),
        )
        self.assertNotIn(
            self.app.deflection_card,
            tuple(descendants(self.app.results)),
        )

    def test_minimum_window_layout_widgets_remain_mapped(self):
        self.root.geometry("900x650")
        self.root.update_idletasks()
        self.assertTrue(self.app.app_toolbar.winfo_ismapped())
        self.assertTrue(self.app.checks_container.winfo_ismapped())
        self.assertTrue(self.app.bending_card.winfo_ismapped())
        self.assertTrue(self.app.deflection_card.winfo_ismapped())


if __name__ == "__main__":
    unittest.main()
