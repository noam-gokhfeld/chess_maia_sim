import chess
import chess.engine
import sys
import traceback
import game
import asyncio

async def create_game(white_elo : int, black_elo : int, playing_style_white : game.PlayingStyles, playing_style_black : game.PlayingStyles):
    try:
        print("setting up Maia engines...")
        await game.setup_engines()
        print("Maia engines set up successfully.")
        print("setting up game headers...")
        game.setup_game("Test Game", f"Maia {white_elo}", f"Maia {black_elo}")
        print("game headers set up successfully.")
        print("simulating game...")
        await game.simulate_game(white_elo=white_elo, black_elo=black_elo, playing_style_white=playing_style_white, playing_style_black=playing_style_black)

    except Exception as e:
        print("WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: ")
        traceback.print_exc()

async def main():
    try:
        print("welcome to the program!")
        while True:
            white_elo = int(input("Enter the ELO rating for the white player: "))
            black_elo = int(input("Enter the ELO rating for the black player: "))
            playing_style_white = game.PlayingStyles(input("Enter the playing style for the white player: "))
            playing_style_black = game.PlayingStyles(input("Enter the playing style for the black player: "))
            print("creating game...")
            await create_game(white_elo, black_elo, playing_style_white, playing_style_black)

    except Exception as e:
        print("WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: ")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())