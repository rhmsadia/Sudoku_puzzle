"""
Sudoku Game GUI
===============
This file controls the playable game:

* 9x9 board and user input
* timer, mistakes, undo, levels
* visual feedback (green / red)
* AI hints and game completion

The AI solver itself lives in sudoku_solver.py.
This file only calls it.
"""

import tkinter as tk
from tkinter import messagebox

from ai_hint import get_hint
from scoring import calculate_score
from sudoku_generator import generate_puzzle
from sudoku_solver import is_board_complete_and_correct, is_correct_number


# ============================================================
# GAME SETTINGS  (edit these values to customize the game)
# ============================================================
# Easy:   more given numbers, 10 minutes
# Medium: fewer given numbers, 7 minutes
# Hard:   fewest given numbers, 5 minutes
DIFFICULTY_SETTINGS = {
    "Easy": {
        "time_seconds": 10 * 60,
        "clues": 40,
    },
    "Medium": {
        "time_seconds": 7 * 60,
        "clues": 32,
    },
    "Hard": {
        "time_seconds": 5 * 60,
        "clues": 26,
    },
}

# Give one AI hint after every 2 mistakes, up to 3 hints total.
MISTAKES_PER_AI_HINT = 2
MAX_AI_HINTS = 3

DEFAULT_DIFFICULTY = "Easy"

# ============================================================
# VISUAL DESIGN
# ============================================================
FONT = "Helvetica Neue"

COLORS = {
    "bg": "#0B1220",
    "header": "#0F172A",
    "surface": "#121A2B",
    "card": "#182338",
    "text": "#F1F5F9",
    "muted": "#8B9BB4",
    "accent": "#3B82F6",
    "accent_deep": "#1D4ED8",
    "good": "#10B981",
    "bad": "#F43F5E",
    "board_frame": "#E8EEF7",
    "cell": "#FFFFFF",
    "cell_given": "#F3F6FB",
    "cell_hover": "#EEF3FF",
    "cell_peer": "#E4ECFA",
    "cell_same": "#D5E3FF",
    "cell_selected": "#BFDBFE",
    "cell_correct": "#D1FAE5",
    "cell_wrong": "#FFE4E6",
    "given_fg": "#0F172A",
    "player_fg": "#1D4ED8",
    "correct_fg": "#047857",
    "wrong_fg": "#E11D48",
    "grid_thin": "#C5D0E3",
    "grid_thick": "#0F172A",
    "btn_text": "#FFFFFF",
    "btn_erase": "#E11D48",
    "btn_undo": "#7C3AED",
    "btn_hint": "#059669",
    "btn_new": "#2563EB",
    "btn_number": "#1D4ED8",
    "btn_number_done": "#1E293B",
    "level_off": "#1E293B",
    "level_on": "#2563EB",
}

CELL_SIZE = 58
BOARD_PAD = 10
THIN_LINE = 1
THICK_LINE = 3


def format_time(seconds):
    """Turn 322 seconds into '05:22'."""
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def ui_font(size, weight="normal"):
    return (FONT, size, weight)


def _lighten(hex_color, amount=0.18):
    """Mix a hex color toward white for hover."""
    hex_color = hex_color.lstrip("#")
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)
    red = min(255, int(red + (255 - red) * amount))
    green = min(255, int(green + (255 - green) * amount))
    blue = min(255, int(blue + (255 - blue) * amount))
    return f"#{red:02x}{green:02x}{blue:02x}"


class SudokuGame:
    """Main Tkinter window and game controller."""

    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku Puzzle")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        # Game state
        self.difficulty = DEFAULT_DIFFICULTY
        self.puzzle = None
        self.solution = None
        self.current = None
        self.cell_status = None
        self.selected = None
        self.hover_cell = None
        self.undo_stack = []
        self.mistakes = 0
        self.hints_used = 0
        self.time_left = 0
        self.total_time = 0
        self.timer_id = None
        self.timer_started = False
        self.game_active = False
        self.paused = False
        self.previous_puzzle = None

        # Widgets filled in by _build_ui
        self.board_canvas = None
        self.stat_level = None
        self.stat_time = None
        self.stat_mistakes = None
        self.stat_hints = None
        self.stat_score = None
        self.status_label = None
        self.level_buttons = {}
        self.number_tiles = {}

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Key>", self._on_key)

        # Start the first game after the window is drawn.
        self.root.after(50, self.start_new_game)

    # ----------------------------------------------------------
    # User interface
    # ----------------------------------------------------------
    def _build_ui(self):
        """Create the modern header, canvas board, and side controls."""
        self._build_header()

        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=(6, 8))

        self._build_board(body)
        self._build_sidebar(body)
        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLORS["header"])
        header.pack(fill="x")

        inner = tk.Frame(header, bg=COLORS["header"])
        inner.pack(fill="x", padx=24, pady=16)

        brand = tk.Frame(inner, bg=COLORS["header"])
        brand.pack(side="left")

        tk.Label(
            brand,
            text="Sudoku Puzzle",
            font=ui_font(26, "bold"),
            bg=COLORS["header"],
            fg=COLORS["text"],
        ).pack(anchor="w")

        stats = tk.Frame(inner, bg=COLORS["header"])
        stats.pack(side="right")

        self.stat_level = self._stat_card(stats, "LEVEL", "Easy")
        self.stat_time = self._stat_card(stats, "TIME LEFT", "10:00")
        self.stat_mistakes = self._stat_card(stats, "MISTAKES", "0")
        self.stat_hints = self._stat_card(stats, "AI HINTS", "0/3")
        self.stat_score = self._stat_card(stats, "SCORE", "0")

        tk.Frame(self.root, bg=COLORS["accent"], height=3).pack(fill="x")

    def _stat_card(self, parent, caption, value):
        card = tk.Frame(parent, bg=COLORS["card"], padx=10, pady=8)
        card.pack(side="left", padx=(10, 0))

        tk.Label(
            card,
            text=caption,
            font=ui_font(8, "bold"),
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).pack(anchor="w")
        value_label = tk.Label(
            card,
            text=value,
            font=ui_font(16, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
        )
        value_label.pack(anchor="w")
        return value_label

    def _build_board(self, parent):
        wrap = tk.Frame(parent, bg=COLORS["surface"], padx=14, pady=14)
        wrap.pack(side="left")

        board_px = BOARD_PAD * 2 + CELL_SIZE * 9
        self.board_canvas = tk.Canvas(
            wrap,
            width=board_px,
            height=board_px,
            bg=COLORS["board_frame"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.board_canvas.pack()
        self.board_canvas.bind("<Button-1>", self._on_board_click)
        self.board_canvas.bind("<Motion>", self._on_board_move)
        self.board_canvas.bind("<Leave>", self._on_board_leave)
        self._draw_board()

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=COLORS["bg"], width=300)
        side.pack(side="left", fill="both", padx=(20, 0))

        tk.Label(
            side,
            text="DIFFICULTY",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(2, 8))

        levels = tk.Frame(side, bg=COLORS["card"])
        levels.pack(fill="x")
        for name in ("Easy", "Medium", "Hard"):
            button = tk.Label(
                levels,
                text=name,
                font=ui_font(12, "bold"),
                bg=COLORS["level_off"],
                fg=COLORS["muted"],
                pady=10,
                cursor="hand2",
            )
            button.pack(side="left", expand=True, fill="x")
            button.bind("<Button-1>", lambda _event, d=name: self.change_difficulty(d))
            self.level_buttons[name] = button

        tk.Label(
            side,
            text="NUMBERS",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(18, 8))

        pad = tk.Frame(side, bg=COLORS["bg"])
        pad.pack(fill="x")
        for index, number in enumerate(range(1, 10)):
            row = index // 3
            col = index % 3
            tile = self._number_tile(pad, number)
            tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            pad.grid_columnconfigure(col, weight=1)

        tk.Label(
            side,
            text="ACTIONS",
            font=ui_font(9, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
        ).pack(anchor="w", pady=(16, 8))

        actions = tk.Frame(side, bg=COLORS["bg"])
        actions.pack(fill="x")
        self._action_tile(actions, "Erase", "Remove a number", COLORS["btn_erase"], self.delete_number, 0, 0)
        self._action_tile(actions, "Undo", "Reverse last move", COLORS["btn_undo"], self.undo, 0, 1)
        self._action_tile(actions, "AI Hint", "Show candidates", COLORS["btn_hint"], self.show_ai_hint, 1, 0)
        self._action_tile(actions, "New Game", "Shuffle a puzzle", COLORS["btn_new"], self.start_new_game, 1, 1)
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

    def _build_status_bar(self):
        """Full-width message bar so feedback is never clipped under the buttons."""
        bar = tk.Frame(self.root, bg=COLORS["card"])
        bar.pack(fill="x", padx=24, pady=(0, 18))
        self.status_label = tk.Label(
            bar,
            text="Select a cell, then enter a number. The timer starts when you make a move.",
            font=ui_font(13, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            justify="center",
            pady=14,
        )
        self.status_label.pack(fill="x")

    def _number_tile(self, parent, number):
        tile = tk.Frame(parent, bg=COLORS["btn_number"], padx=2, pady=6)
        number_label = tk.Label(
            tile,
            text=str(number),
            font=ui_font(22, "bold"),
            bg=COLORS["btn_number"],
            fg=COLORS["btn_text"],
        )
        number_label.pack()
        count_label = tk.Label(
            tile,
            text="9 left",
            font=ui_font(10, "bold"),
            bg=COLORS["btn_number"],
            fg="#FFFFFF",
        )
        count_label.pack()

        self.number_tiles[number] = {
            "frame": tile,
            "number": number_label,
            "count": count_label,
        }
        self._bind_tile(tile, lambda n=number: self.enter_number(n), COLORS["btn_number"])
        return tile

    def _action_tile(self, parent, title, subtitle, color, command, row, col):
        tile = tk.Frame(parent, bg=color, padx=10, pady=12)
        tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        tk.Label(
            tile,
            text=title,
            font=ui_font(13, "bold"),
            bg=color,
            fg=COLORS["btn_text"],
        ).pack()
        tk.Label(
            tile,
            text=subtitle,
            font=ui_font(11, "bold"),
            bg=color,
            fg="#FFFFFF",
        ).pack(pady=(4, 0))
        self._bind_tile(tile, command, color)

    def _bind_tile(self, tile, command, color):
        """Make a Frame and its labels act like a colored button (works on macOS)."""
        def apply(fill):
            tile.configure(bg=fill)
            for child in tile.winfo_children():
                child.configure(bg=fill)

        def on_enter(_event):
            apply(_lighten(tile._normal_bg))

        def on_leave(_event):
            apply(tile._normal_bg)

        tile._normal_bg = color
        widgets = [tile] + list(tile.winfo_children())
        for widget in widgets:
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda _event: command())
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _ui_button(self, parent, text, bg, command, width=12):
        button = tk.Label(
            parent,
            text=text,
            font=ui_font(12, "bold"),
            bg=bg,
            fg=COLORS["btn_text"],
            width=width,
            padx=12,
            pady=10,
            cursor="hand2",
        )
        button._normal_bg = bg
        button.bind("<Button-1>", lambda _event: command())
        button.bind("<Enter>", lambda _event: button.config(bg=_lighten(button._normal_bg)))
        button.bind("<Leave>", lambda _event: button.config(bg=button._normal_bg))
        return button

    # ----------------------------------------------------------
    # Canvas board
    # ----------------------------------------------------------
    def _cell_at(self, x, y):
        col = (x - BOARD_PAD) // CELL_SIZE
        row = (y - BOARD_PAD) // CELL_SIZE
        if 0 <= row < 9 and 0 <= col < 9:
            return (int(row), int(col))
        return None

    def _on_board_click(self, event):
        cell = self._cell_at(event.x, event.y)
        if cell is not None:
            self.select_cell(*cell)

    def _on_board_move(self, event):
        cell = self._cell_at(event.x, event.y)
        if cell != self.hover_cell:
            self.hover_cell = cell
            self._draw_board()

    def _on_board_leave(self, _event):
        if self.hover_cell is not None:
            self.hover_cell = None
            self._draw_board()

    def refresh_board(self):
        self._draw_board()
        self._refresh_number_pad()

    def _draw_board(self):
        canvas = self.board_canvas
        canvas.delete("all")

        for row in range(9):
            for col in range(9):
                x1 = BOARD_PAD + col * CELL_SIZE
                y1 = BOARD_PAD + row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                bg, fg, text, weight = self._cell_style(row, col)
                canvas.create_rectangle(x1, y1, x2, y2, fill=bg, outline="")
                if text:
                    canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=text,
                        fill=fg,
                        font=ui_font(22, weight),
                    )
                if self.selected == (row, col):
                    canvas.create_rectangle(
                        x1 + 3,
                        y1 + 3,
                        x2 - 3,
                        y2 - 3,
                        outline=COLORS["accent_deep"],
                        width=2,
                    )

        start = BOARD_PAD
        end = BOARD_PAD + CELL_SIZE * 9
        for index in range(10):
            pos = BOARD_PAD + index * CELL_SIZE
            thick = index % 3 == 0
            width = THICK_LINE if thick else THIN_LINE
            color = COLORS["grid_thick"] if thick else COLORS["grid_thin"]
            canvas.create_line(pos, start, pos, end, fill=color, width=width)
            canvas.create_line(start, pos, end, pos, fill=color, width=width)

        if self.current is None:
            canvas.create_text(
                (start + end) / 2,
                (start + end) / 2,
                text="Preparing puzzle…",
                fill=COLORS["muted"],
                font=ui_font(16),
            )

    def _cell_style(self, row, col):
        """Choose fill, text color, glyph, and weight for one cell."""
        if self.current is None:
            return COLORS["cell"], COLORS["given_fg"], "", "bold"

        value = self.current[row][col]
        status = self.cell_status[row][col]
        text = "" if value == 0 else str(value)
        selected = self.selected == (row, col)
        hovered = self.hover_cell == (row, col)

        peer = False
        same_number = False
        if self.selected is not None:
            selected_row, selected_col = self.selected
            peer = (
                row == selected_row
                or col == selected_col
                or (row // 3 == selected_row // 3 and col // 3 == selected_col // 3)
            ) and not selected
            selected_value = self.current[selected_row][selected_col]
            same_number = (
                selected_value != 0
                and value == selected_value
                and not selected
            )

        if status == "given":
            bg, fg, weight = COLORS["cell_given"], COLORS["given_fg"], "bold"
        elif status == "correct":
            bg, fg, weight = COLORS["cell_correct"], COLORS["correct_fg"], "bold"
        elif status == "incorrect":
            bg, fg, weight = COLORS["cell_wrong"], COLORS["wrong_fg"], "bold"
        else:
            bg, fg, weight = COLORS["cell"], COLORS["player_fg"], "bold"

        if status == "incorrect":
            bg = COLORS["cell_wrong"]
        elif selected:
            bg = COLORS["cell_selected"]
        elif same_number:
            bg = COLORS["cell_same"]
        elif peer:
            bg = COLORS["cell_peer"]
        elif hovered and status in ("empty", "given", "correct"):
            bg = COLORS["cell_hover"]

        return bg, fg, text, weight

    def _refresh_number_pad(self):
        if self.current is None:
            return
        for number, widgets in self.number_tiles.items():
            remaining = 9 - self._count_placed(number)
            done = remaining <= 0
            bg = COLORS["btn_number_done"] if done else COLORS["btn_number"]
            count_fg = COLORS["muted"] if done else "#FFFFFF"
            text = "done" if done else f"{remaining} left"
            widgets["frame"]._normal_bg = bg
            widgets["frame"].configure(bg=bg)
            widgets["number"].configure(bg=bg, fg=COLORS["btn_text"] if not done else COLORS["muted"])
            widgets["count"].configure(bg=bg, fg=count_fg, text=text)

    def _count_placed(self, number):
        total = 0
        for row in range(9):
            for col in range(9):
                if self.current[row][col] == number and self.cell_status[row][col] != "incorrect":
                    total += 1
        return total

    # ----------------------------------------------------------
    # Starting and resetting a game
    # ----------------------------------------------------------
    def start_new_game(self, difficulty=None):
        """Generate a new shuffled puzzle and reset all counters."""
        if difficulty is not None:
            self.difficulty = difficulty

        self._stop_timer()
        self.game_active = False
        self.paused = True
        self.set_status("Generating a new puzzle...", "info")
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        settings = DIFFICULTY_SETTINGS[self.difficulty]
        puzzle, solution = generate_puzzle(
            difficulty=self.difficulty,
            clue_count=settings["clues"],
            previous_puzzle=self.previous_puzzle,
        )

        self.previous_puzzle = [row[:] for row in puzzle]
        self.puzzle = puzzle
        self.solution = solution
        self.current = [row[:] for row in puzzle]
        self.cell_status = [
            ["given" if puzzle[r][c] != 0 else "empty" for c in range(9)]
            for r in range(9)
        ]
        self.selected = None
        self.hover_cell = None
        self.undo_stack = []
        self.mistakes = 0
        self.hints_used = 0
        self.total_time = settings["time_seconds"]
        self.time_left = settings["time_seconds"]
        self.timer_started = False
        self.paused = False
        self.game_active = True

        self.root.config(cursor="")
        self._update_level_buttons()
        self.refresh_board()
        self.refresh_header()
        self.set_status("Select a cell, then enter a number. The timer starts when you make a move.", "info")

    def change_difficulty(self, difficulty):
        """Start a brand-new game at a different level."""
        self.start_new_game(difficulty)

    # ----------------------------------------------------------
    # Header and status
    # ----------------------------------------------------------
    def refresh_header(self):
        """Update level, timer, mistakes, and live score."""
        score = calculate_score(
            self.difficulty,
            self.time_left,
            self.mistakes,
            self.hints_used,
            completed=False,
        )
        self.stat_level.config(text=self.difficulty)
        self.stat_time.config(text=format_time(self.time_left))
        self.stat_mistakes.config(text=str(self.mistakes))
        self.stat_hints.config(text=f"{self.hints_used}/{MAX_AI_HINTS}")
        self.stat_score.config(text=str(score))

    def _update_level_buttons(self):
        for name, button in self.level_buttons.items():
            if name == self.difficulty:
                button.config(bg=COLORS["level_on"], fg=COLORS["btn_text"])
            else:
                button.config(bg=COLORS["level_off"], fg=COLORS["muted"])

    def set_status(self, message, kind="info"):
        colors = {
            "correct": COLORS["good"],
            "incorrect": COLORS["bad"],
            "info": COLORS["text"],
        }
        self.status_label.config(
            text=message,
            fg=colors.get(kind, COLORS["text"]),
        )

    # ----------------------------------------------------------
    # Player actions
    # ----------------------------------------------------------
    def select_cell(self, row, col):
        if not self.game_active:
            return
        self._begin_timer()
        self.selected = (row, col)
        self.refresh_board()

    def enter_number(self, number):
        """Place a number in the selected empty cell and check it with AI."""
        if not self._can_edit():
            return
        self._begin_timer()
        if self.selected is None:
            self.set_status("Select an empty cell first.", "info")
            return

        row, col = self.selected
        if self.cell_status[row][col] == "given":
            self.set_status("Original numbers cannot be changed.", "info")
            return

        if self.current[row][col] == number:
            return

        self._save_undo(row, col)
        self.current[row][col] = number

        if is_correct_number(self.solution, row, col, number):
            self.cell_status[row][col] = "correct"
            self.set_status("Correct!", "correct")
        else:
            self.cell_status[row][col] = "incorrect"
            self.mistakes += 1
            self.set_status("Incorrect number.", "incorrect")
            self.refresh_board()
            self.refresh_header()
            if self.mistakes % MISTAKES_PER_AI_HINT == 0:
                self._give_mistake_hint()
            return

        self.refresh_board()
        self.refresh_header()
        self._check_completion()

    def delete_number(self):
        """Clear a player-entered number. Original clues stay locked."""
        if not self._can_edit():
            return
        self._begin_timer()
        if self.selected is None:
            self.set_status("Select a cell to delete.", "info")
            return

        row, col = self.selected
        if self.cell_status[row][col] == "given":
            self.set_status("Original numbers cannot be deleted.", "info")
            return
        if self.current[row][col] == 0:
            return

        self._save_undo(row, col)
        self.current[row][col] = 0
        self.cell_status[row][col] = "empty"
        self.refresh_board()
        self.refresh_header()
        self.set_status("Number deleted.", "info")

    def undo(self):
        """Undo the most recent player entry or delete."""
        if not self._can_edit():
            return
        self._begin_timer()
        if not self.undo_stack:
            self.set_status("Nothing to undo.", "info")
            return

        action = self.undo_stack.pop()
        row = action["row"]
        col = action["col"]
        self.current[row][col] = action["prev_value"]
        self.cell_status[row][col] = action["prev_status"]
        self.selected = (row, col)
        self.refresh_board()
        self.refresh_header()
        self.set_status("Last move undone.", "info")

    def show_ai_hint(self):
        """Show candidates and one AI recommendation for the selected cell."""
        if not self.game_active:
            return
        self._begin_timer()
        if self.hints_used >= MAX_AI_HINTS:
            self.set_status("No more AI hints remaining.", "info")
            return

        cell = self._cell_for_hint()
        if cell is None:
            self.set_status("Select an empty cell to get an AI hint.", "info")
            return

        row, col = cell
        self.selected = (row, col)
        self.refresh_board()

        hint = get_hint(self._board_for_hints(), row, col, self.solution)
        if hint is None:
            self.set_status("Select an empty cell to get an AI hint.", "info")
            return

        self.hints_used += 1
        self.refresh_header()
        self.paused = True
        messagebox.showinfo("AI Hint", hint["message"])
        self.paused = False
        self.set_status(
            f"AI Recommendation: {hint['recommendation']}",
            "info",
        )

    def _save_undo(self, row, col):
        self.undo_stack.append(
            {
                "row": row,
                "col": col,
                "prev_value": self.current[row][col],
                "prev_status": self.cell_status[row][col],
            }
        )

    def _can_edit(self):
        return self.game_active and not self.paused

    def _cell_for_hint(self):
        """Use the selected empty cell, or the first empty cell if needed."""
        if self.selected is not None:
            row, col = self.selected
            if self.current[row][col] == 0:
                return (row, col)

        for row in range(9):
            for col in range(9):
                if self.current[row][col] == 0:
                    return (row, col)
        return None

    def _board_for_hints(self):
        """Copy the board but treat incorrect guesses as empty."""
        board = [row[:] for row in self.current]
        for row in range(9):
            for col in range(9):
                if self.cell_status[row][col] == "incorrect":
                    board[row][col] = 0
        return board

    def _on_key(self, event):
        """Allow typing 1-9, Delete, Backspace, and arrow-key navigation."""
        if event.char in "123456789":
            self.enter_number(int(event.char))
        elif event.keysym in ("BackSpace", "Delete"):
            self.delete_number()
        elif event.keysym in ("Up", "Down", "Left", "Right"):
            self._move_selection(event.keysym)

    def _move_selection(self, direction):
        if not self.game_active:
            return
        row, col = self.selected if self.selected is not None else (0, 0)
        if direction == "Up":
            row = (row - 1) % 9
        elif direction == "Down":
            row = (row + 1) % 9
        elif direction == "Left":
            col = (col - 1) % 9
        elif direction == "Right":
            col = (col + 1) % 9
        self.select_cell(row, col)

    # ----------------------------------------------------------
    # AI assistance after every 2 mistakes (max 3 hints)
    # ----------------------------------------------------------
    def _give_mistake_hint(self):
        """Automatically give an AI hint after 2, 4, and 6 mistakes."""
        if self.hints_used >= MAX_AI_HINTS:
            self.set_status("No more AI hints remaining.", "info")
            return
        self.show_ai_hint()

    # ----------------------------------------------------------
    # Timer
    # ----------------------------------------------------------
    def _begin_timer(self):
        """Start the countdown after the player's first action."""
        if self.timer_started or not self.game_active:
            return
        self.timer_started = True
        self._start_timer()

    def _start_timer(self):
        self._stop_timer()
        self.timer_id = self.root.after(1000, self._tick)

    def _stop_timer(self):
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def _tick(self):
        if not self.game_active:
            return

        if not self.paused:
            self.time_left -= 1
            if self.time_left <= 0:
                self.time_left = 0
                self.refresh_header()
                self._on_timeout()
                return
            self.refresh_header()

        self.timer_id = self.root.after(1000, self._tick)

    def _on_timeout(self):
        self.game_active = False
        self._stop_timer()
        messagebox.showinfo(
            "Time's Up!",
            "Time's Up!\n\n"
            "You could not complete the puzzle in time.\n\n"
            "A new shuffled puzzle will now start.",
        )
        self.start_new_game(self.difficulty)

    # ----------------------------------------------------------
    # Puzzle completion
    # ----------------------------------------------------------
    def _check_completion(self):
        if not is_board_complete_and_correct(self.current, self.solution):
            return

        self.game_active = False
        self._stop_timer()

        time_used = self.total_time - self.time_left
        score = calculate_score(
            self.difficulty,
            self.time_left,
            self.mistakes,
            self.hints_used,
            completed=True,
        )
        self.stat_score.config(text=str(score))
        self.set_status("Congratulations! You solved the Sudoku!", "correct")
        self._show_win_dialog(time_used, score)

    def _show_win_dialog(self, time_used, score):
        dialog = tk.Toplevel(self.root)
        dialog.title("Puzzle Complete")
        dialog.configure(bg=COLORS["bg"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        card = tk.Frame(dialog, bg=COLORS["surface"], padx=28, pady=24)
        card.pack(padx=8, pady=8)

        tk.Label(
            card,
            text="Puzzle complete",
            font=ui_font(20, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"],
        ).pack(pady=(0, 6))
        tk.Label(
            card,
            text="You solved the Sudoku!",
            font=ui_font(12),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
        ).pack()

        summary = tk.Frame(card, bg=COLORS["card"])
        summary.pack(fill="x", pady=18)
        for label, value in (
            ("Time", format_time(time_used)),
            ("Mistakes", str(self.mistakes)),
            ("Hints", str(self.hints_used)),
            ("Score", str(score)),
        ):
            row = tk.Frame(summary, bg=COLORS["card"])
            row.pack(fill="x", padx=16, pady=6)
            tk.Label(row, text=label, font=ui_font(11), bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")
            tk.Label(row, text=value, font=ui_font(12, "bold"), bg=COLORS["card"], fg=COLORS["text"]).pack(side="right")

        buttons = tk.Frame(card, bg=COLORS["surface"])
        buttons.pack()
        self._ui_button(
            buttons,
            "Play Again",
            COLORS["btn_hint"],
            lambda: self._close_win_dialog(dialog, play_again=True),
        ).pack(side="left", padx=6)
        self._ui_button(
            buttons,
            "Change Level",
            COLORS["btn_new"],
            lambda: self._close_win_dialog(dialog, play_again=False),
        ).pack(side="left", padx=6)

        dialog.update_idletasks()
        self._center_dialog(dialog)

    def _close_win_dialog(self, dialog, play_again):
        dialog.destroy()
        if play_again:
            self.start_new_game(self.difficulty)
        else:
            self._show_level_picker()

    def _show_level_picker(self):
        picker = tk.Toplevel(self.root)
        picker.title("Change Level")
        picker.configure(bg=COLORS["bg"])
        picker.resizable(False, False)
        picker.transient(self.root)
        picker.grab_set()

        card = tk.Frame(picker, bg=COLORS["surface"], padx=24, pady=20)
        card.pack(padx=8, pady=8)

        tk.Label(
            card,
            text="Choose a level",
            font=ui_font(16, "bold"),
            bg=COLORS["surface"],
            fg=COLORS["text"],
        ).pack(pady=(0, 14))

        row = tk.Frame(card, bg=COLORS["surface"])
        row.pack()
        for name, color in (("Easy", "#059669"), ("Medium", "#2563EB"), ("Hard", "#E11D48")):
            self._ui_button(
                row,
                name,
                color,
                lambda d=name: self._pick_level(picker, d),
                width=10,
            ).pack(side="left", padx=6)

        picker.update_idletasks()
        self._center_dialog(picker)

    def _pick_level(self, picker, difficulty):
        picker.destroy()
        self.start_new_game(difficulty)

    def _center_dialog(self, dialog):
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"+{x}+{y}")

    def _on_close(self):
        self.game_active = False
        self._stop_timer()
        self.root.destroy()
