# AI-Based Sudoku Puzzle Game

## Project Description

This is a beginner-friendly Sudoku puzzle game written in Python and Tkinter. The player fills a 9x9 grid following normal Sudoku rules. Behind the scenes, the game uses AI techniques — a **Constraint Satisfaction Problem (CSP)** and **Backtracking** — to generate puzzles, solve them, check answers, and give intelligent hints.

You only need to run `main.py`. All other Python files stay in the same folder so they can import each other.

## Features

* 9x9 Sudoku puzzle with locked original clues
* Three difficulty levels: Easy, Medium, and Hard
* Countdown timer for each level
* Insert numbers with the keyboard or on-screen buttons
* Delete a player-entered number
* Undo recent moves
* Mistake counter (`Mistakes: 0/2`)
* Immediate correct / incorrect feedback (green and red cells)
* AI solver using CSP and Backtracking
* AI Hint button with possible candidates
* AI candidate recommendation and a short explanation
* Score based on difficulty, time, mistakes, and hints
* New shuffled puzzle after the timer reaches `00:00`

## AI Techniques

### Constraint Satisfaction Problem (CSP)

Sudoku is treated as a CSP:

* **Variables** are the empty cells
* **Domains** are the numbers 1 to 9
* **Constraints** are the Sudoku rules: a number cannot repeat in a row, a column, or a 3x3 box

The AI finds the legal candidates for a cell by applying these constraints.

### Backtracking

The solver tries a legal number in an empty cell, then continues to the next cell. If a later cell has no legal number, the AI **backtracks**: it undoes the last choice and tries a different number. This continues until the board is complete or it is clear that the puzzle has no solution.

### Candidate Recommendation

When the player asks for a hint, the AI does **not** solve the whole puzzle on screen. It only looks at one cell, lists the possible numbers, recommends one suitable candidate, and explains why that number is valid.

## Technologies

```text
Python
Tkinter
CSP
Backtracking
```

## How to Run

1. Open the `AI-Sudoku-Game` folder.
2. Run:

```bash
python main.py
```

If your computer uses `python3`:

```bash
python3 main.py
```

No extra libraries are required. Python's built-in Tkinter is enough.

## Project Structure

```text
AI-Sudoku-Game/
│
├── main.py
├── sudoku_generator.py
├── sudoku_solver.py
├── game.py
├── ai_hint.py
├── scoring.py
└── README.md
```

* **main.py** — Starts the application and opens the game window.
* **sudoku_generator.py** — Builds a valid completed board, shuffles it, and removes numbers according to difficulty. It prefers puzzles with one unique solution.
* **sudoku_solver.py** — The AI solver. It uses CSP ideas and backtracking to find empty cells, list possible numbers, validate placements, and solve the puzzle.
* **game.py** — The Tkinter GUI and game controller. It manages the board, user input, timer, mistakes, undo, levels, and completion.
* **ai_hint.py** — Creates AI hints: possible candidates, a recommended number, and a short explanation.
* **scoring.py** — Calculates the score from difficulty, leftover time, mistakes, and hints used.
* **README.md** — This file.

## Difficulty Settings

These values are grouped at the top of `game.py` so they are easy to change:

```text
Easy:   Time = 10 minutes, more given numbers
Medium: Time = 7 minutes,  medium number of clues
Hard:   Time = 5 minutes,  fewer given numbers
```

## How to Play

1. Choose **Easy**, **Medium**, or **Hard**.
2. Click an empty cell. The selected cell is highlighted.
3. Type `1`–`9` or press an on-screen number button.
4. A **green** cell means the number is correct. A **red** cell means it is incorrect.
5. Use **Delete** to clear a number you entered. Original clues cannot be deleted.
6. Use **Undo** to reverse recent moves.
7. Use **AI Hint** if you want possible numbers and a recommended candidate for the selected cell.
8. Finish the board before the timer reaches `00:00`.

After more than 2 mistakes, the game offers an AI assistance popup. The game does not end because of mistakes; the AI is there to help you learn.
