"""
Sudoku Puzzle Generator
=======================
Creates a new valid Sudoku puzzle every game.

Steps:
1. Build a completed valid Sudoku board.
2. Shuffle rows, columns, bands, stacks, and digits
   so each game is different.
3. Remove numbers according to the difficulty level.
4. Prefer puzzles that still have exactly one solution.
"""

import random

from sudoku_solver import copy_board, count_solutions, solve_sudoku


# How many given numbers (clues) to leave on the board.
# Easy keeps more clues. Hard keeps fewer clues.
DEFAULT_CLUES = {
    "Easy": 40,
    "Medium": 32,
    "Hard": 26,
}


def _fill_diagonal_boxes(board):
    """
    Fill the three diagonal 3x3 boxes with shuffled numbers 1-9.

    These boxes do not overlap, so they can be filled independently.
    This gives the solver a valid starting pattern.
    """
    for box_start in range(0, 9, 3):
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        index = 0
        for row in range(box_start, box_start + 3):
            for col in range(box_start, box_start + 3):
                board[row][col] = numbers[index]
                index += 1


def generate_complete_board():
    """Create one fully filled valid Sudoku board."""
    board = [[0 for _ in range(9)] for _ in range(9)]
    _fill_diagonal_boxes(board)

    # The AI solver fills the remaining empty cells.
    if not solve_sudoku(board):
        # Very unlikely, but try again if the pattern cannot be solved.
        return generate_complete_board()

    return shuffle_completed_board(board)


def _transpose(board):
    """Turn rows into columns. Used to shuffle columns using row logic."""
    return [list(row) for row in zip(*board)]


def shuffle_completed_board(board):
    """
    Shuffle a completed board without breaking Sudoku rules.

    Allowed shuffles:
    * swap rows inside a 3-row band
    * swap the three bands
    * swap columns inside a 3-column stack
    * swap the three stacks
    * relabel digits (for example all 1s become 7s)
    """
    board = copy_board(board)

    # Swap rows inside each band (rows 0-2, 3-5, 6-8).
    for band in range(3):
        rows = [band * 3, band * 3 + 1, band * 3 + 2]
        random.shuffle(rows)
        band_copy = [board[r][:] for r in rows]
        for i in range(3):
            board[band * 3 + i] = band_copy[i]

    # Swap the three bands.
    bands = [0, 1, 2]
    random.shuffle(bands)
    new_rows = []
    for band in bands:
        new_rows.extend(board[band * 3:band * 3 + 3])
    board = new_rows

    # Shuffle columns by transposing, shuffling rows, then transposing back.
    board = _transpose(board)
    for band in range(3):
        rows = [band * 3, band * 3 + 1, band * 3 + 2]
        random.shuffle(rows)
        band_copy = [board[r][:] for r in rows]
        for i in range(3):
            board[band * 3 + i] = band_copy[i]

    bands = [0, 1, 2]
    random.shuffle(bands)
    new_rows = []
    for band in bands:
        new_rows.extend(board[band * 3:band * 3 + 3])
    board = _transpose(new_rows)

    # Relabel digits so the same pattern still looks like a new puzzle.
    digits = list(range(1, 10))
    shuffled = digits[:]
    random.shuffle(shuffled)
    mapping = {digits[i]: shuffled[i] for i in range(9)}
    for row in range(9):
        for col in range(9):
            board[row][col] = mapping[board[row][col]]

    return board


def _remove_clues(complete_board, clue_count):
    """
    Remove numbers from a completed board until about `clue_count` remain.

    A cell is only removed if the puzzle still has exactly one solution.
    If uniqueness cannot be kept for a cell, that number stays.
    """
    puzzle = copy_board(complete_board)
    positions = [(row, col) for row in range(9) for col in range(9)]
    random.shuffle(positions)

    removed_target = 81 - clue_count
    removed = 0

    for row, col in positions:
        if removed >= removed_target:
            break

        saved = puzzle[row][col]
        puzzle[row][col] = 0

        # Keep the hole only if the AI still finds one unique solution.
        if count_solutions(puzzle, limit=2) == 1:
            removed += 1
        else:
            puzzle[row][col] = saved

    return puzzle


def generate_puzzle(difficulty="Medium", clue_count=None, previous_puzzle=None):
    """
    Generate a new Sudoku puzzle and its unique solution.

    Returns (puzzle, solution).
    Empty cells in the puzzle are stored as 0.

    If `previous_puzzle` is given, try a few times to make a different one.
    """
    if clue_count is None:
        clue_count = DEFAULT_CLUES.get(difficulty, DEFAULT_CLUES["Medium"])

    puzzle = None
    solution = None

    # Try a few times so timeout / New Game usually gets a different board.
    for _ in range(8):
        solution = generate_complete_board()
        puzzle = _remove_clues(solution, clue_count)

        if previous_puzzle is None or puzzle != previous_puzzle:
            break

    return puzzle, solution
