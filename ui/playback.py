"""Playback model for stepping through a finished game.

Pure logic (uses ``chess`` but no tkinter) so it can be unit-tested without a
display. The UI reads ``board``/``last_move`` to render and ``move_label_text``
for the caption; navigation methods return whether the position changed so the
caller knows when to re-render.
"""

import chess


class GamePlayback:
    """Ordered board positions plus a cursor into them."""

    def __init__(self, positions=None, moves=None, sans=None):
        # A fresh model shows the standard start position with no moves.
        self.positions = positions if positions is not None else [chess.Board()]
        self.moves = moves if moves is not None else []
        self.sans = sans if sans is not None else []
        self.current_ply = 0

    @classmethod
    def from_game(cls, game_product):
        """Build playback from a ``chess.pgn.Game`` (honors its setup FEN)."""
        board = game_product.board()
        positions = [board.copy()]
        moves = []
        sans = []
        for move in game_product.mainline_moves():
            sans.append(board.san(move))
            board.push(move)
            moves.append(move)
            positions.append(board.copy())
        return cls(positions, moves, sans)

    @property
    def board(self):
        """Board at the current ply."""
        return self.positions[self.current_ply]

    @property
    def last_move(self):
        """Move that produced the current position, or None at the start."""
        return self.moves[self.current_ply - 1] if self.current_ply > 0 else None

    def go_to(self, index) -> bool:
        """Jump to ``index`` (clamped). Returns True if the position changed."""
        index = max(0, min(len(self.positions) - 1, index))
        if index == self.current_ply:
            return False
        self.current_ply = index
        return True

    def step(self, delta) -> bool:
        """Move the cursor by ``delta`` plies. Returns True if it changed."""
        return self.go_to(self.current_ply + delta)

    def move_label_text(self) -> str:
        """Caption for the current position (e.g. ``1. e4`` / ``1... e5``)."""
        i = self.current_ply
        if i == 0:
            return "Start position"
        prev = self.positions[i - 1]
        dots = "" if prev.turn == chess.WHITE else "…"
        return f"{prev.fullmove_number}.{dots} {self.sans[i - 1]}    ({i}/{len(self.moves)})"
