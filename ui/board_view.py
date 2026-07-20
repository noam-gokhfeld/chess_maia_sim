"""The chessboard widget: an 8x8 grid of labels that renders a position."""

import chess
import customtkinter as ctk

# --- Board appearance -------------------------------------------------------
SQUARE_SIZE = 62
LIGHT_SQUARE = "#EBECD0"
DARK_SQUARE = "#779556"
LIGHT_HIGHLIGHT = "#F5F682"
DARK_HIGHLIGHT = "#B9CA43"
PIECE_COLOR = "#111111"
BOARD_FONT = ("Segoe UI Symbol", 34)


class BoardView(ctk.CTkFrame):
    """Displays a chess position; call ``render`` to update it."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.cells = {}
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                cell = ctk.CTkLabel(
                    self,
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

    def render(self, board, last_move=None):
        """Draw ``board``, highlighting the squares of ``last_move`` if given."""
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
