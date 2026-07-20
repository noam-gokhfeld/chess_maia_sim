"""The main application window: wires the board, player settings, and playback
together and drives simulations off the UI thread."""

import threading
import tkinter as tk
from tkinter import filedialog

import chess
import customtkinter as ctk

import game
from ui import config
from ui.board_view import BoardView
from ui.player_settings import PlayerSettings
from ui.playback import GamePlayback


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Maia Chess Game Simulator")
        self.geometry("1220x900")
        self.minsize(1080, 760)

        # Playback state, replaced wholesale when a simulation completes.
        self.playback = GamePlayback()

        # Per-side settings components, built by _build_right_pane.
        self.players = {
            "white": PlayerSettings(None, "White player"),
            "black": PlayerSettings(None, "Black player"),
        }

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_pane()
        self._build_right_pane()

        # Arrow-key navigation (ignored while typing in an entry).
        self.bind("<Left>", lambda e: self._maybe_nav(e, -1))
        self.bind("<Right>", lambda e: self._maybe_nav(e, +1))

        self._refresh()

    # -- Left pane: board + navigation --------------------------------------
    def _build_left_pane(self):
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="n")

        self.board_view = BoardView(left)
        self.board_view.pack(padx=8, pady=8)

        self.move_label = ctk.CTkLabel(left, text="Start position", font=("Segoe UI", 15))
        self.move_label.pack(pady=(4, 6))

        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(pady=(0, 8))
        for text, cmd in (
            ("⏮", lambda: self._go_to(0)),
            ("◀", lambda: self._step(-1)),
            ("▶", lambda: self._step(+1)),
            ("⏭", lambda: self._go_to(len(self.playback.positions) - 1)),
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
        # Settings take the available vertical space; the PGN box keeps a fixed
        # height at the bottom. (Row 0 expands, row 1 does not.)
        right.grid_rowconfigure(0, weight=1)

        settings = ctk.CTkScrollableFrame(right, label_text="Simulation settings")
        settings.grid(row=0, column=0, sticky="nsew")
        settings.grid_columnconfigure(1, weight=1)

        row = 0
        for player in self.players.values():
            player.parent = settings
            row = player.build(row)

        # Engine model type (5M / 23M / 79M).
        ctk.CTkLabel(settings, text="Engine model").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        self.model_menu = ctk.CTkOptionMenu(
            settings, values=config.MODEL_LABELS, command=self._on_model_change
        )
        self.model_menu.set(config.LABEL_BY_MODEL[game.MaiaEngineModel.MAIA3_5M])
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
        self.path_entry.insert(0, config.default_engine_path(game.MaiaEngineModel.MAIA3_5M))
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

        # PGN output (fixed height, pinned below the settings).
        self.pgn_box = ctk.CTkTextbox(right, height=200, font=("Consolas", 13), wrap="word")
        self.pgn_box.grid(row=1, column=0, sticky="ew", pady=(10, 0))

    def _on_model_change(self, label):
        """Keep the engine path in sync with the selected model, unless the user
        typed a custom path (then we leave it untouched)."""
        model = config.MODEL_BY_LABEL[label]
        if config.is_default_path(self.path_entry.get()):
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, config.default_engine_path(model))

    def _browse_engine(self):
        path = filedialog.askopenfilename(
            title="Select Maia engine executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    # -- Simulation ---------------------------------------------------------
    def _on_simulate(self):
        try:
            white_elo = int(self.players["white"].elo.get())
            black_elo = int(self.players["black"].elo.get())
        except ValueError:
            self._set_status("ELO ratings must be whole numbers.", error=True)
            return

        fen = self.fen_entry.get().strip() or chess.STARTING_FEN
        try:
            chess.Board(fen)
        except ValueError:
            self._set_status("Invalid FEN string.", error=True)
            return

        style_w, temp_w, topp_w = self.players["white"].get_config()
        style_b, temp_b, topp_b = self.players["black"].get_config()

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
            engine_model=config.MODEL_BY_LABEL[self.model_menu.get()],
            fen=fen,
            path_to_engine=self.path_entry.get().strip() or None,
        )

        self.simulate_btn.configure(state="disabled")
        self._set_status("Simulating…")
        self.progress.start()
        threading.Thread(target=self._run_sim, args=(params,), daemon=True).start()

    def _run_sim(self, params):
        try:
            result = game.simulate_game(**params)
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
        self.playback = GamePlayback.from_game(result)
        self._refresh()
        self._set_status(
            f"Complete — {len(self.playback.moves)} moves. Use ← / → to step through."
        )
        self.focus_set()

    # -- Playback -----------------------------------------------------------
    def _maybe_nav(self, event, delta):
        # Ignore arrow keys while an entry has focus (let the text cursor move).
        if isinstance(self.focus_get(), tk.Entry):
            return
        self._step(delta)

    def _step(self, delta):
        if self.playback.step(delta):
            self._refresh()

    def _go_to(self, index):
        if self.playback.go_to(index):
            self._refresh()

    def _refresh(self):
        """Redraw the board and move caption from the current playback state."""
        self.board_view.render(self.playback.board, self.playback.last_move)
        self.move_label.configure(text=self.playback.move_label_text())

    def _set_status(self, text, error=False):
        color = "#B22222" if error else ("gray10", "gray90")
        self.status_label.configure(text=text, text_color=color)


def run():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
