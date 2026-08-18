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
    "Easy": 1000,
    "Medium": 2000,
    "Hard": 3000,
}

# Extra points for each second still on the clock at the end.
TIME_BONUS_PER_SECOND = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3,
}

MISTAKE_PENALTY = 50
HINT_PENALTY = 75
COMPLETION_BONUS = 250


def calculate_score(difficulty, time_left, mistakes, hints_used, completed=False):
    """
    Calculate the player's score.

    During play (completed=False):
        level base - mistake penalty - hint penalty

    After solving (completed=True):
        that value + leftover-time bonus + completion bonus
    """
    score = BASE_SCORE.get(difficulty, BASE_SCORE["Easy"])
    score -= mistakes * MISTAKE_PENALTY
    score -= hints_used * HINT_PENALTY

    if completed:
        per_second = TIME_BONUS_PER_SECOND.get(difficulty, 1)
        score += max(0, time_left) * per_second
        score += COMPLETION_BONUS

    if score < 0:
        score = 0

    return score
