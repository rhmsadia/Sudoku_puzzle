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

# Import random to shuffle numbers, rows, columns, and other parts of the board.
import random

# Import helper functions from the Sudoku solver.
from sudoku_solver import copy_board, count_solutions, solve_sudoku


# How many given numbers (clues) to leave on the board.
# Easy keeps more clues. Hard keeps fewer clues.
DEFAULT_CLUES = {
    # Easy puzzles have 40 given numbers.
    "Easy": 40,

    # Medium puzzles have 32 given numbers.
    "Medium": 32,

    # Hard puzzles have 26 given numbers.
    "Hard": 26,
}


def _fill_diagonal_boxes(board):
    """
    Fill the three diagonal 3x3 boxes with shuffled numbers 1-9.

    These boxes do not overlap, so they can be filled independently.
    This gives the solver a valid starting pattern.
    """

    # There are three diagonal boxes starting at rows/columns 0, 3, and 6.
    for box_start in range(0, 9, 3):

        # Create a list containing numbers 1 through 9.
        numbers = list(range(1, 10))

        # Shuffle the numbers so the starting board is different each time.
        random.shuffle(numbers)

        # Keep track of which number should be placed next.
        index = 0

        # Go through the three rows of the current 3x3 box.
        for row in range(box_start, box_start + 3):

            # Go through the three columns of the current 3x3 box.
            for col in range(box_start, box_start + 3):

                # Place the shuffled number into the cell.
                board[row][col] = numbers[index]

                # Move to the next number.
                index += 1


def generate_complete_board():
    """Create one fully filled valid Sudoku board."""

    # Create an empty 9x9 Sudoku board.
    board = [[0 for _ in range(9)] for _ in range(9)]

    # Fill the three diagonal 3x3 boxes first.
    _fill_diagonal_boxes(board)

    # The AI solver fills the remaining empty cells.
    if not solve_sudoku(board):

        # Very unlikely, but try again if the pattern cannot be solved.
        return generate_complete_board()

    # Shuffle the completed board while keeping it valid.
    return shuffle_completed_board(board)


def _transpose(board):
    """Turn rows into columns. Used to shuffle columns using row logic."""

    # Transpose the board so columns become rows.
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

    # Make a copy so the original board is not changed.
    board = copy_board(board)

    # Swap rows inside each band (rows 0-2, 3-5, 6-8).
    for band in range(3):

        # Get the three row positions inside the current band.
        rows = [band * 3, band * 3 + 1, band * 3 + 2]

        # Randomly change the order of those rows.
        random.shuffle(rows)

        # Save the shuffled rows.
        band_copy = [board[r][:] for r in rows]

        # Put the shuffled rows back into the board.
        for i in range(3):
            board[band * 3 + i] = band_copy[i]

    # Swap the three bands.
    bands = [0, 1, 2]

    # Randomly change the order of the bands.
    random.shuffle(bands)

    # Create a new board using the shuffled bands.
    new_rows = []

    # Add each band in its new random order.
    for band in bands:
        new_rows.extend(board[band * 3:band * 3 + 3])

    # Replace the old board with the shuffled version.
    board = new_rows

    # Shuffle columns by transposing, shuffling rows, then transposing back.
    board = _transpose(board)

    # Shuffle rows inside each 3-column stack.
    for band in range(3):

        # Get the three positions inside the current stack.
        rows = [band * 3, band * 3 + 1, band * 3 + 2]

        # Randomly change their order.
        random.shuffle(rows)

        # Save the shuffled rows.
        band_copy = [board[r][:] for r in rows]

        # Put the shuffled rows back.
        for i in range(3):
            board[band * 3 + i] = band_copy[i]

    # Shuffle the three stacks.
    bands = [0, 1, 2]

    # Randomly change their order.
    random.shuffle(bands)

    # Create a new board using the shuffled stacks.
    new_rows = []

    # Add each stack in its new random order.
    for band in bands:
        new_rows.extend(board[band * 3:band * 3 + 3])

    # Transpose the board back so rows and columns return to normal.
    board = _transpose(new_rows)

    # Relabel digits so the same pattern still looks like a new puzzle.
    digits = list(range(1, 10))

    # Make a copy of the digits for shuffling.
    shuffled = digits[:]

    # Randomly shuffle the digit labels.
    random.shuffle(shuffled)

    # Create a mapping from each original digit to a new digit.
    mapping = {digits[i]: shuffled[i] for i in range(9)}

    # Apply the new digit mapping to every cell.
    for row in range(9):
        for col in range(9):
            board[row][col] = mapping[board[row][col]]

    # Return the shuffled but still valid Sudoku board.
    return board


def _remove_clues(complete_board, clue_count):
    """
    Remove numbers from a completed board until about `clue_count` remain.

    A cell is only removed if the puzzle still has exactly one solution.
    If uniqueness cannot be kept for a cell, that number stays.
    """

    # Copy the completed board so the solution is not changed.
    puzzle = copy_board(complete_board)

    # Create a list containing every cell position.
    positions = [(row, col) for row in range(9) for col in range(9)]

    # Randomize the order in which cells will be removed.
    random.shuffle(positions)

    # Calculate how many numbers need to be removed.
    removed_target = 81 - clue_count

    # Keep track of how many numbers have been removed.
    removed = 0

    # Try removing cells in the randomized order.
    for row, col in positions:

        # Stop once the required number of cells has been removed.
        if removed >= removed_target:
            break

        # Save the original number in case it needs to be restored.
        saved = puzzle[row][col]

        # Temporarily remove the number.
        puzzle[row][col] = 0

        # Keep the empty cell only if the puzzle still has one unique solution.
        if count_solutions(puzzle, limit=2) == 1:
            removed += 1
        else:
            # Restore the number if removing it creates multiple solutions.
            puzzle[row][col] = saved

    # Return the generated puzzle.
    return puzzle


def generate_puzzle(difficulty="Medium", clue_count=None, previous_puzzle=None):
    """
    Generate a new Sudoku puzzle and its unique solution.

    Returns (puzzle, solution).
    Empty cells in the puzzle are stored as 0.

    If `previous_puzzle` is given, try a few times to make a different one.
    """

    # If a clue count was not provided, use the default for the selected difficulty.
    if clue_count is None:
        clue_count = DEFAULT_CLUES.get(difficulty, DEFAULT_CLUES["Medium"])

    # These variables will store the generated puzzle and its solution.
    puzzle = None
    solution = None

    # Try a few times so timeout / New Game usually gets a different board.
    for _ in range(8):

        # Generate a complete valid Sudoku solution.
        solution = generate_complete_board()

        # Remove numbers from the solution to create the puzzle.
        puzzle = _remove_clues(solution, clue_count)

        # Stop if there is no previous puzzle or the new puzzle is different.
        if previous_puzzle is None or puzzle != previous_puzzle:
            break

    # Return both the playable puzzle and its complete solution.
    return puzzle, solution
