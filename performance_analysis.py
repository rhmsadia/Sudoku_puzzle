"""
Performance Analysis for the AI Sudoku Solver
=============================================
Compares four backtracking strategies on the same puzzles this game uses.

The goal is to measure how search heuristics change two things:

* Nodes  — how many search-tree states the solver visits
* Time   — median wall-clock time to solve one puzzle, in milliseconds

Algorithms
----------
1. Naive Backtracking
   Pick the first empty cell (row-major). Try 1-9 and recurse only when
   the number already satisfies the row, column, and box constraints.

2. Backtracking + Forward Checking
   Same first-empty variable order, but after each assignment reject the
   choice immediately if any neighbouring empty cell has an empty domain.

3. CSP + MRV  (this project's solver)
   Treat Sudoku as a Constraint Satisfaction Problem. Pick the empty
   cell with the fewest remaining legal values (Minimum Remaining
   Values). This is `find_empty_cell` in sudoku_solver.py.

4. CSP + MRV + LCV
   Same variable ordering as the project solver, plus Least Constraining
   Value: try the candidate that rules out the fewest options in
   neighbouring empty cells first.

How to run
----------
    python3 performance_analysis.py

Optional:
    python3 performance_analysis.py --trials 10 --repeats 21

Writes three files next to this script:

    performance_results.csv
    node_comparison.png
    time_comparison.png

matplotlib is required only for this analysis, not for playing the game.
"""

from __future__ import annotations

import argparse
import csv
import gc
import os
import random
import statistics
import sys
import time
from collections import defaultdict

GAME_FOLDER = os.path.dirname(os.path.abspath(__file__))
if GAME_FOLDER not in sys.path:
    sys.path.insert(0, GAME_FOLDER)
os.chdir(GAME_FOLDER)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sudoku_generator import DEFAULT_CLUES, generate_puzzle
from sudoku_solver import (
    boards_equal,
    copy_board,
    find_empty_cell,
    get_possible_numbers,
    is_valid,
)


# Reproducible puzzle stream so the CSV can be regenerated.
RANDOM_SEED = 440

CSV_PATH = os.path.join(GAME_FOLDER, "performance_results.csv")
NODE_GRAPH_PATH = os.path.join(GAME_FOLDER, "node_comparison.png")
TIME_GRAPH_PATH = os.path.join(GAME_FOLDER, "time_comparison.png")

DIFFICULTIES = ("Easy", "Medium", "Hard")

ALGORITHMS = (
    "Naive Backtracking",
    "BT + Forward Checking",
    "CSP + MRV (Project)",
    "CSP + MRV + LCV",
)

ALGORITHM_COLORS = {
    "Naive Backtracking": "#F43F5E",
    "BT + Forward Checking": "#7C3AED",
    "CSP + MRV (Project)": "#2563EB",
    "CSP + MRV + LCV": "#059669",
}


class SearchStats:
    """Counters collected during one solve."""

    def __init__(self):
        self.nodes = 0
        self.assignments = 0
        self.backtracks = 0


def count_empty_cells(board):
    """Count cells that still need a number (stored as 0)."""
    return sum(1 for row in board for value in row if value == 0)


def find_first_empty(board):
    """Naive variable ordering: first empty cell in row-major order."""
    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                return (row, col)
    return None


def empty_peers(row, col, board):
    """Empty cells that share a row, column, or 3x3 box with (row, col)."""
    peers = []
    box_row = (row // 3) * 3
    box_col = (col // 3) * 3
    seen = {(row, col)}

    for c in range(9):
        if (row, c) not in seen and board[row][c] == 0:
            peers.append((row, c))
            seen.add((row, c))
    for r in range(9):
        if (r, col) not in seen and board[r][col] == 0:
            peers.append((r, col))
            seen.add((r, col))
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            if (r, c) not in seen and board[r][c] == 0:
                peers.append((r, c))
                seen.add((r, c))
    return peers


def forward_check_ok(board, row, col):
    """
    Return False if the latest assignment emptied a neighbour's domain.

    This is forward checking: after placing a value, every remaining
    neighbour must still have at least one legal number.
    """
    for peer_row, peer_col in empty_peers(row, col, board):
        if not get_possible_numbers(board, peer_row, peer_col):
            return False
    return True


def least_constraining_order(board, row, col, candidates):
    """
    Sort candidates by the LCV heuristic.

    Score = how many neighbouring empty cells currently allow this number.
    A lower score means the value rules out fewer neighbour options.
    """

    def lcv_score(number):
        score = 0
        for peer_row, peer_col in empty_peers(row, col, board):
            if is_valid(board, peer_row, peer_col, number):
                score += 1
        return score

    return sorted(candidates, key=lcv_score)


def _search(board, stats, choose_cell, order_values, use_forward_checking):
    """Shared backtracking search used by every algorithm."""
    stats.nodes += 1
    empty = choose_cell(board)
    if empty is None:
        return True

    row, col = empty
    for number in order_values(board, row, col):
        board[row][col] = number
        stats.assignments += 1
        if use_forward_checking and not forward_check_ok(board, row, col):
            board[row][col] = 0
            stats.backtracks += 1
            continue
        if _search(board, stats, choose_cell, order_values, use_forward_checking):
            return True
        board[row][col] = 0
        stats.backtracks += 1
    return False


def naive_values(board, row, col):
    """Try 1-9, skipping numbers that already break a constraint."""
    return [number for number in range(1, 10) if is_valid(board, row, col, number)]


def domain_values(board, row, col):
    """Try only the CSP domain of the current cell."""
    return get_possible_numbers(board, row, col)


def domain_values_lcv(board, row, col):
    """CSP domain, ordered by Least Constraining Value."""
    return least_constraining_order(board, row, col, get_possible_numbers(board, row, col))


SOLVERS = {
    "Naive Backtracking": (find_first_empty, naive_values, False),
    "BT + Forward Checking": (find_first_empty, domain_values, True),
    "CSP + MRV (Project)": (find_empty_cell, domain_values, False),
    "CSP + MRV + LCV": (find_empty_cell, domain_values_lcv, False),
}


def solve_with_algorithm(puzzle, algorithm_name):
    """
    Solve a copy of `puzzle` with one algorithm.

    Returns (solved_board_or_None, stats, time_seconds).
    """
    choose_cell, order_values, use_fc = SOLVERS[algorithm_name]
    board = copy_board(puzzle)
    stats = SearchStats()
    started = time.perf_counter()
    solved = _search(board, stats, choose_cell, order_values, use_fc)
    elapsed = time.perf_counter() - started
    return (board if solved else None, stats, elapsed)


def median_solve_time(puzzle, algorithm_name, repeats):
    """Run the same solve several times and return the median seconds."""
    samples = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            _board, _stats, elapsed = solve_with_algorithm(puzzle, algorithm_name)
            samples.append(elapsed)
    finally:
        if gc_was_enabled:
            gc.enable()
    return statistics.median(samples)


def generate_trial_puzzles(trials):
    """Build the same set of puzzles every solver will be tested on."""
    puzzles = []
    for difficulty in DIFFICULTIES:
        clue_count = DEFAULT_CLUES[difficulty]
        print(f"Generating {trials} {difficulty} puzzle(s) ({clue_count} clues)...")
        for trial in range(1, trials + 1):
            puzzle, solution = generate_puzzle(
                difficulty=difficulty,
                clue_count=clue_count,
            )
            empty_cells = count_empty_cells(puzzle)
            actual_clues = 81 - empty_cells
            print(
                f"  {difficulty} trial {trial}/{trials}: "
                f"{actual_clues} clues, {empty_cells} empty cells"
            )
            puzzles.append(
                {
                    "trial": trial,
                    "difficulty": difficulty,
                    "clues": actual_clues,
                    "empty_cells": empty_cells,
                    "puzzle": puzzle,
                    "solution": solution,
                }
            )
    return puzzles


def run_benchmark(puzzles, repeats):
    """Solve every puzzle with every algorithm and return CSV rows."""
    rows = []
    total = len(puzzles) * len(ALGORITHMS)
    done = 0

    for item in puzzles:
        for algorithm_name in ALGORITHMS:
            done += 1
            board, stats, _first_elapsed = solve_with_algorithm(
                item["puzzle"], algorithm_name
            )
            median_s = median_solve_time(item["puzzle"], algorithm_name, repeats)
            solved = board is not None and boards_equal(board, item["solution"])
            time_ms = median_s * 1000.0
            print(
                f"  [{done}/{total}] {item['difficulty']} t{item['trial']} "
                f"{algorithm_name}: nodes={stats.nodes}, "
                f"time={time_ms:.3f} ms, solved={solved}"
            )
            rows.append(
                {
                    "seed": RANDOM_SEED,
                    "trial": item["trial"],
                    "difficulty": item["difficulty"],
                    "clues": item["clues"],
                    "empty_cells": item["empty_cells"],
                    "algorithm": algorithm_name,
                    "solved": "yes" if solved else "no",
                    "time_repeats": repeats,
                    "time_ms": round(time_ms, 6),
                    "time_s": round(median_s, 9),
                    "nodes": stats.nodes,
                    "assignments": stats.assignments,
                    "backtracks": stats.backtracks,
                }
            )
    return rows


def write_csv(rows, path):
    """Write one row per (puzzle, algorithm) measurement."""
    fieldnames = [
        "seed",
        "trial",
        "difficulty",
        "clues",
        "empty_cells",
        "algorithm",
        "solved",
        "time_repeats",
        "time_ms",
        "time_s",
        "nodes",
        "assignments",
        "backtracks",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}")


def load_csv(path):
    """Read a previously written results CSV with numeric fields restored."""
    int_fields = {
        "seed",
        "trial",
        "clues",
        "empty_cells",
        "time_repeats",
        "nodes",
        "assignments",
        "backtracks",
    }
    float_fields = {"time_ms", "time_s"}
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in int_fields:
            row[key] = int(row[key])
        for key in float_fields:
            row[key] = float(row[key])
    return rows


def grouped_values(rows, metric):
    """Map (difficulty, algorithm) -> list of metric values."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row["difficulty"], row["algorithm"])].append(row[metric])
    return groups


def mean_std(values):
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return statistics.mean(values), statistics.stdev(values)


def median_iqr(values):
    """Return (median, lower_error, upper_error) using the 25th–75th percentile."""
    if not values:
        return 0.0, 0.0, 0.0
    median = statistics.median(values)
    if len(values) == 1:
        return float(median), 0.0, 0.0
    if len(values) < 4:
        spread = max(values) - min(values)
        return float(median), spread / 2.0, spread / 2.0
    q1, _q2, q3 = statistics.quantiles(values, n=4)
    return float(median), max(0.0, median - q1), max(0.0, q3 - median)


def style_axes(ax):
    ax.set_facecolor("#F8FAFC")
    ax.grid(axis="y", linestyle="--", linewidth=0.7, color="#CBD5E1", alpha=0.9)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94A3B8")
    ax.spines["bottom"].set_color("#94A3B8")


def format_bar_label(value, metric):
    if metric == "nodes":
        if value >= 1000:
            return f"{value:,.0f}"
        return f"{value:.1f}"
    if value >= 100:
        return f"{value:.1f}"
    return f"{value:.2f}"


def draw_grouped_bar_chart(
    rows,
    metric,
    ylabel,
    title,
    output_path,
    log_scale=False,
):
    """Grouped bar chart of algorithm performance by difficulty."""
    groups = grouped_values(rows, metric)
    n_algorithms = len(ALGORITHMS)
    n_difficulties = len(DIFFICULTIES)
    bar_width = 0.18
    x_centers = list(range(n_difficulties))

    fig, ax = plt.subplots(figsize=(11.5, 6.6), dpi=200)
    style_axes(ax)

    all_medians = []
    for index, algorithm in enumerate(ALGORITHMS):
        medians = []
        lower_errors = []
        upper_errors = []
        for difficulty in DIFFICULTIES:
            median_value, lower, upper = median_iqr(groups[(difficulty, algorithm)])
            medians.append(median_value)
            lower_errors.append(lower)
            upper_errors.append(upper)
            all_medians.append(median_value)

        offsets = [
            center + (index - (n_algorithms - 1) / 2) * bar_width
            for center in x_centers
        ]
        bars = ax.bar(
            offsets,
            medians,
            bar_width,
            yerr=[lower_errors, upper_errors],
            capsize=3.5,
            label=algorithm,
            color=ALGORITHM_COLORS[algorithm],
            edgecolor="white",
            linewidth=0.6,
            error_kw={"ecolor": "#334155", "elinewidth": 0.9, "alpha": 0.8},
        )

        for bar, median_value in zip(bars, medians):
            ax.annotate(
                format_bar_label(median_value, metric),
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
                color="#0F172A",
            )

    ax.set_xticks(x_centers)
    ax.set_xticklabels(DIFFICULTIES)
    ax.set_xlabel("Difficulty (game clue counts: Easy 40, Medium 32, Hard 26)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log_scale:
        ax.set_yscale("log")
        positive = [value for value in all_medians if value > 0]
        if positive:
            bottom = min(positive) * 0.45
            if metric == "nodes":
                bottom = max(1.0, bottom)
            else:
                bottom = max(0.05, bottom)
            ax.set_ylim(bottom=bottom)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {output_path}")


def print_summary(rows):
    """Print average nodes and time so the report numbers are easy to copy."""
    groups_nodes = grouped_values(rows, "nodes")
    groups_time = grouped_values(rows, "time_ms")
    unsolved = [row for row in rows if row["solved"] != "yes"]

    def print_table(title, groups, digits):
        print(f"\n{title}")
        print(f"{'Algorithm':<28} {'Easy':>22} {'Medium':>22} {'Hard':>22}")
        for algorithm in ALGORITHMS:
            cells = []
            for difficulty in DIFFICULTIES:
                values = groups[(difficulty, algorithm)]
                mean_value, std_value = mean_std(values)
                median_value, _lo, _hi = median_iqr(values)
                if digits == 1:
                    cells.append(
                        f"{median_value:,.1f} (μ {mean_value:,.1f}±{std_value:,.1f})"
                    )
                else:
                    cells.append(
                        f"{median_value:,.3f} (μ {mean_value:,.3f}±{std_value:,.3f})"
                    )
            print(f"{algorithm:<28} {cells[0]:>22} {cells[1]:>22} {cells[2]:>22}")

    print_table("Nodes visited  [median (mean ± std)]", groups_nodes, digits=1)
    print_table("Solve time ms  [median (mean ± std)]", groups_time, digits=3)

    if unsolved:
        print(f"\nWARNING: {len(unsolved)} run(s) did not match the generated solution.")
    else:
        print("\nAll solver runs matched the generated unique solution.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark Sudoku solvers and write CSV plus comparison graphs."
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=10,
        help="Puzzles generated per difficulty (default: 10).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=21,
        help="Timed repeats per puzzle/algorithm; CSV stores the median (default: 21).",
    )
    parser.add_argument(
        "--plot-only",
        action="store_true",
        help="Rebuild the graphs from an existing performance_results.csv.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.trials < 1:
        raise SystemExit("--trials must be at least 1")
    if args.repeats < 1:
        raise SystemExit("--repeats must be at least 1")

    if args.plot_only:
        if not os.path.exists(CSV_PATH):
            raise SystemExit(f"No CSV found at {CSV_PATH}. Run without --plot-only first.")
        rows = load_csv(CSV_PATH)
        print(f"Loaded {len(rows)} rows from {CSV_PATH}")
    else:
        random.seed(RANDOM_SEED)
        print("CSE440 Sudoku performance analysis")
        print(f"Random seed: {RANDOM_SEED}")
        print(f"Trials per difficulty: {args.trials}")
        print(f"Timed repeats per solve (median kept): {args.repeats}")
        print()

        puzzles = generate_trial_puzzles(args.trials)
        print("\nSolving each puzzle with every algorithm...")
        rows = run_benchmark(puzzles, args.repeats)
        write_csv(rows, CSV_PATH)

    trial_count = len({(row["difficulty"], row["trial"]) for row in rows}) // len(DIFFICULTIES)
    draw_grouped_bar_chart(
        rows,
        metric="nodes",
        ylabel="Median search nodes visited (log scale)",
        title=(
            "Node Comparison of Sudoku Solving Algorithms\n"
            f"Median with 25th–75th percentile over {trial_count} puzzles per difficulty"
        ),
        output_path=NODE_GRAPH_PATH,
        log_scale=True,
    )
    draw_grouped_bar_chart(
        rows,
        metric="time_ms",
        ylabel="Median solve time (milliseconds, log scale)",
        title=(
            "Time Comparison of Sudoku Solving Algorithms\n"
            f"Median with 25th–75th percentile over {trial_count} puzzles per difficulty"
        ),
        output_path=TIME_GRAPH_PATH,
        log_scale=True,
    )
    print_summary(rows)


if __name__ == "__main__":
    main()
