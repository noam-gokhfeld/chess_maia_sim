import unittest
import chess
import game


class DummyEngine:
    def __init__(self):
        self.calls = []

    async def configure(self, config):
        self.calls.append(config)


class ConfigureEngineForTurnTests(unittest.IsolatedAsyncioTestCase):
    async def test_configures_for_white_turn(self):
        engine = DummyEngine()
        board = chess.Board()

        await game.configure_engine_for_turn(
            engine,
            board,
            1600,
            1500,
            game.PlayingStyles.STRATEGIC,
            game.PlayingStyles.MECHANICAL,
        )

        self.assertEqual(engine.calls[-1]["SelfElo"], 1600)
        self.assertEqual(engine.calls[-1]["OppoElo"], 1500)
        self.assertEqual(engine.calls[-1]["Temperature"], 0.8)
        self.assertEqual(engine.calls[-1]["TopP"], 0.5)

    async def test_configures_for_black_turn(self):
        engine = DummyEngine()
        board = chess.Board()
        board.push_san("e4")

        await game.configure_engine_for_turn(
            engine,
            board,
            1600,
            1500,
            game.PlayingStyles.STRATEGIC,
            game.PlayingStyles.MECHANICAL,
        )

        self.assertEqual(engine.calls[-1]["SelfElo"], 1500)
        self.assertEqual(engine.calls[-1]["OppoElo"], 1600)
        self.assertEqual(engine.calls[-1]["Temperature"], 0.3)
        self.assertEqual(engine.calls[-1]["TopP"], 0.4)


if __name__ == "__main__":
    unittest.main()
