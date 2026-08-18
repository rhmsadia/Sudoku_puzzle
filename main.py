"""
Sudoku Puzzle
=============
Start the game with:

    python3 main.py
"""

import os
import sys
import tkinter as tk

# Always load the other game files from this folder,
# even if you run the command from a different directory.
GAME_FOLDER = os.path.dirname(os.path.abspath(__file__))
if GAME_FOLDER not in sys.path:
    sys.path.insert(0, GAME_FOLDER)
os.chdir(GAME_FOLDER)

from game import SudokuGame


def main():
    root = tk.Tk()
    SudokuGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
