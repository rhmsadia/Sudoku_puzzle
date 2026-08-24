"""
AI Sudoku Solver
================
This module is the main AI part of the project.

It treats Sudoku as a Constraint Satisfaction Problem (CSP):

* Variables  -> empty cells
* Domains    -> numbers 1 to 9
* Constraints
    - a number cannot repeat in a row
    - a number cannot repeat in a column
    - a number cannot repeat in a 3x3 box

The solver uses backtracking:
it tries a legal number, continues, and goes back if that choice
later breaks a constraint.
"""


def copy_board(board):
    """Return a new copy of a 9x9 board so the original is not changed."""

    # Copy each row so changes to the new board do not affect the original.
    return [row[:] for row in board]


def find_empty_cell(board):
    """
    Find the next empty cell (value 0).

    Uses the MRV idea from CSP: pick the empty cell with the fewest
    possible numbers. This makes backtracking faster.
    Returns (row, col) or None if the board is full.
    """

    # Store the best empty cell found so far.
    best_cell = None

    # Start with 10 because a Sudoku cell can have at most 9 options.
    fewest_options = 10

    # Check every cell in the 9x9 board.
    for row in range(9):
        for col in range(9):

            # Only consider empty cells.
            if board[row][col] == 0:

                # Find all legal numbers for this cell.
                options = get_possible_numbers(board, row, col)

                # Count how many legal numbers are available.
                option_count = len(options)

                # A cell with 0 options cannot be filled. Return it early
                # so backtracking can undo the previous choice.
                if option_count == 0:
                    return (row, col)

                # Choose the cell with the fewest possible numbers.
                if option_count < fewest_options:
                    fewest_options = option_count
                    best_cell = (row, col)

                    # 1 option is already the best we can hope for.
                    if fewest_options == 1:
                        return best_cell

    # Return the best empty cell, or None if the board is full.
    return best_cell


def is_valid(board, row, col, number):
    """
    Check Sudoku constraints for placing `number` at (row, col).

    Returns True only if the number does not already appear in:
    the same row, the same column, or the same 3x3 box.
    """

    # Check the row constraint.
    # If the number already exists in this row, it cannot be placed.
    if number in board[row]:
        return False

    # Check the column constraint.
    for r in range(9):
        if board[r][col] == number:
            return False

    # Find the starting row of the 3x3 box.
    box_row = (row // 3) * 3

    # Find the starting column of the 3x3 box.
    box_col = (col // 3) * 3

    # Check every cell inside the 3x3 box.
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):

            # The number cannot appear anywhere in the same box.
            if board[r][c] == number:
                return False

    # The number does not break any Sudoku constraint.
    return True


def get_possible_numbers(board, row, col):
    """
    Return the domain (legal candidates) for one empty cell.

    This is the CSP domain of the variable at (row, col):
    numbers 1-9 that do not break row, column, or box constraints.
    """

    # A cell that is already filled does not need candidates.
    if board[row][col] != 0:
        return []

    # Store all legal numbers for this cell.
    possible = []

    # Test every Sudoku number from 1 to 9.
    for number in range(1, 10):

        # Add the number if it satisfies all Sudoku constraints.
        if is_valid(board, row, col, number):
            possible.append(number)

    # Return the list of legal candidates.
    return possible


def solve_sudoku(board):
    """
    Solve a Sudoku board in place using CSP + backtracking.

    Returns True if a complete valid solution is found.
    Returns False if the puzzle has no solution.
    """

    # Find the next empty cell using the MRV strategy.
    empty = find_empty_cell(board)

    # No empty cell left means the board is solved.
    if empty is None:
        return True

    # Get the row and column of the selected empty cell.
    row, col = empty

    # Find all legal numbers that can be placed there.
    candidates = get_possible_numbers(board, row, col)

    # Try each possible number one by one.
    for number in candidates:

        # Temporarily place the number in the cell.
        board[row][col] = number

        # Continue solving the board recursively.
        if solve_sudoku(board):
            return True

        # This number did not work, so undo it (backtrack).
        board[row][col] = 0

    # None of the candidates produced a solution.
    return False


def get_solution(puzzle):
    """
    Return a solved copy of the puzzle, or None if it cannot be solved.
    The original puzzle is not modified.
    """

    # Create a separate copy of the puzzle.
    board = copy_board(puzzle)

    # Try to solve the copied board.
    if solve_sudoku(board):
        return board

    # Return None if no solution exists.
    return None


def count_solutions(board, limit=2):
    """
    Count how many solutions a puzzle has, up to `limit`.

    Used by the generator to prefer puzzles with one unique solution.
    Stops early once `limit` solutions are found.
    """

    # Work on a copy so the original board is not changed.
    board = copy_board(board)

    # Use a list so the nested search function can update the count.
    found = [0]

    def search():
        # Stop searching once the requested number of solutions is found.
        if found[0] >= limit:
            return

        # Find the next empty cell.
        empty = find_empty_cell(board)

        # If there are no empty cells, one complete solution was found.
        if empty is None:
            found[0] += 1
            return

        # Get the position of the empty cell.
        row, col = empty

        # Try every legal number in the cell.
        for number in get_possible_numbers(board, row, col):

            # Place the candidate number temporarily.
            board[row][col] = number

            # Continue searching for more solutions.
            search()

            # Remove the number before trying the next candidate.
            board[row][col] = 0

            # Stop early when the limit has been reached.
            if found[0] >= limit:
                return

    # Start the recursive search.
    search()

    # Return the number of solutions found.
    return found[0]


def is_correct_number(solution, row, col, number):
    """Return True if `number` matches the AI solution at (row, col)."""

    # Without a solution, the number cannot be checked.
    if solution is None:
        return False

    # Compare the player's number with the correct solution value.
    return solution[row][col] == number


def boards_equal(board_a, board_b):
    """Return True if two 9x9 boards contain the same numbers."""

    # Compare every cell in both boards.
    for row in range(9):
        for col in range(9):

            # If even one cell is different, the boards are not equal.
            if board_a[row][col] != board_b[row][col]:
                return False

    # Every cell matches.
    return True


def is_board_complete_and_correct(board, solution):
    """Return True if every cell is filled and matches the AI solution."""

    # A board cannot be correct without a valid solution.
    if solution is None:
        return False

    # The boards are complete and correct only when every cell matches.
    return boards_equal(board, solution)
