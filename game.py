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
    DISCIPLINED_GM = "disciplined_gm" # rigorous consistency and zero risk, temp=0.3, topp=0.9
    MECHANICAL = "mechanical" # maximum determinism, minimal randomness, temp=0.3, topp=0.4
    CREATIVE = "creative" # exploratory play with higher randomness, temp=0.8, topp=0.9
    STRATEGIC = "strategic" # balanced approach with moderate randomness, temp=0.8, topp=0.5


print("creating game, board, and node objects...")
game = chess.pgn.Game()
board = chess.Board()
node = game

async def setup_maia_engine(engine_model: MaiaEngineModel):
    try:
        transport, engine = await chess.engine.popen_uci(
            [sys.executable, "-m", "maia3.uci", "--model", engine_model.value]
        )
        return transport, engine
    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()
        return None, None

async def setup_engine():
    print("setting up Maia engine...")
    global maia_engine, maia_engine_transport
    maia_engine_transport, maia_engine = await setup_maia_engine(MaiaEngineModel.MAIA3_5M)
    if maia_engine is None or maia_engine_transport is None:
        raise RuntimeError("Failed to start the Maia engine.")

    print("Maia engine set up successfully.")
    return maia_engine

async def configure_engine_for_turn(engine, board, white_elo, black_elo, playing_style_white, playing_style_black):
    if board.turn == chess.WHITE:
        self_elo = white_elo
        oppo_elo = black_elo
        temperature, topp = configure_playing_style(playing_style_white)
    else:
        self_elo = black_elo
        oppo_elo = white_elo
        temperature, topp = configure_playing_style(playing_style_black)

    await engine.configure({
        "SelfElo": self_elo,
        "OppoElo": oppo_elo,
        "Temperature": temperature,
        "TopP": topp,
    })

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
        global maia_engine
        global maia_engine_transport
        global node

        if maia_engine is None or maia_engine_transport is None:
            raise RuntimeError("Maia engine was not initialized successfully.")

        while not board.is_game_over():
            await configure_engine_for_turn(
                maia_engine,
                board,
                white_elo,
                black_elo,
                playing_style_white,
                playing_style_black,
            )
            result = await maia_engine.play(board, chess.engine.Limit(nodes=1))

            board.push(result.move)
            node = node.add_main_variation(result.move)
            await asyncio.sleep(0.1)  # Small delay to allow for async processing

        final_result = board.result()
        game.headers["Result"] = final_result

        print(game)

        return game

    except Exception as e:
        print(f"WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: {e}")
        traceback.print_exc()