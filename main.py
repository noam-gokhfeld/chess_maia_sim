import chess
import chess.engine
import sys
import traceback
import game
import asyncio

async def main():
    try:
        print("welcome to the program!")
        print("setting up Maia engine...")
        while True:
            white_elo = int(input("Enter the ELO rating for the white player: "))
            black_elo = int(input("Enter the ELO rating for the black player: "))
            playing_style_white = game.PlayingStyles(input("Enter the playing style for the white player: "))
            playing_style_black = game.PlayingStyles(input("Enter the playing style for the black player: "))
            print("crafting game...")
            game_product = await game.simulate_game(white_elo, black_elo, playing_style_white, playing_style_black)

    except Exception as e:
        print("WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: ")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())