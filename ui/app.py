"""The main application window: wires the board, player settings, and playback
together and drives simulations off the UI thread.

Layout at a glance
------------------
The window is a two-column grid:

* Left pane  -- the chess board plus the move caption and navigation buttons.
* Right pane -- a scrollable "Simulation settings" panel on top and a
  fixed-height PGN output box pinned below it.

Because tkinter is single-threaded, the (potentially slow) engine simulation is
run on a background thread and its result is marshalled back onto the UI thread
with ``self.after`` -- see the "Simulation" section below.
"""

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
    """Top-level customtkinter window tying together the board, the per-side
    settings, and playback of a simulated game."""

    def __init__(self):
        """Build the window, lay out both panes, wire key bindings, and draw the
        initial (empty) board."""
        super().__init__()
        self.title("Maia Chess Game Simulator")
        self.geometry("1220x900")
        self.minsize(1080, 760)

        # Playback state, replaced wholesale when a simulation completes.
        self.playback = GamePlayback()

        # Per-side settings components. They are created here without a parent
        # widget; _build_right_pane assigns their ``parent`` and grids them into
        # the shared settings frame.
        self.players = {
            "white": PlayerSettings(None, "White player"),
            "black": PlayerSettings(None, "Black player"),
        }

        # Two-column layout: the left (board) column keeps its natural width
        # (weight 0) while the right (settings) column absorbs any extra space
        # (weight 1). The single row expands vertically.
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
        """Build the board view, the move caption, and the navigation buttons in
        the left column."""
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=10, pady=10, sticky="n")

        self.board_view = BoardView(left)
        self.board_view.pack(padx=8, pady=8)

        self.move_label = ctk.CTkLabel(left, text="Start position", font=("Segoe UI", 15))
        self.move_label.pack(pady=(4, 6))

        # Jump-to-start / step-back / step-forward / jump-to-end buttons, grouped
        # on one row inside a transparent frame.
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
        """Assemble the right column: a scrollable settings panel on top and the
        PGN output box pinned below.

        This method is only an orchestrator. Each logical group of widgets is
        built by a dedicated ``_build_*`` helper that grids itself starting at a
        given row and returns the next free row -- the same ``(row) -> next_row``
        contract used by ``PlayerSettings.build`` -- so the shared 2-column grid
        stays aligned across all sections.
        """
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        # Settings take the available vertical space; the PGN box keeps a fixed
        # height at the bottom. (Row 0 expands, row 1 does not.)
        right.grid_rowconfigure(0, weight=1)

        # Scrollable container for every setting. Column 1 (the inputs) expands so
        # entries/menus stretch to fill the width; column 0 (labels) stays at its
        # natural width.
        settings = ctk.CTkScrollableFrame(right, label_text="Simulation settings")
        settings.grid(row=0, column=0, sticky="nsew")
        settings.grid_columnconfigure(1, weight=1)

        # Thread a running row counter through each builder so all sections share
        # one continuous, aligned grid.
        row = 0
        row = self._build_player_rows(settings, row)
        row = self._build_model_row(settings, row)
        row = self._build_engine_path_rows(settings, row)
        row = self._build_fen_row(settings, row)
        row = self._build_run_controls(settings, row)

        # The PGN box lives on ``right`` (the outer frame's fixed row 1), not in
        # the scrollable settings area above.
        self._build_pgn_box(right)

    def _build_player_rows(self, settings, row) -> int:
        """Grid both players' settings sections into the shared frame.

        Each ``PlayerSettings`` grids itself and returns the next free row, which
        we pass along so the two sections stack without overlapping.
        """
        for player in self.players.values():
            player.parent = settings
            row = player.build(row)
        return row

    def _build_model_row(self, settings, row) -> int:
        """Add the engine model dropdown (5M / 23M / 79M)."""
        ctk.CTkLabel(settings, text="Engine model").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        self.model_menu = ctk.CTkOptionMenu(
            settings, values=config.MODEL_LABELS, command=self._on_model_change
        )
        self.model_menu.set(config.LABEL_BY_MODEL[game.MaiaEngineModel.MAIA3_5M])
        self.model_menu.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        return row + 1

    def _build_engine_path_rows(self, settings, row) -> int:
        """Add the engine-executable path field (with a Browse button) and the
        hint explaining that an empty path launches the engine via Python."""
        ctk.CTkLabel(settings, text="Engine path").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        # A nested frame lets the entry and the Browse button share one grid cell;
        # the entry (column 0) expands, the button keeps its fixed width.
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
        return row + 1

    def _build_fen_row(self, settings, row) -> int:
        """Add the starting-FEN entry (defaults to the standard start position)."""
        ctk.CTkLabel(settings, text="Starting FEN").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        self.fen_entry = ctk.CTkEntry(settings)
        self.fen_entry.insert(0, chess.STARTING_FEN)
        self.fen_entry.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        return row + 1

    def _build_run_controls(self, settings, row) -> int:
        """Add the Simulate button, the status label, and the progress bar.

        All three span both columns so they stretch across the panel width.
        """
        self.simulate_btn = ctk.CTkButton(settings, text="Simulate", command=self._on_simulate)
        self.simulate_btn.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 6))
        row += 1

        self.status_label = ctk.CTkLabel(settings, text="Ready.", anchor="w")
        self.status_label.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8)
        row += 1

        # Indeterminate bar: it only animates (start/stop) while a simulation is
        # in flight -- there is no measurable percentage to show.
        self.progress = ctk.CTkProgressBar(settings, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        self.progress.set(0)
        return row + 1

    def _build_pgn_box(self, right):
        """Add the fixed-height PGN output box below the settings panel.

        It is parented to ``right`` (the outer frame's fixed row 1), so it stays
        put below the scrollable settings rather than scrolling with them.
        """
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
        """Open a file picker and copy the chosen executable into the path field."""
        path = filedialog.askopenfilename(
            title="Select Maia engine executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    # -- Simulation ---------------------------------------------------------
    def _on_simulate(self):
        """Validate the inputs, then kick off the engine simulation.

        Runs on the UI thread: it reads and checks the widget values, disables the
        button, shows progress, and hands the actual (slow) work to a background
        thread so the window stays responsive.
        """
        # ELO ratings must be whole numbers; reject non-numeric input early.
        try:
            white_elo = int(self.players["white"].elo.get())
            black_elo = int(self.players["black"].elo.get())
        except ValueError:
            self._set_status("ELO ratings must be whole numbers.", error=True)
            return

        # An empty FEN falls back to the standard start position; anything else
        # must parse as a legal board before we run the engine.
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

        # Lock the button and start the animation, then run the simulation off the
        # UI thread (daemon so it dies with the app).
        self.simulate_btn.configure(state="disabled")
        self._set_status("Simulating…")
        self.progress.start()
        threading.Thread(target=self._run_sim, args=(params,), daemon=True).start()

    def _run_sim(self, params):
        """Run the simulation on a background thread.

        tkinter is not thread-safe, so this never touches widgets directly: it
        marshals the outcome (success or failure) back onto the UI thread with
        ``self.after(0, ...)``, which queues ``_on_sim_done`` to run there.
        """
        try:
            result = game.simulate_game(**params)
        except Exception as exc:  # surface any failure in the UI
            self.after(0, self._on_sim_done, None, str(exc))
            return
        self.after(0, self._on_sim_done, result, None)

    def _on_sim_done(self, result, error):
        """Handle a finished simulation back on the UI thread: stop the progress
        bar, re-enable the button, and either show an error or load the game."""
        self.progress.stop()
        self.progress.set(0)
        self.simulate_btn.configure(state="normal")

        if error is not None:
            self._set_status(f"Simulation failed: {error}", error=True)
            return
        if result is None:
            self._set_status("Simulation failed — see console for details.", error=True)
            return

        # Show the game's PGN and load it into playback so the board can step
        # through the moves.
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
        """Arrow-key handler: step through the game unless an entry is focused.

        While the user is typing in a text field we let the arrow keys move the
        text cursor instead of navigating the game.
        """
        if isinstance(self.focus_get(), tk.Entry):
            return
        self._step(delta)

    def _step(self, delta):
        """Move ``delta`` plies forward/backward and redraw if the move succeeded."""
        if self.playback.step(delta):
            self._refresh()

    def _go_to(self, index):
        """Jump to a specific position index and redraw if it changed."""
        if self.playback.go_to(index):
            self._refresh()

    def _refresh(self):
        """Redraw the board and move caption from the current playback state."""
        self.board_view.render(self.playback.board, self.playback.last_move)
        self.move_label.configure(text=self.playback.move_label_text())

    def _set_status(self, text, error=False):
        """Update the status line; red for errors, theme-default otherwise."""
        color = "#B22222" if error else ("gray10", "gray90")
        self.status_label.configure(text=text, text_color=color)


def run():
    """Configure the customtkinter theme and start the application event loop."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
