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
    return [row[:] for row in board]


def find_empty_cell(board):
    """
    Find the next empty cell (value 0).

    Uses the MRV idea from CSP: pick the empty cell with the fewest
    possible numbers. This makes backtracking faster.
    Returns (row, col) or None if the board is full.
    """
    best_cell = None
    fewest_options = 10

    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                options = get_possible_numbers(board, row, col)
                option_count = len(options)

                # A cell with 0 options cannot be filled. Return it early
                # so backtracking can undo the previous choice.
                if option_count == 0:
                    return (row, col)

                if option_count < fewest_options:
                    fewest_options = option_count
                    best_cell = (row, col)

                    # 1 option is already the best we can hope for.
                    if fewest_options == 1:
                        return best_cell

    return best_cell


def is_valid(board, row, col, number):
    """
    Check Sudoku constraints for placing `number` at (row, col).

    Returns True only if the number does not already appear in:
    the same row, the same column, or the same 3x3 box.
    """
    # Row constraint
    if number in board[row]:
        return False

    # Column constraint
    for r in range(9):
        if board[r][col] == number:
            return False

    # 3x3 box constraint
    box_row = (row // 3) * 3
    box_col = (col // 3) * 3
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            if board[r][c] == number:
                return False

    return True


def get_possible_numbers(board, row, col):
    """
    Return the domain (legal candidates) for one empty cell.

    This is the CSP domain of the variable at (row, col):
    numbers 1-9 that do not break row, column, or box constraints.
    """
    if board[row][col] != 0:
        return []

    possible = []
    for number in range(1, 10):
        if is_valid(board, row, col, number):
            possible.append(number)
    return possible


def solve_sudoku(board):
    """
    Solve a Sudoku board in place using CSP + backtracking.

    Returns True if a complete valid solution is found.
    Returns False if the puzzle has no solution.
    """
    empty = find_empty_cell(board)

    # No empty cell left means the board is solved.
    if empty is None:
        return True

    row, col = empty
    candidates = get_possible_numbers(board, row, col)

    for number in candidates:
        board[row][col] = number

        if solve_sudoku(board):
            return True

        # This number did not work, so undo it (backtrack).
        board[row][col] = 0

    return False


def get_solution(puzzle):
    """
    Return a solved copy of the puzzle, or None if it cannot be solved.
    The original puzzle is not modified.
    """
    board = copy_board(puzzle)
    if solve_sudoku(board):
        return board
    return None


def count_solutions(board, limit=2):
    """
    Count how many solutions a puzzle has, up to `limit`.

    Used by the generator to prefer puzzles with one unique solution.
    Stops early once `limit` solutions are found.
    """
    board = copy_board(board)
    found = [0]

    def search():
        if found[0] >= limit:
            return

        empty = find_empty_cell(board)
        if empty is None:
            found[0] += 1
            return

        row, col = empty
        for number in get_possible_numbers(board, row, col):
            board[row][col] = number
            search()
            board[row][col] = 0
            if found[0] >= limit:
                return

    search()
    return found[0]


def is_correct_number(solution, row, col, number):
    """Return True if `number` matches the AI solution at (row, col)."""
    if solution is None:
        return False
    return solution[row][col] == number


def boards_equal(board_a, board_b):
    """Return True if two 9x9 boards contain the same numbers."""
    for row in range(9):
        for col in range(9):
            if board_a[row][col] != board_b[row][col]:
                return False
    return True


def is_board_complete_and_correct(board, solution):
    """Return True if every cell is filled and matches the AI solution."""
    if solution is None:
        return False
    return boards_equal(board, solution)
