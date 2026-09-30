import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import state
from settings import (
    STREAM_BITS,
    MODULATIONS,
    WINDOW_BITS,
    BG,
    SPINE,
    TICK,
    ACCENT,
    GREEN,
    BTN,
    GRID,
)
from modulation import bps, update_rf_line
from drawing import (
    draw_digital,
    draw_rf,
    draw_constellation,
    update_info,
)


# ============================================================
# UI  –  Tkinter setup (scrollable page, header, streams,
#         animation controls, parameter sliders)
# ============================================================


class SimulatorUI:
    """Builds and owns every Tkinter widget.

    Public attributes that main.py wires into the animation loop:
        root, canvas, ax_bits, ax_rf, ax_const,
        info, stats, mod_buttons, stream_labels, stream_boxes,
        position_scale, speed_scale, button, page_canvas
    """

    def __init__(self, root):
        self.root = root
        root.title("RF Transmission Simulator")
        root.geometry("1100x750")
        root.minsize(900, 600)
        root.configure(bg=BG)

        self._build_scrollable_page()
        self._build_header()
        self._build_modulation_selector()
        self._build_stream_boxes()
        self._build_figure()
        self._build_view_button()
        self._build_controls()

    # ---- scrollable page -------------------------------------------

    def _build_scrollable_page(self):
        self.page_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        page_scrollbar = tk.Scrollbar(
            self.root, orient="vertical", command=self.page_canvas.yview
        )
        self.page = tk.Frame(self.page_canvas, bg=BG)

        self.page.bind(
            "<Configure>",
            lambda e: self.page_canvas.configure(
                scrollregion=self.page_canvas.bbox("all")
            ),
        )

        self._page_window = self.page_canvas.create_window(
            (0, 0), window=self.page, anchor="nw"
        )
        self.page_canvas.configure(yscrollcommand=page_scrollbar.set)

        page_scrollbar.pack(side="right", fill="y")
        self.page_canvas.pack(side="left", fill="both", expand=True)

        self.page_canvas.bind("<Configure>", self._resize_page)
        self.page_canvas.bind_all("<MouseWheel>", self._scroll_page)

    def _resize_page(self, event):
        self.page_canvas.itemconfig(self._page_window, width=event.width)

    def _scroll_page(self, event):
        self.page_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ---- header ----------------------------------------------------

    def _build_header(self):
        header = tk.Frame(self.page, bg=BG)
        header.pack(fill="x", padx=25, pady=(15, 6))

        title = tk.Label(
            header,
            text="YCbCr → RF Transmission Simulator",
            fg="white",
            bg=BG,
            font=("Arial", 20, "bold"),
        )
        title.pack(anchor="w")

        self.info = tk.Label(
            header, text="", fg="#9aa4ad", bg=BG, font=("Arial", 11)
        )
        self.info.pack(anchor="w", pady=(4, 0))

    # ---- modulation selector ---------------------------------------

    def _build_modulation_selector(self):
        mod_frame = tk.Frame(self.page, bg=BG)
        mod_frame.pack(fill="x", padx=25, pady=(4, 2))

        tk.Label(
            mod_frame,
            text="Modulation",
            fg="white",
            bg=BG,
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=(0, 10))

        self.mod_buttons = {}
        for name in MODULATIONS:
            b = tk.Button(
                mod_frame,
                text=name,
                command=lambda n=name: self.set_modulation(n),
                bg=BTN,
                fg="white",
                activeforeground="white",
                relief="flat",
                padx=18,
                pady=5,
                font=("Arial", 10, "bold"),
            )
            b.pack(side="left", padx=4)
            self.mod_buttons[name] = b

        self.stats = tk.Label(
            self.page,
            text="",
            fg="#9aa4ad",
            bg=BG,
            font=("Arial", 10),
            justify="left",
        )
        self.stats.pack(anchor="w", padx=25, pady=(0, 6))

    # ---- stream boxes ----------------------------------------------

    def _build_stream_boxes(self):
        stream_frame = tk.Frame(self.page, bg=BG)
        stream_frame.pack(fill="x", padx=25)

        self.streams = ["Y1", "Y2", "Y3", "Y4", "Cb", "Cr"]
        self.stream_labels = []
        self.stream_boxes = []

        for name in self.streams:
            box = tk.Frame(
                stream_frame,
                bg="#182027",
                highlightbackground=SPINE,
                highlightthickness=1,
            )
            box.pack(side="left", expand=True, fill="x", padx=4)

            name_label = tk.Label(
                box, text=name, fg="white", bg="#182027", font=("Arial", 13, "bold")
            )
            name_label.pack(pady=(8, 2))

            status = tk.Label(
                box,
                text="● TX → RF → RX ●",
                fg=GREEN,
                bg="#182027",
                font=("Arial", 9),
            )
            status.pack(pady=(0, 8))

            for widget in (box, name_label, status):
                widget.bind(
                    "<Button-1>", lambda event, n=name: self.select_stream(n)
                )

            self.stream_labels.append(status)
            self.stream_boxes.append(box)

    # ---- matplotlib figure -----------------------------------------

    def _build_figure(self):
        self.fig = Figure(figsize=(10, 8.5), constrained_layout=True, facecolor=BG)
        self.ax_bits = self.fig.add_subplot(311)
        self.ax_rf = self.fig.add_subplot(312)
        self.ax_const = self.fig.add_subplot(313)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.page)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=25, pady=15)

    # ---- view constellation button ---------------------------------

    def _build_view_button(self):
        view_frame = tk.Frame(self.page, bg=BG)
        view_frame.pack(pady=(2, 6))

        view_button = tk.Button(
            view_frame,
            text="▼  VIEW CONSTELLATION",
            command=self._show_constellation,
            bg=BTN,
            fg="white",
            activebackground="#344c60",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=7,
            font=("Arial", 10, "bold"),
        )
        view_button.pack()

    def _show_constellation(self):
        self.page_canvas.update_idletasks()
        self.page_canvas.yview_moveto(1.0)

    # ---- bottom controls -------------------------------------------

    def _build_controls(self):
        button_frame = tk.Frame(self.root, bg=BG)
        button_frame.pack(pady=(0, 3))

        self.button = tk.Button(
            button_frame,
            text="▶  START",
            command=self.toggle,
            bg=BTN,
            fg="white",
            activebackground="#344c60",
            activeforeground="white",
            relief="flat",
            padx=30,
            pady=10,
            font=("Arial", 11, "bold"),
        )
        self.button.pack(side="left", padx=10)

        speed_frame = tk.Frame(self.root, bg=BG)
        speed_frame.pack(pady=(0, 2))

        tk.Label(
            speed_frame, text="Wave Speed", fg="white", bg=BG, font=("Arial", 10)
        ).pack(side="left", padx=8)

        self.speed_scale = tk.Scale(
            speed_frame,
            from_=1,
            to=100,
            orient="horizontal",
            length=250,
            bg=BG,
            fg="white",
            highlightthickness=0,
            troughcolor=GRID,
            activebackground=ACCENT,
            showvalue=True,
        )
        self.speed_scale.set(50)
        self.speed_scale.pack(side="left")

        position_frame = tk.Frame(self.root, bg=BG)
        position_frame.pack(pady=(0, 10))

        tk.Label(
            position_frame,
            text="Digital Position",
            fg="white",
            bg=BG,
            font=("Arial", 10),
        ).pack(side="left", padx=8)

        self.position_scale = tk.Scale(
            position_frame,
            from_=0,
            to=max(0, len(state.BITS) - WINDOW_BITS),
            orient="horizontal",
            length=250,
            bg=BG,
            fg="white",
            highlightthickness=0,
            troughcolor=GRID,
            activebackground=ACCENT,
            showvalue=True,
            command=self._move_digital,
        )
        self.position_scale.set(0)
        self.position_scale.pack(side="left")

    # ============================================================
    # CALLBACKS  (identical logic to the original)
    # ============================================================

    def redraw_all(self):
        update_info(self.info, self.stats)
        draw_digital(self.ax_bits)
        draw_rf(self.ax_rf)
        draw_constellation(self.ax_const)
        self.canvas.draw_idle()

    def set_modulation(self, name):
        state.modulation = name

        for key, btn in self.mod_buttons.items():
            if key == name:
                btn.config(bg=ACCENT, fg="#08111a", activebackground=ACCENT)
            else:
                btn.config(bg=BTN, fg="white", activebackground="#344c60")

        self.redraw_all()

    def select_stream(self, name):
        state.selected_stream = name
        state.BITS = STREAM_BITS[name]
        state.window_start = 0
        state.phase_offset = 0.0

        for box, s in zip(self.stream_boxes, self.streams):
            box.config(highlightbackground=ACCENT if s == name else SPINE)

        self.position_scale.config(to=max(0, len(state.BITS) - WINDOW_BITS))
        self.position_scale.set(0)

        self.redraw_all()

    def toggle(self):
        state.running = not state.running

        if state.running:
            self.button.config(text="■  STOP")
            for label in self.stream_labels:
                label.config(text="● TRANSMITTING", fg=ACCENT)
            if state.animation_job is None:
                self._animate()
        else:
            # Cancel the pending tick so a quick STOP/START can't run two loops
            if state.animation_job is not None:
                self.root.after_cancel(state.animation_job)
                state.animation_job = None
            self.button.config(text="▶  START")
            for label in self.stream_labels:
                label.config(text="● TX → RF → RX ●", fg=GREEN)

    def _animate(self):
        if not state.running:
            state.animation_job = None
            return

        state.phase_offset += 0.18

        if len(state.BITS) > WINDOW_BITS:
            state.window_start += 1
            if state.window_start > len(state.BITS) - WINDOW_BITS:
                state.window_start = 0

        # Slider follows the clock (its callback ignores unchanged values)
        self.position_scale.set(state.window_start)

        draw_digital(self.ax_bits)
        update_rf_line()
        draw_constellation(self.ax_const)
        self.canvas.draw_idle()

        speed = self.speed_scale.get()
        delay = max(10, int(200 - speed * 1.9))
        state.animation_job = self.root.after(delay, self._animate)

    def _move_digital(self, value):
        """Manual drag of the position slider: all three plots follow it."""
        new_start = int(float(value))
        if new_start == state.window_start:
            return  # animation already moved us here; nothing to redraw

        state.window_start = new_start
        draw_digital(self.ax_bits)
        update_rf_line()
        draw_constellation(self.ax_const)
        self.canvas.draw_idle()
