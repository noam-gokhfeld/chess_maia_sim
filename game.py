
import random
import traceback
import chess
import chess.engine
import chess.pgn
from enum import Enum
from datetime import date
import time
import sys

class MaiaEngineModel(Enum):
    MAIA3_5M = "maia3-5m"
    MAIA3_23M = "maia3-23m"
    MAIA3_79M = "maia3-79m"

class PlayingStyles(Enum):
    NOT_USING_PLAYING_STYLE = (0.0, 1.0) # not using playingstyles enum
    SOLID = (0.3, 1.00) # rigorous consistency and zero risk, temp=0.3, topp=1.00
    NATURAL = (0.75, 0.95) # natural play, temp=0.75, topp=0.95
    GAMBITTER = (1.10, 0.98) #creative and chaos friendly, temp=1.10, topp=0.98
    BLUNDERING = (1.20, 1.00) # embraces mistakes for learning, temp=1.20, topp=1.00
    BULLET = (0.95, 0.85) # fast-paced, temp=0.95, topp=0.85

    def __init__(self, temperature : float, topp: float):
        self.temperature = temperature
        self.topp = topp





def setup_maia_engine(engine_model: MaiaEngineModel, elo=1500, temperature: float = 0.0, topp: float = 1.0, path_to_engine: str = None):
    try:
        seed = str(random.randint(1, 999999))
        if path_to_engine is None:
            engine = chess.engine.SimpleEngine.popen_uci(
                [sys.executable, "-m", "maia3.uci",
                "--model", engine_model.value,
                "--elo", str(elo),
                "--temperature", str(temperature),
                "--top-p", str(topp),
                "--seed", seed]
            )
        else:
            engine = chess.engine.SimpleEngine.popen_uci(
                [path_to_engine,
                "--model", engine_model.value,
                "--elo", str(elo),
                "--temperature", str(temperature),
                "--top-p", str(topp),
                "--seed", seed]
            )
        return engine
    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()
        return None


def setup_game(event, white, black, fen=chess.STARTING_FEN):
    game = chess.pgn.Game()
    board = chess.Board(fen)
    game.setup(board)
    game.headers["Event"] = event
    game.headers["White"] = white
    game.headers["Black"] = black
    game.headers["Date"] = date.today().strftime("%Y.%m.%d")
    game.headers["Round"] = "?"
    game.headers["Result"] = "*"
    game.headers["Site"] = "Simulation Program"
    return game, board
    



def simulate_game(white_elo, 
                  black_elo, 
                  playing_style_white : PlayingStyles,
                  playing_style_black : PlayingStyles,
                  custom_temperature_white: float = None,
                  custom_topp_white: float = None,
                  custom_temperature_black: float = None,
                  custom_topp_black: float = None,
                  engine_model: MaiaEngineModel=MaiaEngineModel.MAIA3_5M,
                  fen=chess.STARTING_FEN,
                  path_to_engine: str = None):
    
    try:
        game, board = setup_game("Simulated Game", f"Maia {white_elo}", f"Maia {black_elo}", fen)
        node = game
        if custom_temperature_white is not None and custom_topp_white is not None:
            temperature_white = custom_temperature_white
            topp_white = custom_topp_white
        else:
            temperature_white, topp_white = playing_style_white.value
        if custom_temperature_black is not None and custom_topp_black is not None:
            temperature_black = custom_temperature_black
            topp_black = custom_topp_black
        else:
            temperature_black, topp_black = playing_style_black.value

        white_maia_engine = setup_maia_engine(engine_model, white_elo, temperature_white, topp_white, path_to_engine)
        black_maia_engine = setup_maia_engine(engine_model, black_elo, temperature_black, topp_black, path_to_engine)

        if white_maia_engine is None:
            raise RuntimeError("Maia white engine was not initialized successfully.")
        if black_maia_engine is None:
            raise RuntimeError("Maia black engine was not initialized successfully.")

        

        while not board.is_game_over():
            if board.turn == chess.WHITE:
                result = white_maia_engine.play(board, chess.engine.Limit(nodes=1))
            else:
                result = black_maia_engine.play(board, chess.engine.Limit(nodes=1))

            board.push(result.move)
            node = node.add_main_variation(result.move)

        final_result = board.result()
        game.headers["Result"] = final_result

        white_maia_engine.quit()
        black_maia_engine.quit()
        return game

    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()