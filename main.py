import os
import sys

# Windows venvs often can't locate the Tcl/Tk runtime (Tcl searches relative to
# .venv\Scripts\ and never finds the base install's `tcl` folder), which makes
# tkinter fail to start. Point it at the base interpreter's Tcl/Tk before any
# tkinter import. Guarded: only on Windows, only if not already configured, and
# only when the directories actually exist -- a no-op in healthy environments.
if sys.platform == "win32" and "TCL_LIBRARY" not in os.environ:
    _tcl_root = os.path.join(sys.base_prefix, "tcl")
    _tcl_lib = os.path.join(_tcl_root, "tcl8.6")
    _tk_lib = os.path.join(_tcl_root, "tk8.6")
    if os.path.isdir(_tcl_lib):
        os.environ["TCL_LIBRARY"] = _tcl_lib
    if os.path.isdir(_tk_lib):
        os.environ["TK_LIBRARY"] = _tk_lib

import asyncio
import threading
import tkinter as tk
from tkinter import filedialog

import chess
import customtkinter as ctk

import game

# --- Engine defaults --------------------------------------------------------
# The console app hardcoded the 5M engine under the project's venv. Derive the
# same location relative to this file so it works regardless of where the repo
# lives, and expose it as an editable field in the UI.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_SCRIPTS = os.path.join(PROJECT_DIR, ".venv", "Scripts")


def default_engine_path(model: game.MaiaEngineModel) -> str:
    """Path to the bundled Maia executable matching a model (e.g. maia3-5m.exe)."""
    return os.path.join(VENV_SCRIPTS, f"{model.value}.exe")


# "MAIA3_5M" -> "5M", keyed for the model dropdown.
MODEL_BY_LABEL = {m.name.replace("MAIA3_", ""): m for m in game.MaiaEngineModel}
MODEL_LABELS = list(MODEL_BY_LABEL.keys())
LABEL_BY_MODEL = {m: label for label, m in MODEL_BY_LABEL.items()}

# Named playing styles the user can pick (everything except the "off" sentinel).
STYLE_NAMES = [
    s.name for s in game.PlayingStyles if s != game.PlayingStyles.NOT_USING_PLAYING_STYLE
]

# --- Board appearance -------------------------------------------------------
SQUARE_SIZE = 62
LIGHT_SQUARE = "#EBECD0"
DARK_SQUARE = "#779556"
LIGHT_HIGHLIGHT = "#F5F682"
DARK_HIGHLIGHT = "#B9CA43"
PIECE_COLOR = "#111111"
BOARD_FONT = ("Segoe UI Symbol", 34)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Maia Chess Game Simulator")
        self.geometry("1180x780")
        self.minsize(1040, 700)

        # Playback state, populated after a simulation completes.
        self.positions = [chess.Board()]
        self.moves = []
        self.sans = []
        self.current_ply = 0

        # Per-side widget references, filled by _build_player_section.
        self.side_widgets = {}

        # Normalized set of the bundled engine paths, used to decide whether the
        # engine-path field is still a "default" we may auto-swap when the model
        # changes (vs. a custom path the user typed, which we leave alone).
        self._default_paths = {
            os.path.normcase(default_engine_path(m)) for m in game.MaiaEngineModel
        }

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_pane()
        self._build_right_pane()

        # Arrow-key navigation (ignored while typing in an entry).
        self.bind("<Left>", lambda e: self._maybe_nav(e, -1))
        self.bind("<Right>", lambda e: self._maybe_nav(e, +1))

        self._render()
        self._update_move_label()

    # -- Left pane: board + navigation --------------------------------------
    def _build_left_pane(self):
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="n")

        board_frame = ctk.CTkFrame(left, fg_color="transparent")
        board_frame.pack(padx=8, pady=8)

        self.cells = {}
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                cell = ctk.CTkLabel(
                    board_frame,
                    text="",
                    width=SQUARE_SIZE,
                    height=SQUARE_SIZE,
                    corner_radius=0,
                    font=BOARD_FONT,
                    text_color=PIECE_COLOR,
                )
                # Rank 8 on top -> grid row 0; file a on the left -> column 0.
                cell.grid(row=7 - rank, column=file, padx=0, pady=0)
                self.cells[square] = cell

        self.move_label = ctk.CTkLabel(left, text="Start position", font=("Segoe UI", 15))
        self.move_label.pack(pady=(4, 6))

        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(pady=(0, 8))
        for text, cmd in (
            ("⏮", lambda: self._go_to(0)),
            ("◀", lambda: self._step(-1)),
            ("▶", lambda: self._step(+1)),
            ("⏭", lambda: self._go_to(len(self.positions) - 1)),
        ):
            ctk.CTkButton(nav, text=text, width=54, command=cmd).pack(side="left", padx=4)

        ctk.CTkLabel(
            left,
            text="Use ← / → arrow keys to step through the game",
            font=("Segoe UI", 12),
            text_color="gray",
        ).pack(pady=(0, 4))

    # -- Right pane: settings (top) + PGN (bottom) --------------------------
    def _build_right_pane(self):
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        settings = ctk.CTkScrollableFrame(right, label_text="Simulation settings")
        settings.grid(row=0, column=0, sticky="ew")
        settings.grid_columnconfigure(1, weight=1)

        row = 0
        row = self._build_player_section(settings, "white", "White player", row)
        row = self._build_player_section(settings, "black", "Black player", row)

        # Engine model type (5M / 23M / 79M).
        ctk.CTkLabel(settings, text="Engine model").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        self.model_menu = ctk.CTkOptionMenu(
            settings, values=MODEL_LABELS, command=self._on_model_change
        )
        self.model_menu.set(LABEL_BY_MODEL[game.MaiaEngineModel.MAIA3_5M])
        self.model_menu.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        row += 1

        # Engine executable path + Browse.
        ctk.CTkLabel(settings, text="Engine path").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        path_frame = ctk.CTkFrame(settings, fg_color="transparent")
        path_frame.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        path_frame.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(path_frame)
        self.path_entry.insert(0, default_engine_path(game.MaiaEngineModel.MAIA3_5M))
        self.path_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            path_frame, text="Browse…", width=80, command=self._browse_engine
        ).grid(row=0, column=1, padx=(6, 0))
        row += 1

        ctk.CTkLabel(
            settings,
            text="Leave the path empty to launch the engine via  python -m maia3.uci",
            font=("Segoe UI", 11),
            text_color="gray",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8)
        row += 1

        # Starting FEN.
        ctk.CTkLabel(settings, text="Starting FEN").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        self.fen_entry = ctk.CTkEntry(settings)
        self.fen_entry.insert(0, chess.STARTING_FEN)
        self.fen_entry.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        row += 1

        # Simulate button + status + progress bar.
        self.simulate_btn = ctk.CTkButton(settings, text="Simulate", command=self._on_simulate)
        self.simulate_btn.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 6))
        row += 1

        self.status_label = ctk.CTkLabel(settings, text="Ready.", anchor="w")
        self.status_label.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8)
        row += 1

        self.progress = ctk.CTkProgressBar(settings, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        self.progress.set(0)
        row += 1

        # PGN output.
        self.pgn_box = ctk.CTkTextbox(right, font=("Consolas", 13), wrap="word")
        self.pgn_box.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

    def _build_player_section(self, parent, side, title, row):
        widgets = {}
        self.side_widgets[side] = widgets

        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 2)
        )
        row += 1

        ctk.CTkLabel(parent, text="ELO rating").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        elo = ctk.CTkEntry(parent)
        elo.insert(0, "1500")
        elo.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        widgets["elo"] = elo
        row += 1

        switch = ctk.CTkSwitch(
            parent,
            text="Custom parameters (temperature / top-p)",
            command=lambda s=side: self._toggle_custom(s),
        )
        switch.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        widgets["switch"] = switch
        row += 1

        # Playing-style row (shown when custom is OFF).
        style_label = ctk.CTkLabel(parent, text="Playing style")
        style_label.grid(row=row, column=0, sticky="w", padx=8, pady=4)
        style_menu = ctk.CTkOptionMenu(parent, values=STYLE_NAMES)
        style_menu.set(game.PlayingStyles.NATURAL.name)
        style_menu.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        widgets["style_label"] = style_label
        widgets["style_menu"] = style_menu
        row += 1

        # Temperature row (shown when custom is ON).
        temp_label = ctk.CTkLabel(parent, text="Temperature")
        temp_label.grid(row=row, column=0, sticky="w", padx=8, pady=4)
        temp_frame = ctk.CTkFrame(parent, fg_color="transparent")
        temp_frame.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        temp_frame.grid_columnconfigure(0, weight=1)
        temp_val = ctk.CTkLabel(temp_frame, text="0.75", width=42)
        temp_val.grid(row=0, column=1, padx=(6, 0))
        temp_slider = ctk.CTkSlider(
            temp_frame, from_=0.0, to=1.5,
            command=lambda v, lbl=temp_val: lbl.configure(text=f"{float(v):.2f}"),
        )
        temp_slider.set(0.75)
        temp_slider.grid(row=0, column=0, sticky="ew")
        widgets["temp_label"] = temp_label
        widgets["temp_frame"] = temp_frame
        widgets["temp_slider"] = temp_slider
        row += 1

        # Top-p row (shown when custom is ON).
        topp_label = ctk.CTkLabel(parent, text="Top-p")
        topp_label.grid(row=row, column=0, sticky="w", padx=8, pady=4)
        topp_frame = ctk.CTkFrame(parent, fg_color="transparent")
        topp_frame.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        topp_frame.grid_columnconfigure(0, weight=1)
        topp_val = ctk.CTkLabel(topp_frame, text="0.95", width=42)
        topp_val.grid(row=0, column=1, padx=(6, 0))
        topp_slider = ctk.CTkSlider(
            topp_frame, from_=0.0, to=1.0,
            command=lambda v, lbl=topp_val: lbl.configure(text=f"{float(v):.2f}"),
        )
        topp_slider.set(0.95)
        topp_slider.grid(row=0, column=0, sticky="ew")
        widgets["topp_label"] = topp_label
        widgets["topp_frame"] = topp_frame
        widgets["topp_slider"] = topp_slider
        row += 1

        # Start with custom OFF: hide the temp/top-p rows.
        self._toggle_custom(side)
        return row

    def _toggle_custom(self, side):
        w = self.side_widgets[side]
        custom = bool(w["switch"].get())
        style = (w["style_label"], w["style_menu"])
        params = (w["temp_label"], w["temp_frame"], w["topp_label"], w["topp_frame"])
        for widget in style:
            widget.grid_remove() if custom else widget.grid()
        for widget in params:
            widget.grid() if custom else widget.grid_remove()

    def _on_model_change(self, label):
        """Keep the engine path in sync with the selected model, unless the user
        typed a custom path (then we leave it untouched)."""
        model = MODEL_BY_LABEL[label]
        current = os.path.normcase(self.path_entry.get().strip())
        if current == "" or current in self._default_paths:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, default_engine_path(model))

    def _browse_engine(self):
        path = filedialog.askopenfilename(
            title="Select Maia engine executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    # -- Simulation ---------------------------------------------------------
    def _player_config(self, side):
        """Return (playing_style, custom_temperature, custom_topp) for a side,
        mirroring the console app's per-side logic."""
        w = self.side_widgets[side]
        if w["switch"].get():
            return (
                game.PlayingStyles.NOT_USING_PLAYING_STYLE,
                round(w["temp_slider"].get(), 2),
                round(w["topp_slider"].get(), 2),
            )
        return game.PlayingStyles[w["style_menu"].get()], None, None

    def _on_simulate(self):
        try:
            white_elo = int(self.side_widgets["white"]["elo"].get())
            black_elo = int(self.side_widgets["black"]["elo"].get())
        except ValueError:
            self._set_status("ELO ratings must be whole numbers.", error=True)
            return

        fen = self.fen_entry.get().strip() or chess.STARTING_FEN
        try:
            chess.Board(fen)
        except ValueError:
            self._set_status("Invalid FEN string.", error=True)
            return

        style_w, temp_w, topp_w = self._player_config("white")
        style_b, temp_b, topp_b = self._player_config("black")

        # Same call shape as the original console main.py.
        params = dict(
            white_elo=white_elo,
            black_elo=black_elo,
            playing_style_white=style_w,
            playing_style_black=style_b,
            custom_temperature_white=temp_w,
            custom_topp_white=topp_w,
            custom_temperature_black=temp_b,
            custom_topp_black=topp_b,
            engine_model=MODEL_BY_LABEL[self.model_menu.get()],
            fen=fen,
            path_to_engine=self.path_entry.get().strip() or None,
        )

        self.simulate_btn.configure(state="disabled")
        self._set_status("Simulating…")
        self.progress.start()
        threading.Thread(target=self._run_sim, args=(params,), daemon=True).start()

    def _run_sim(self, params):
        try:
            result = asyncio.run(game.simulate_game(**params))
        except Exception as exc:  # surface any failure in the UI
            self.after(0, self._on_sim_done, None, str(exc))
            return
        self.after(0, self._on_sim_done, result, None)

    def _on_sim_done(self, result, error):
        self.progress.stop()
        self.progress.set(0)
        self.simulate_btn.configure(state="normal")

        if error is not None:
            self._set_status(f"Simulation failed: {error}", error=True)
            return
        if result is None:
            self._set_status("Simulation failed — see console for details.", error=True)
            return

        self.pgn_box.delete("1.0", "end")
        self.pgn_box.insert("1.0", str(result))
        self._load_positions(result)
        self._set_status(f"Complete — {len(self.moves)} moves. Use ← / → to step through.")
        self.focus_set()

    # -- Playback -----------------------------------------------------------
    def _load_positions(self, game_product):
        board = game_product.board()  # honors the game's setup FEN
        self.positions = [board.copy()]
        self.moves = []
        self.sans = []
        for move in game_product.mainline_moves():
            self.sans.append(board.san(move))
            board.push(move)
            self.moves.append(move)
            self.positions.append(board.copy())
        self.current_ply = 0
        self._render()
        self._update_move_label()

    def _maybe_nav(self, event, delta):
        # Ignore arrow keys while an entry has focus (let the text cursor move).
        if isinstance(self.focus_get(), tk.Entry):
            return
        self._step(delta)

    def _step(self, delta):
        self._go_to(self.current_ply + delta)

    def _go_to(self, index):
        if not self.positions:
            return
        index = max(0, min(len(self.positions) - 1, index))
        if index != self.current_ply:
            self.current_ply = index
            self._render()
            self._update_move_label()

    def _render(self):
        board = self.positions[self.current_ply]
        last_move = self.moves[self.current_ply - 1] if self.current_ply > 0 else None
        for square, cell in self.cells.items():
            piece = board.piece_at(square)
            text = piece.unicode_symbol() if piece else ""
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            is_light = (file + rank) % 2 == 1
            if last_move and square in (last_move.from_square, last_move.to_square):
                color = LIGHT_HIGHLIGHT if is_light else DARK_HIGHLIGHT
            else:
                color = LIGHT_SQUARE if is_light else DARK_SQUARE
            cell.configure(text=text, fg_color=color)

    def _update_move_label(self):
        i = self.current_ply
        if i == 0:
            self.move_label.configure(text="Start position")
            return
        prev = self.positions[i - 1]
        dots = "" if prev.turn == chess.WHITE else "…"
        self.move_label.configure(
            text=f"{prev.fullmove_number}.{dots} {self.sans[i - 1]}    ({i}/{len(self.moves)})"
        )

    def _set_status(self, text, error=False):
        color = "#B22222" if error else ("gray10", "gray90")
        self.status_label.configure(text=text, text_color=color)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
