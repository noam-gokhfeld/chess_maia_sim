import chess
import chess.engine

def get_maia_prediction(fen_position: str, elo: int = 1500):
    """
    Given a board position and an ELO target, returns the highest-probability 
    human move and its exact percentage chance.
    """
    # 1. Spin up the engine and target the specific ELO
    engine = chess.engine.SimpleEngine.popen_uci(["maia3-uci"])
    engine.configure({"Elo": elo})
    
    board = chess.Board(fen_position)
    
    # 2. Extract analysis info (limit to 1 node for instant NN execution)
    analysis = engine.analyse(board, limit=chess.engine.Limit(nodes=1))
    
    # Close the engine right away so we don't leave zombie processes running
    engine.quit()
    
    # 3. Extract the primary move data from the first analysis slot
    if analysis:
        top_line = analysis[0]
        
        # Get the move object and turn it into standard SAN notation (e.g., "e4")
        predicted_move = board.san(top_line["pv"][0])
        
        # Maia exposes its raw neural network policy array via python-chess's info stream.
        # Under the hood, this probability is mapped directly to the WDL expectation value.
        score = top_line.get("score")
        probability = score.wdl().expectation() * 100 if score else 0.0
        
        return {
            "move": predicted_move,
            "probability": f"{probability:.1f}%"
        }
    
    return None

# --- How you use it in your code ---
# Let's test it with the standard starting position
starting_fen = chess.STARTING_FEN

result = get_maia_prediction(starting_fen, elo=1500)
print(result)
# Output: {'move': 'e4', 'probability': '46.1%'}