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
    DISCIPLINED_GM = "disciplined_gm" # rigorous consistency and zero risk, temp=0.3, topp=1.0
    MECHANICAL = "mechanical" # maximum determinism, minimal randomness, temp=0.3, topp=0.6
    CREATIVE = "creative" # exploratory play with higher randomness, temp=0.8, topp=1.0
    STRATEGIC = "strategic" # balanced approach with moderate randomness, temp=0.8, topp=0.75





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
    game.headers["Event"] = event
    game.headers["White"] = white
    game.headers["Black"] = black
    game.headers["Date"] = date.today().strftime("%Y.%m.%d")
    game.headers["Round"] = "?"
    game.headers["Result"] = "*"
    game.headers["Site"] = "Simulation Program"
    return game, board

def configure_playing_style(playing_style: PlayingStyles):
    if playing_style == PlayingStyles.DISCIPLINED_GM:
        temperature = random.randint(25, 35) / 100.0 
        topp = 1.0
    elif playing_style == PlayingStyles.MECHANICAL:
        temperature = random.randint(25, 35) / 100.0
        topp = 0.6
    elif playing_style == PlayingStyles.CREATIVE:
        temperature = random.randint(75, 85) / 100.0
        topp = 1.0
    elif playing_style == PlayingStyles.STRATEGIC:
        temperature = random.randint(75, 85) / 100.0
        topp = 0.75
    else:
        raise ValueError("Invalid playing style selected.")
    
    return temperature, topp



async def simulate_game(white_elo, 
                  black_elo, 
                  playing_style_white : PlayingStyles=PlayingStyles.STRATEGIC,
                  playing_style_black : PlayingStyles=PlayingStyles.STRATEGIC):
    
    try:
        game, board = setup_game("Simulated Game", f"Maia {white_elo}", f"Maia {black_elo}")
        node = game
        temperature_white, topp_white = configure_playing_style(playing_style_white)
        temperature_black, topp_black = configure_playing_style(playing_style_black)
        white_maia_engine_transport, white_maia_engine = await setup_maia_engine(MaiaEngineModel.MAIA3_5M, white_elo, temperature_white, topp_white)
        black_maia_engine_transport, black_maia_engine = await setup_maia_engine(MaiaEngineModel.MAIA3_5M, black_elo, temperature_black, topp_black)

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
            await asyncio.sleep(0.1)  # Small delay to allow for async processing

        final_result = board.result()
        game.headers["Result"] = final_result

        print(game)

        await white_maia_engine.quit()
        await black_maia_engine.quit()
        return game

    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()