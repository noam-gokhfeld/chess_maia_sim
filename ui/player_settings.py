"""Per-side settings block (ELO + playing style or custom temperature/top-p).

Grids its rows directly into the shared settings frame (so both players and the
engine/FEN rows below stay in one aligned 2-column grid), while owning its own
widget references, the custom-parameters toggle, and config parsing.
"""

import customtkinter as ctk

import game
from ui import config


class PlayerSettings:
    """One player's settings rows within a shared grid."""

    def __init__(self, parent, title):
        self.parent = parent
        self.title = title

    def build(self, start_row) -> int:
        """Grid this section into ``parent`` starting at ``start_row``.

        Returns the next free row so the caller can lay out following widgets.
        """
        parent = self.parent
        row = start_row

        ctk.CTkLabel(
            parent, text=self.title, font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 2))
        row += 1

        ctk.CTkLabel(parent, text="ELO rating").grid(
            row=row, column=0, sticky="w", padx=8, pady=4
        )
        self.elo = ctk.CTkEntry(parent)
        self.elo.insert(0, "1500")
        self.elo.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        row += 1

        self.switch = ctk.CTkSwitch(
            parent,
            text="Custom parameters (temperature / top-p)",
            command=self._toggle_custom,
        )
        self.switch.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        # Playing-style row (shown when custom is OFF).
        self.style_label = ctk.CTkLabel(parent, text="Playing style")
        self.style_label.grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.style_menu = ctk.CTkOptionMenu(parent, values=config.STYLE_NAMES)
        self.style_menu.set(game.PlayingStyles.NATURAL.name)
        self.style_menu.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        row += 1

        # Temperature row (shown when custom is ON).
        self.temp_label = ctk.CTkLabel(parent, text="Temperature")
        self.temp_label.grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.temp_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.temp_frame.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        self.temp_frame.grid_columnconfigure(0, weight=1)
        temp_val = ctk.CTkLabel(self.temp_frame, text="0.75", width=42)
        temp_val.grid(row=0, column=1, padx=(6, 0))
        self.temp_slider = ctk.CTkSlider(
            self.temp_frame, from_=0.0, to=1.5,
            command=lambda v, lbl=temp_val: lbl.configure(text=f"{float(v):.2f}"),
        )
        self.temp_slider.set(0.75)
        self.temp_slider.grid(row=0, column=0, sticky="ew")
        row += 1

        # Top-p row (shown when custom is ON).
        self.topp_label = ctk.CTkLabel(parent, text="Top-p")
        self.topp_label.grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.topp_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.topp_frame.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        self.topp_frame.grid_columnconfigure(0, weight=1)
        topp_val = ctk.CTkLabel(self.topp_frame, text="0.95", width=42)
        topp_val.grid(row=0, column=1, padx=(6, 0))
        self.topp_slider = ctk.CTkSlider(
            self.topp_frame, from_=0.0, to=1.0,
            command=lambda v, lbl=topp_val: lbl.configure(text=f"{float(v):.2f}"),
        )
        self.topp_slider.set(0.95)
        self.topp_slider.grid(row=0, column=0, sticky="ew")
        row += 1

        # Start with custom OFF: hide the temp/top-p rows.
        self._toggle_custom()
        return row

    def _toggle_custom(self):
        """Show the style row when custom is off, temp/top-p rows when on."""
        custom = bool(self.switch.get())
        style = (self.style_label, self.style_menu)
        params = (self.temp_label, self.temp_frame, self.topp_label, self.topp_frame)
        for widget in style:
            widget.grid_remove() if custom else widget.grid()
        for widget in params:
            widget.grid() if custom else widget.grid_remove()

    def get_config(self):
        """Return ``(playing_style, custom_temperature, custom_topp)`` for this side."""
        return config.resolve_player_config(
            bool(self.switch.get()),
            self.temp_slider.get(),
            self.topp_slider.get(),
            self.style_menu.get(),
        )
