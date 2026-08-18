"""
AI Hint System
==============
Gives the player a small amount of help for one selected cell.

The hint does NOT solve the whole puzzle.
It only looks at one cell and uses CSP constraints to:

1. Find possible candidates (legal numbers).
2. Recommend one suitable number.
3. Explain why that number is valid.
"""

from sudoku_solver import get_possible_numbers


def format_candidates(candidates):
    """Turn a list of numbers into text such as '2, 6, 9'."""
    if not candidates:
        return "None"
    return ", ".join(str(number) for number in candidates)


def recommend_number(candidates, solution=None, row=None, col=None):
    """
    Choose one candidate to recommend.

    If the AI solution is available, recommend the true value for that cell.
    That way the hint never suggests a number that the game would mark wrong.
    If there is only one candidate, that number is the recommendation.
    """
    if not candidates:
        return None

    if solution is not None and row is not None and col is not None:
        answer = solution[row][col]
        if answer in candidates:
            return answer

    # Fallback: the first legal candidate.
    return candidates[0]


def explain_recommendation(number, row, col):
    """Build a short beginner-friendly explanation for the recommended number."""
    display_row = row + 1
    display_col = col + 1
    return (
        f"{number} is a valid candidate because it does not "
        f"appear in row {display_row}, column {display_col}, "
        f"or the 3x3 box that contains this cell."
    )


def get_hint(board, row, col, solution=None):
    """
    Create an AI hint for one cell.

    Returns a dictionary:
    {
        "row": 3,
        "col": 6,
        "candidates": [2, 6, 9],
        "recommendation": 6,
        "explanation": "...",
        "message": "..."   # ready-to-show text
    }

    Returns None if the cell is not empty.
    """
    if board[row][col] != 0:
        return None

    candidates = get_possible_numbers(board, row, col)
    recommendation = recommend_number(candidates, solution, row, col)

    if recommendation is None:
        explanation = (
            "There are no valid numbers for this cell with the current board. "
            "A previous entry may be incorrect."
        )
    else:
        explanation = explain_recommendation(recommendation, row, col)

    hint = {
        "row": row,
        "col": col,
        "candidates": candidates,
        "recommendation": recommendation,
        "explanation": explanation,
    }
    hint["message"] = format_hint_message(hint)
    return hint


def format_hint_message(hint):
    """Create the text shown in the AI Hint popup."""
    row = hint["row"] + 1
    col = hint["col"] + 1
    candidates_text = format_candidates(hint["candidates"])
    recommendation = hint["recommendation"]

    if recommendation is None:
        recommendation_text = "None"
    else:
        recommendation_text = str(recommendation)

    return (
        f"AI Hint\n\n"
        f"Selected Cell\n"
        f"Row: {row}\n"
        f"Column: {col}\n\n"
        f"Possible numbers: {candidates_text}\n\n"
        f"AI Recommendation: {recommendation_text}\n\n"
        f"Why?\n\n"
        f"{hint['explanation']}"
    )
