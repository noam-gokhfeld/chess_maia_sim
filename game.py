import asyncio
import traceback
import chess
import chess.engine
import chess.pgn
from enum import Enum
from datetime import date
import sys

class MaiaEngineModel(Enum):
    MAIA3_5M = "maia3-5m"
    MAIA3_23M = "maia3-23m"
    MAIA3_79M = "maia3-79m"

class PlayingStyles(Enum):
    DISCIPLINED_GM = 1 # rigorous consistency and zero risk, temp=0.3, topp=0.9
    MECHANICAL = 2 # maximum determinism, minimal randomness, temp=0.3, topp=0.4
    CREATIVE = 3 # exploratory play with higher randomness, temp=0.8, topp=0.9
    STRATEGIC = 4 # balanced approach with moderate randomness, temp=0.8, topp=0.5


print("creating game, board, and node objects...")
game = chess.pgn.Game()
board = chess.Board()
node = game

async def setup_maia_engine(engine_model: MaiaEngineModel):
    try:
        transport, engine = await chess.engine.popen_uci(
            [sys.executable, "-m", "maia3.uci", "--model", engine_model.value]
        )
        return engine
    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()
        return None

async def setup_engines():
    print("setting white Maia engine...")
    global maia_engine_white, maia_engine_black
    maia_engine_white = await setup_maia_engine(MaiaEngineModel.MAIA3_5M)
    if maia_engine_white is None:
        raise RuntimeError("Failed to start the white Maia engine.")

    print("setting black Maia engine...")
    maia_engine_black = await setup_maia_engine(MaiaEngineModel.MAIA3_5M)
    if maia_engine_black is None:
        raise RuntimeError("Failed to start the black Maia engine.")

    print("Maia engines set up successfully.")
    return maia_engine_white, maia_engine_black

def setup_game(event, white, black):
    global game
    game.headers["Event"] = event
    game.headers["White"] = white
    game.headers["Black"] = black
    game.headers["Date"] = date.today().strftime("%Y.%m.%d")
    game.headers["Round"] = "?"
    game.headers["Result"] = "*"
    game.headers["Site"] = "Simulation Program"

def configure_playing_style(playing_style: PlayingStyles):
    if playing_style == PlayingStyles.DISCIPLINED_GM:
        temperature = 0.3
        topp = 0.9
    elif playing_style == PlayingStyles.MECHANICAL:
        temperature = 0.3
        topp = 0.4
    elif playing_style == PlayingStyles.CREATIVE:
        temperature = 0.8
        topp = 0.9
    elif playing_style == PlayingStyles.STRATEGIC:
        temperature = 0.8
        topp = 0.5
    else:
        raise ValueError("Invalid playing style selected.")
    
    return temperature, topp



async def simulate_game(white_elo, 
                  black_elo, 
                  playing_style_white : PlayingStyles=PlayingStyles.STRATEGIC,
                  playing_style_black : PlayingStyles=PlayingStyles.STRATEGIC):
    
    try:
        global board
        global game
        global maia_engine_white
        global maia_engine_black
        global node

        if maia_engine_white is None or maia_engine_black is None:
            raise RuntimeError("Maia engines were not initialized successfully.")

        white_temperature, white_topp = configure_playing_style(playing_style_white)
        black_temperature, black_topp = configure_playing_style(playing_style_black)

        await maia_engine_white.configure({
                "SelfElo": white_elo,
                "OppoElo": black_elo,
                "Temperature": white_temperature,
                "TopP": white_topp,
        })

        await maia_engine_black.configure({
                "SelfElo": black_elo,
                "OppoElo": white_elo,
                "Temperature": black_temperature,
                "TopP": black_topp,
        })

        while not board.is_game_over():
            if board.turn == chess.WHITE:
                result = await maia_engine_white.play(board, chess.engine.Limit(nodes=1))
            else:
                result = await maia_engine_black.play(board, chess.engine.Limit(nodes=1))

            board.push(result.move)
            node = node.add_main_variation(result.move)
            await asyncio.sleep(0.1)  # Small delay to allow for async processing

        final_result = board.result()
        game.headers["Result"] = final_result

        await maia_engine_white.quit()
        await maia_engine_black.quit()

        print(game)

        return game

    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()