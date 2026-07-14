import traceback
import game
import asyncio
import customtkinter as ctk

async def main():
    try:
        print("welcome to the program!")
        print("setting up Maia engine...")
        while True:
            custom_temperature_white = None
            custom_topp_white = None
            custom_temperature_black = None
            custom_topp_black = None
            playing_style_white = game.PlayingStyles.NOT_USING_PLAYING_STYLE
            playing_style_black = game.PlayingStyles.NOT_USING_PLAYING_STYLE
            white_elo = int(input("Enter the ELO rating for the white player: "))
            black_elo = int(input("Enter the ELO rating for the black player: "))
            customconfig_white = bool(input("Do you want to use custom playing styles for the white player? (y/n): ").lower() == 'y')
            customconfig_black = bool(input("Do you want to use custom playing styles for the black player? (y/n): ").lower() == 'y')
            if customconfig_white:
                custom_temperature_white = float(input("Enter the temperature for the white player (0.0 to 1.0): "))
                custom_topp_white = float(input("Enter the top-p for the white player (0.0 to 1.0): "))
            else:
                playing_style_white_str = (input("Enter the playing style for the white player: "))
                if playing_style_white_str.upper() in game.PlayingStyles.__members__:
                    playing_style_white = game.PlayingStyles[playing_style_white_str.upper()]

            if customconfig_black:
                custom_temperature_black = float(input("Enter the temperature for the black player (0.0 to 1.0): "))
                custom_topp_black = float(input("Enter the top-p for the black player (0.0 to 1.0): "))
            else:
                playing_style_black_str = (input("Enter the playing style for the black player: "))
                if playing_style_black_str.upper() in game.PlayingStyles.__members__:
                    playing_style_black = game.PlayingStyles[playing_style_black_str.upper()]

            print("crafting game...")
            game_product = await game.simulate_game(white_elo,
                                                    black_elo,
                                                    playing_style_white,
                                                    playing_style_black,
                                                    custom_temperature_white=custom_temperature_white,
                                                    custom_topp_white=custom_topp_white,
                                                    custom_temperature_black=custom_temperature_black,
                                                    custom_topp_black=custom_topp_black,
                                                    engine_model=game.MaiaEngineModel.MAIA3_5M,
                                                    fen="r1bqkbnr/1pp2ppp/p1p5/4p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5",
                                                    path_to_engine=r"D:\app_projects\chess_maia_sim\.venv\Scripts\maia3-5m.exe")
            print("Game simulation complete!")
            print("Game PGN:")
            print(game_product)

    except Exception as e:
        print("WAAAAAAAHHH THERE IS AN ERROR IN THE CODE: ")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())