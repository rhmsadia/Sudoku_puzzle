"""
Scoring System
==============
The score depends on:

* difficulty  (harder level -> higher base score)
* leftover time  (faster finish -> higher score)
* mistakes  (more mistakes -> lower score)
* hints used  (more hints -> lower score)

During the game the header shows the level score only:

    Easy:   1000
    Medium: 2000
    Hard:   3000

Time bonus is added when the puzzle is completed, so the score
does not fall while the timer counts down.
"""

# Points shown for each level while playing.
BASE_SCORE = {
    # Easy starts with 1000 points.
    "Easy": 1000,

    # Medium starts with 2000 points.
    "Medium": 2000,

    # Hard starts with 3000 points.
    "Hard": 3000,
}

# Extra points for each second still on the clock at the end.
TIME_BONUS_PER_SECOND = {
    # Easy gives 1 extra point for each remaining second.
    "Easy": 1,

    # Medium gives 2 extra points for each remaining second.
    "Medium": 2,

    # Hard gives 3 extra points for each remaining second.
    "Hard": 3,
}

# Points deducted for every mistake.
MISTAKE_PENALTY = 50

# Points deducted for every AI hint used.
HINT_PENALTY = 75

# Extra points awarded for successfully completing the puzzle.
COMPLETION_BONUS = 250


def calculate_score(difficulty, time_left, mistakes, hints_used, completed=False):
    """
    Calculate the player's score.

    During play (completed=False):
        level base - mistake penalty - hint penalty

    After solving (completed=True):
        that value + leftover-time bonus + completion bonus
    """

    # Get the starting score for the selected difficulty.
    # If the difficulty is not found, use Easy as the default.
    score = BASE_SCORE.get(difficulty, BASE_SCORE["Easy"])

    # Deduct points based on the number of mistakes.
    score -= mistakes * MISTAKE_PENALTY

    # Deduct points based on the number of AI hints used.
    score -= hints_used * HINT_PENALTY

    # Add the time and completion bonuses only after the puzzle is solved.
    if completed:
        # Get the number of points awarded for each remaining second.
        per_second = TIME_BONUS_PER_SECOND.get(difficulty, 1)

        # Add the leftover-time bonus.
        score += max(0, time_left) * per_second

        # Add the completion bonus.
        score += COMPLETION_BONUS

    # Prevent the score from becoming negative.
    if score < 0:
        score = 0

    # Return the final calculated score.
    return score
