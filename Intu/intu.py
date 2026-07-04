import chess
import chess.engine

# 1. Start the Maia-3 UCI engine process
# You can pass the '--elo' argument directly upon initialization
engine = chess.engine.SimpleEngine.popen_uci([
    "maia3-uci", 
    "--model", "maia3-5m", 
    "--use-uci-history", 
    "--elo", "1500"  # Sets the Elo to 1500
])

# 2. Setup a standard chess board
board = chess.Board()

# 3. Request a move from Maia-3
# Note: Since Maia-3 is a policy-based transformer that outputs human-like moves instantly, 
# you should limit the calculation to 1 node.
result = engine.play(board, limit=chess.engine.Limit(nodes=1))

print("Maia-3 plays:", result.move)

# Always close the engine process when finished
engine.quit()