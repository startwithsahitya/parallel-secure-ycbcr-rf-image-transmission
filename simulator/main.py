"""RF Transmission Simulator  –  entry point.

Initialises the Tkinter root, builds the UI, triggers the first
draw, and enters the main event loop.
"""

import tkinter as tk
from ui import SimulatorUI
import state
from report_generator import generate_report


def main():
    root = tk.Tk()
    app = SimulatorUI(root)

    # Every widget referenced by these calls now exists.
    app.select_stream(state.selected_stream)
    app.set_modulation(state.modulation)
    generate_report()

    root.mainloop()


if __name__ == "__main__":
    main()
