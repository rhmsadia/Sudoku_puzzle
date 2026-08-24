"""
Sudoku Puzzle
=============
Start the game with:

    python3 main.py
"""

# Import os to work with file and folder paths.
import os

# Import sys to access and modify Python's module search path.
import sys

# Import tkinter to create the main application window.
import tkinter as tk


# Always load the other game files from this folder,
# even if you run the command from a different directory.
# Get the absolute path of the folder containing this file.
GAME_FOLDER = os.path.dirname(os.path.abspath(__file__))

# Add the game folder to Python's module search path if it is not already there.
if GAME_FOLDER not in sys.path:
    sys.path.insert(0, GAME_FOLDER)

# Change the current working directory to the game folder.
os.chdir(GAME_FOLDER)

# Import the SudokuGame class that controls the main game.
from game import SudokuGame


def main():
    # Create the main Tkinter application window.
    root = tk.Tk()

    # Create the Sudoku game inside the main window.
    SudokuGame(root)

    # Start Tkinter's event loop so the window can respond to user actions.
    root.mainloop()


# Run the main function only when this file is executed directly.
# This prevents the game from starting automatically if main.py is imported.
if __name__ == "__main__":
    main()
