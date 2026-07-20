import unittest

import chess
import chess.pgn

from ui.playback import GamePlayback


def build_game(sans):
    """A chess.pgn.Game with the given SAN mainline from the start position."""
    pgn_game = chess.pgn.Game()
    node = pgn_game
    board = chess.Board()
    for san in sans:
        move = board.push_san(san)
        node = node.add_main_variation(move)
    return pgn_game


class FromGameTests(unittest.TestCase):
    def test_positions_and_sans(self):
        sans = ["e4", "e5", "Nf3"]
        pb = GamePlayback.from_game(build_game(sans))
        self.assertEqual(len(pb.moves), 3)
        self.assertEqual(len(pb.positions), len(pb.moves) + 1)
        self.assertEqual(pb.sans, sans)

    def test_starts_at_ply_zero(self):
        pb = GamePlayback.from_game(build_game(["e4"]))
        self.assertEqual(pb.current_ply, 0)
        self.assertIsNone(pb.last_move)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.pb = GamePlayback.from_game(build_game(["e4", "e5", "Nf3"]))

    def test_go_to_clamps_low(self):
        self.assertFalse(self.pb.go_to(-5))
        self.assertEqual(self.pb.current_ply, 0)

    def test_go_to_clamps_high(self):
        self.assertTrue(self.pb.go_to(999))
        self.assertEqual(self.pb.current_ply, len(self.pb.positions) - 1)

    def test_go_to_same_index_reports_no_change(self):
        self.assertFalse(self.pb.go_to(0))

    def test_step_forward_and_back(self):
        self.assertTrue(self.pb.step(+1))
        self.assertEqual(self.pb.current_ply, 1)
        self.assertTrue(self.pb.step(-1))
        self.assertEqual(self.pb.current_ply, 0)
        # Can't step before the start.
        self.assertFalse(self.pb.step(-1))

    def test_last_move_tracks_cursor(self):
        self.pb.go_to(1)
        self.assertEqual(self.pb.last_move, self.pb.moves[0])


class MoveLabelTests(unittest.TestCase):
    def setUp(self):
        self.pb = GamePlayback.from_game(build_game(["e4", "e5"]))

    def test_start_position(self):
        self.assertEqual(self.pb.move_label_text(), "Start position")

    def test_white_move(self):
        self.pb.go_to(1)
        self.assertEqual(self.pb.move_label_text(), "1. e4    (1/2)")

    def test_black_move(self):
        self.pb.go_to(2)
        # Matches the original format: full-move number, a dot, then the ellipsis.
        self.assertEqual(self.pb.move_label_text(), "1.… e5    (2/2)")


if __name__ == "__main__":
    unittest.main()
