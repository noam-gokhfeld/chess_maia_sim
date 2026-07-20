"""Entry point for the Maia Chess Game Simulator desktop UI.

Importing ``ui.app`` triggers ``ui/__init__`` first, which runs the Windows
Tcl/Tk bootstrap before customtkinter (and therefore tkinter) is imported.
"""

from ui.app import run

if __name__ == "__main__":
    run()
