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

# Import the function that finds all valid numbers for a selected cell.
from sudoku_solver import get_possible_numbers


def format_candidates(candidates):
    """Turn a list of numbers into text such as '2, 6, 9'."""
    # If there are no candidates, return "None".
    if not candidates:
        return "None"

    # Convert each candidate number to text and join them with commas.
    return ", ".join(str(number) for number in candidates)


def recommend_number(candidates, solution=None, row=None, col=None):
    """
    Choose one candidate to recommend.

    If the AI solution is available, recommend the true value for that cell.
    That way the hint never suggests a number that the game would mark wrong.
    If there is only one candidate, that number is the recommendation.
    """
    # If there are no valid candidates, return None.
    if not candidates:
        return None

    # Check whether the correct solution and cell position are available.
    if solution is not None and row is not None and col is not None:
        # Get the correct answer for the selected cell.
        answer = solution[row][col]

        # If the correct answer is one of the valid candidates, recommend it.
        if answer in candidates:
            return answer

    # Fallback: the first legal candidate.
    return candidates[0]


def explain_recommendation(number, row, col):
    """Build a short beginner-friendly explanation for the recommended number."""
    # Convert the zero-based row number into a normal row number.
    display_row = row + 1

    # Convert the zero-based column number into a normal column number.
    display_col = col + 1

    # Return an explanation showing why the number is valid.
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
    # Check whether the selected cell already contains a number.
    if board[row][col] != 0:
        return None

    # Find all valid candidate numbers for the selected cell.
    candidates = get_possible_numbers(board, row, col)

    # Choose one number to recommend to the player.
    recommendation = recommend_number(candidates, solution, row, col)

    # If there is no valid recommendation, explain that the cell has a problem.
    if recommendation is None:
        explanation = (
            "There are no valid numbers for this cell with the current board. "
            "A previous entry may be incorrect."
        )
    else:
        # Create an explanation for why the recommended number is valid.
        explanation = explain_recommendation(recommendation, row, col)

    # Store all hint information in a dictionary.
    hint = {
        "row": row,
        "col": col,
        "candidates": candidates,
        "recommendation": recommendation,
        "explanation": explanation,
    }

    # Create the final message that will be displayed to the player.
    hint["message"] = format_hint_message(hint)

    # Return the complete hint information.
    return hint


def format_hint_message(hint):
    """Create the text shown in the AI Hint popup."""
    # Convert the zero-based row number to a normal row number.
    row = hint["row"] + 1

    # Convert the zero-based column number to a normal column number.
    col = hint["col"] + 1

    # Convert the candidate numbers into readable text.
    candidates_text = format_candidates(hint["candidates"])

    # Get the recommended number from the hint dictionary.
    recommendation = hint["recommendation"]

    # Display "None" if there is no recommendation.
    if recommendation is None:
        recommendation_text = "None"
    else:
        # Convert the recommendation number into text.
        recommendation_text = str(recommendation)

    # Build the complete message shown in the AI Hint popup.
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
