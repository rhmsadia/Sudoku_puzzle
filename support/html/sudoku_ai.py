"""Sudoku solver using constraint satisfaction and backtracking.

This solver models Sudoku as a CSP and supports plain backtracking, propagation,
and heuristics-based search with lightweight statistics and trace output.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

Digits = "123456789"
Rows = "ABCDEFGHI"
Cols = Digits
Squares = [r + c for r in Rows for c in Cols]

Units: Dict[str, List[List[str]]] = {}
Peers: Dict[str, set[str]] = {}

for s in Squares:
    row_units = [[s[0] + c for c in Cols]]
    col_units = [[r + s[1] for r in Rows]]
    block_row = (Rows.index(s[0]) // 3) * 3
    block_col = (Cols.index(s[1]) // 3) * 3
    block_units = [[Rows[r] + Cols[c] for r in range(block_row, block_row + 3) for c in range(block_col, block_col + 3)]]
    Units[s] = row_units + col_units + block_units
    Peers[s] = set(sum(Units[s], [])) - {s}


def normalize_grid(grid: str) -> str:
    """Normalize puzzle input into an 81-character string using 0 for blanks."""
    if not isinstance(grid, str):
        raise ValueError("Puzzle input must be a string.")
    chars = [c for c in grid if c in Digits or c in "0." or c == "*"]
    if len(chars) != 81:
        raise ValueError("Grid must contain 81 cells; use digits, 0, '.', or '*'.")
    return "".join("0" if c in "0.*" else c for c in chars)


def validate_grid(grid: str) -> bool:
    """Check whether a puzzle is structurally consistent before solving."""
    normalized = normalize_grid(grid)
    rows: Dict[str, set[str]] = {row: set() for row in Rows}
    cols: Dict[str, set[str]] = {col: set() for col in Cols}
    blocks: Dict[str, set[str]] = {str(index): set() for index in range(9)}

    for idx, char in enumerate(normalized):
        if char == "0":
            continue
        square = Squares[idx]
        row_label = square[0]
        col_label = square[1]
        block_label = str(((Rows.index(row_label) // 3) * 3) + (Cols.index(col_label) // 3))
        if char in rows[row_label] or char in cols[col_label] or char in blocks[block_label]:
            return False
        rows[row_label].add(char)
        cols[col_label].add(char)
        blocks[block_label].add(char)
    return True


def parse_grid(grid: str) -> Dict[str, str]:
    """Convert a normalized grid into a domain map of {square: digits}."""
    normalized = normalize_grid(grid)
    values = {s: Digits for s in Squares}
    for square, char in zip(Squares, normalized):
        if char == "0":
            continue
        if assign(values, square, char) is None:
            raise ValueError(f"Invalid puzzle or contradiction at cell {square}.")
    return values


def assign(values: Dict[str, str], square: str, digit: str, stats: Optional[Dict[str, Any]] = None, trace: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, str]]:
    """Assign a digit to a square and propagate constraints."""
    if digit not in values[square]:
        return None
    if stats is not None:
        stats["assignments"] += 1
    if trace is not None:
        trace.append({"event": "assign", "square": square, "digit": digit})

    other_values = values[square].replace(digit, "")
    for other_digit in other_values:
        if eliminate(values, square, other_digit, stats, trace) is None:
            return None
    return values


def eliminate(values: Dict[str, str], square: str, digit: str, stats: Optional[Dict[str, Any]] = None, trace: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, str]]:
    """Eliminate a digit from a square's domain and propagate any forced moves."""
    if digit not in values[square]:
        return values
    values[square] = values[square].replace(digit, "")
    if not values[square]:
        return None

    if stats is not None:
        stats["propagations"] += 1
    if trace is not None:
        trace.append({"event": "eliminate", "square": square, "digit": digit})

    if len(values[square]) == 1:
        last_digit = values[square]
        for peer in Peers[square]:
            if eliminate(values, peer, last_digit, stats, trace) is None:
                return None

    for unit in Units[square]:
        places_for_digit = [s for s in unit if digit in values[s]]
        if len(places_for_digit) == 0:
            return None
        if len(places_for_digit) == 1:
            if assign(values, places_for_digit[0], digit, stats, trace) is None:
                return None
    return values


def solved(values: Dict[str, str]) -> bool:
    return all(len(values[s]) == 1 for s in Squares)


def select_unassigned_square(values: Dict[str, str], mode: str) -> Optional[str]:
    """Select the next square with MRV and, for heuristic mode, degree ordering."""
    unassigned = [s for s in Squares if len(values[s]) > 1]
    if not unassigned:
        return None
    if mode == "backtracking":
        return unassigned[0]
    if mode == "propagation":
        return min(unassigned, key=lambda s: (len(values[s]), -len(Peers[s])))
    return min(unassigned, key=lambda s: (len(values[s]), -len(Peers[s])))


def order_values(values: Dict[str, str], square: str, mode: str) -> List[str]:
    """Return candidate digits in an order influenced by the selected solver mode."""
    candidates = [digit for digit in values[square]]
    if mode != "heuristics":
        return candidates

    def lcv_score(digit: str) -> int:
        score = 0
        for peer in Peers[square]:
            if digit in values[peer]:
                score += len(values[peer])
        return score

    return sorted(candidates, key=lambda d: (lcv_score(d), d))


def search(values: Dict[str, str], mode: str, stats: Optional[Dict[str, Any]] = None, trace: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, str]]:
    """Recursively solve the puzzle with propagation and heuristics as requested."""
    if values is None:
        return None
    if solved(values):
        return values

    square = select_unassigned_square(values, mode)
    if square is None:
        return values

    for digit in order_values(values, square, mode):
        new_values = copy.deepcopy(values)
        if assign(new_values, square, digit, stats, trace) is not None:
            result = search(new_values, mode, stats, trace)
            if result is not None:
                return result
        if stats is not None:
            stats["backtracks"] += 1
        if trace is not None:
            trace.append({"event": "backtrack", "square": square, "digit": digit})
    return None


def format_solution(values: Dict[str, str]) -> str:
    width = 1 + max(len(values[s]) for s in Squares)
    line = "+" + "+".join(["-" * (width * 3)] * 3) + "+"
    output_lines: List[str] = []
    for r in Rows:
        row_values = []
        for c in Cols:
            row_values.append(values[r + c].center(width))
            if c in "36":
                row_values.append("|")
        output_lines.append("|" + "".join(row_values) + "|")
        if r in "CF":
            output_lines.append(line)
    return "\n".join([line] + output_lines + [line])


def solve_sudoku(grid: str, mode: str = "heuristics") -> Dict[str, str]:
    """Solve a Sudoku puzzle from a string representation."""
    result = solve_sudoku_with_stats(grid, mode=mode)
    return result["solution"]


def solve_sudoku_with_stats(grid: str, mode: str = "heuristics", trace: bool = False) -> Dict[str, Any]:
    """Solve a Sudoku puzzle and return the solution plus solving stats and optional trace."""
    if mode not in {"backtracking", "propagation", "heuristics"}:
        raise ValueError("Mode must be 'backtracking', 'propagation', or 'heuristics'.")

    if not validate_grid(grid):
        raise ValueError("The supplied grid is invalid because it violates Sudoku constraints.")

    start = time.perf_counter()
    stats: Dict[str, Any] = {"mode": mode, "assignments": 0, "propagations": 0, "backtracks": 0, "solved": False, "time_ms": 0.0}
    steps: List[Dict[str, Any]] = [] if trace else []
    values = parse_grid(grid)
    solution = search(values, mode, stats, steps if trace else None)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    stats["time_ms"] = round(elapsed_ms, 3)
    stats["solved"] = solution is not None
    if solution is None:
        raise ValueError("No solution exists for the given Sudoku puzzle.")
    return {"solution": solution, "stats": stats, "steps": steps}


def compare_solve_modes(grid: str) -> List[Dict[str, Any]]:
    """Run the same puzzle through the three solver variants."""
    return [solve_sudoku_with_stats(grid, mode=mode, trace=False) for mode in ("backtracking", "propagation", "heuristics")]


def get_hint(grid: str, square: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return a single correct move for the current puzzle."""
    if not validate_grid(grid):
        raise ValueError("The supplied grid is invalid because it violates Sudoku constraints.")

    solution = solve_sudoku(grid)
    if square is not None:
        if square not in Squares:
            raise ValueError("Target square is invalid.")
        return {"square": square, "digit": solution[square]}

    values = parse_grid(grid)
    for square_name in Squares:
        if len(values[square_name]) > 1:
            for digit in values[square_name]:
                test_values = copy.deepcopy(values)
                if assign(test_values, square_name, digit) is not None:
                    return {"square": square_name, "digit": digit}

    for square_name in Squares:
        if grid[Squares.index(square_name)] == "0":
            return {"square": square_name, "digit": solution[square_name]}
    return {"square": Squares[0], "digit": solution[Squares[0]]}


def generate_puzzle(difficulty: str = "easy") -> str:
    """Create a playable puzzle string by removing givens from a solved board."""
    solved_grid = (
        "534678912"
        "672195348"
        "198342567"
        "859761423"
        "426853791"
        "713924856"
        "961537284"
        "287419635"
        "345286179"
    )
    difficulty_targets = {"easy": 40, "medium": 32, "hard": 24, "expert": 18, "evil": 14}
    target = difficulty_targets.get(difficulty.lower(), difficulty_targets["easy"])
    board = list(solved_grid)
    for index in range(81):
        if len([cell for cell in board if cell != "0"]) <= target:
            break
        if index % 2 == 0:
            board[index] = "0"
    puzzle = "".join(board)
    if not validate_grid(puzzle):
        return generate_puzzle(difficulty)
    return puzzle


def read_puzzle_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return normalize_grid(text)


# Kaggle dataset cache
_kaggle_puzzles_cache: Dict[str, List[str]] = {}


def load_kaggle_puzzles(difficulty: str = "easy", limit: Optional[int] = 100) -> List[str]:
    """Load Sudoku puzzles from Kaggle dataset with optional difficulty filter.
    
    This uses the 'radcliffe/3-million-sudoku-puzzles-with-ratings' dataset.
    On first call, it downloads ~207MB and caches locally in ~/.cache/kagglehub/
    
    Args:
        difficulty: Difficulty level ('easy', 'medium', 'hard', 'expert', 'evil')
        limit: Maximum puzzles to load (None = load all)
    
    Returns:
        List of 81-character puzzle strings
    """
    cache_key = f"{difficulty}_{limit}"
    if cache_key in _kaggle_puzzles_cache:
        return _kaggle_puzzles_cache[cache_key]
    
    try:
        from kaggle_loader import load_puzzles_by_difficulty, get_dataset_path
    except ImportError:
        print("Note: kaggle_loader module not found. Run: pip install kagglehub pandas")
        return []
    
    try:
        dataset_path = get_dataset_path()
        if not dataset_path:
            return []
        
        puzzles = load_puzzles_by_difficulty(dataset_path, difficulty)
        if limit and len(puzzles) > limit:
            puzzles = puzzles[:limit]
        
        _kaggle_puzzles_cache[cache_key] = puzzles
        return puzzles
    except Exception as e:
        print(f"Error loading Kaggle puzzles: {e}")
        return []


def launch_web_app(host: str = "", port: int = 8000) -> None:
    ui_path = Path(__file__).resolve().parent / "sudoku_ui.html"
    if not ui_path.exists():
        raise FileNotFoundError("UI file sudoku_ui.html not found.")
    ui_html = ui_path.read_text(encoding="utf-8")

    class SudokuRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html", "/sudoku_ui.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(ui_html.encode("utf-8"))
            else:
                self.send_error(404, "Not Found")

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body)
                if self.path == "/solve":
                    puzzle = payload.get("puzzle", "")
                    mode = payload.get("mode", "heuristics")
                    result = solve_sudoku_with_stats(puzzle, mode=mode, trace=True)
                    payload_response = {
                        "solution": "".join(result["solution"][s] for s in Squares),
                        "stats": result["stats"],
                        "steps": result["steps"],
                    }
                elif self.path == "/compare":
                    puzzle = payload.get("puzzle", "")
                    payload_response = {"results": compare_solve_modes(puzzle)}
                elif self.path == "/validate":
                    puzzle = payload.get("puzzle", "")
                    payload_response = {"valid": validate_grid(puzzle)}
                elif self.path == "/hint":
                    puzzle = payload.get("puzzle", "")
                    square = payload.get("square")
                    payload_response = {"hint": get_hint(puzzle, square)}
                elif self.path == "/generate":
                    difficulty = payload.get("difficulty", "easy")
                    payload_response = {"puzzle": generate_puzzle(difficulty)}
                elif self.path == "/kaggle-puzzle":
                    # New endpoint: Load puzzle from Kaggle dataset
                    difficulty = payload.get("difficulty", "easy")
                    puzzles = load_kaggle_puzzles(difficulty, limit=1)
                    if puzzles:
                        payload_response = {"puzzle": puzzles[0], "source": "kaggle"}
                    else:
                        raise ValueError("Could not load puzzle from Kaggle dataset. Ensure kagglehub and credentials are set up.")
                else:
                    self.send_error(404, "Not Found")
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload_response).encode("utf-8"))
            except Exception as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    server_address = (host, port)
    address_string = f"http://{host or 'localhost'}:{port}"
    print(f"Launching Sudoku game UI at {address_string}")
    webbrowser.open(address_string)
    httpd = HTTPServer(server_address, SudokuRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down web app.")
        httpd.server_close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sudoku AI Solver using constraint satisfaction and backtracking."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Path to a text file containing an 81-character Sudoku puzzle.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch a simple web-based Sudoku interface.",
    )
    parser.add_argument(
        "--host",
        default="",
        help="Host address for the web UI (default: localhost).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the web UI (default: 8000).",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.gui:
        launch_web_app(host=args.host, port=args.port)
        return

    if args.file:
        puzzle = read_puzzle_file(args.file)
    else:
        puzzle = (
            "530070000"
            "600195000"
            "098000060"
            "800060003"
            "400803001"
            "700020006"
            "060000280"
            "000419005"
            "000080079"
        )

    print("Sudoku AI Solver (CSE 440 Project)")
    print("Input puzzle:\n")
    print(format_solution(parse_grid(puzzle)))
    solution = solve_sudoku(puzzle)
    print("Solution:\n")
    print(format_solution(solution))


if __name__ == "__main__":
    main()
