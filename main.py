import chess
import chess.engine
import sys
import traceback
import game
import asyncio

async def main():
    try:
        print("setting up Maia engines...")
        await game.setup_engines()
        print("Maia engines set up successfully.")
        print("setting up game headers...")
        game.setup_game("Test Game", "Maia 1500", "Maia 1600")
        print("game headers set up successfully.")
        print("simulating game...")
        await game.simulate_game(white_elo=1500, black_elo=1600, playing_style_white=game.PlayingStyles.CREATIVE, playing_style_black=game.PlayingStyles.CREATIVE)

    except Exception as e:
        print("WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: ")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())