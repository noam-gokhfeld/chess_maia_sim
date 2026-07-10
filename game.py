import asyncio
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
    CUSTOM = (float(input("Enter the temperature for the custom playing style (0.0 to 1.0): ")), float(input("Enter the top-p for the custom playing style (0.0 to 1.0): ")))
    SOLID = (0.3, 0.80) # rigorous consistency and zero risk, temp=0.3, topp=0.80
    NATURALL = (0.75, 0.95) # natural play, temp=0.75, topp=0.95
    AGRESSIVE = (1.10, 0.98) #creative and chaos friendly, temp=1.10, topp=0.98
    BLUNDERING = (0.60, 1.00) # embraces mistakes for learning, temp=0.60, topp=1.00
    BULLET = (0.90, 0.90) # fast-paced, temp=0.90, topp=0.90
    ARGMAX = (0.0, 1.0) # deterministic play, always choosing the best move, temp=0.0, topp=1.0

    def __init__(self, temperature : float, topp: float):
        self.temperature = temperature
        self.topp = topp





async def setup_maia_engine(engine_model: MaiaEngineModel, elo=1500, temperature: float = 0.0, topp: float = 1.0):
    try:
        seed = str(random.randint(1, 999999))
        transport, engine = await chess.engine.popen_uci(
            [sys.executable, "-m", "maia3.uci",
             "--model", engine_model.value,
             "--elo", str(elo),
             "--temperature", str(temperature),
             "--top-p", str(topp),
             "--seed", seed]
        )
        return transport, engine
    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()
        return None, None


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
    



async def simulate_game(white_elo, 
                  black_elo, 
                  playing_style_white : PlayingStyles=PlayingStyles.STRATEGIC,
                  playing_style_black : PlayingStyles=PlayingStyles.STRATEGIC,
                  engine_model: MaiaEngineModel=MaiaEngineModel.MAIA3_5M,
                  fen=chess.STARTING_FEN):
    
    try:
        game, board = setup_game("Simulated Game", f"Maia {white_elo}", f"Maia {black_elo}", fen)
        node = game
        temperature_white, topp_white = playing_style_white.value
        temperature_black, topp_black = playing_style_black.value
        white_maia_engine_transport, white_maia_engine = await setup_maia_engine(engine_model, white_elo, temperature_white, topp_white)
        black_maia_engine_transport, black_maia_engine = await setup_maia_engine(engine_model, black_elo, temperature_black, topp_black)

        if white_maia_engine is None or white_maia_engine_transport is None:
            raise RuntimeError("Maia white engine was not initialized successfully.")
        if black_maia_engine is None or black_maia_engine_transport is None:
            raise RuntimeError("Maia black engine was not initialized successfully.")

        

        while not board.is_game_over():
            if board.turn == chess.WHITE:
                result = await white_maia_engine.play(board, chess.engine.Limit(nodes=1))
            else:
                result = await black_maia_engine.play(board, chess.engine.Limit(nodes=1))

            board.push(result.move)
            node = node.add_main_variation(result.move)
            await asyncio.sleep(0)  # Small delay to allow for async processing

        final_result = board.result()
        game.headers["Result"] = final_result

        await white_maia_engine.quit()
        await black_maia_engine.quit()
        return game

    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()